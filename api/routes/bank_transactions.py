"""FASTAPI-P2.7 — manual bank transaction write endpoint."""

from __future__ import annotations

import datetime
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_write_access
from models import User
from services.context import RequestContext
from services.write_banking import (
    BankTransactionWriteResult,
    create_manual_bank_transaction,
)

router = APIRouter(tags=["writes"])

WRITE_BANKING_ENV = "ERP_API_WRITE_BANKING"


class CreateBankTransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: datetime.date
    amount: float
    transaction_type: str = Field(
        ...,
        description="deposit, withdrawal, or transfer",
    )
    bank_account_id: int
    destination_bank_account_id: int | None = Field(
        default=None,
        description="Required for transfer — must differ from bank_account_id",
    )
    currency: str | None = Field(
        default=None,
        description="Optional; defaults to the source bank account currency",
    )
    notes: str = ""


class CreateBankTransactionResponse(BaseModel):
    bank_transaction_id: int
    paired_transaction_id: int | None
    journal_entry_id: int | None
    message: str
    status: str = "ok"


def _write_banking_enabled() -> bool:
    return os.getenv(WRITE_BANKING_ENV, "").strip().lower() in ("1", "true", "yes")


def _require_write_banking_feature() -> None:
    if not _write_banking_enabled():
        raise HTTPException(status_code=404, detail="Not Found")


def _result_to_response(
    result: BankTransactionWriteResult,
) -> CreateBankTransactionResponse:
    return CreateBankTransactionResponse(
        bank_transaction_id=result.bank_transaction_id,
        paired_transaction_id=result.paired_transaction_id,
        journal_entry_id=result.journal_entry_id,
        message=result.message,
    )


@router.post(
    "",
    status_code=201,
    summary="Record a manual bank transaction",
    description=(
        "Creates a manual deposit, withdrawal, or transfer on a bank sub-ledger "
        "account and posts GL when applicable. Requires ``ERP_API_WRITE_BANKING=1``. "
        "Imported statement rows are not modified. Company scope comes from "
        "``X-Company-Id`` only."
    ),
    response_model=CreateBankTransactionResponse,
    responses={
        400: {"description": "Business validation failure."},
        401: {"description": "Missing or invalid bearer token."},
        403: {"description": "Membership or manage_banking permission denied."},
        404: {"description": "Write API disabled or not found."},
        422: {"description": "Request schema validation failure."},
    },
)
def post_bank_transaction(
    body: CreateBankTransactionRequest,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> CreateBankTransactionResponse:
    _require_write_banking_feature()
    company_id = require_company_write_access(session, context, "manage_banking")
    user = session.get(User, context.user_id)
    performed_by = user.username if user is not None else None
    try:
        result = create_manual_bank_transaction(
            session,
            company_id=company_id,
            performed_by=performed_by,
            entry_date=body.date,
            amount=body.amount,
            transaction_type=body.transaction_type,
            bank_account_id=body.bank_account_id,
            destination_bank_account_id=body.destination_bank_account_id,
            currency=body.currency,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _result_to_response(result)
