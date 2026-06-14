"""FASTAPI-P2.4 — receivable payment write endpoint."""

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
from services.write_receivable_payments import (
    ReceivablePaymentWriteResult,
    record_receivable_payment,
)

router = APIRouter(tags=["writes"])

WRITE_RECEIVABLE_PAYMENTS_ENV = "ERP_API_WRITE_RECEIVABLE_PAYMENTS"


class CreateReceivablePaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: datetime.date
    amount: float
    currency: str = "TRY"
    payment_method: str = Field(..., description="Cash or Bank")
    sale_id: int
    customer_id: int | None = None
    customer_name: str | None = None
    bank_account_id: int | None = Field(
        default=None,
        description="Bank account for Bank payment method",
    )
    notes: str = ""


class CreateReceivablePaymentResponse(BaseModel):
    payment_id: int
    journal_entry_id: int
    sale_id: int
    message: str
    status: str = "ok"


def _write_receivable_payments_enabled() -> bool:
    return os.getenv(WRITE_RECEIVABLE_PAYMENTS_ENV, "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _require_write_receivable_payments_feature() -> None:
    if not _write_receivable_payments_enabled():
        raise HTTPException(status_code=404, detail="Not Found")


def _result_to_response(
    result: ReceivablePaymentWriteResult,
) -> CreateReceivablePaymentResponse:
    return CreateReceivablePaymentResponse(
        payment_id=result.payment_id,
        journal_entry_id=result.journal_entry_id,
        sale_id=result.sale_id,
        message=result.message,
    )


@router.post(
    "",
    status_code=201,
    summary="Record a receivable payment",
    description=(
        "Applies a cash or bank payment against an open credit sale. "
        "Requires ``ERP_API_WRITE_RECEIVABLE_PAYMENTS=1``. Company scope comes from "
        "``X-Company-Id`` only — never from the request body."
    ),
    response_model=CreateReceivablePaymentResponse,
    responses={
        400: {"description": "Business validation failure."},
        401: {"description": "Missing or invalid bearer token."},
        403: {"description": "Membership or create_transaction permission denied."},
        404: {"description": "Write API disabled or not found."},
        422: {"description": "Request schema validation failure."},
    },
)
def post_receivable_payment(
    body: CreateReceivablePaymentRequest,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> CreateReceivablePaymentResponse:
    _require_write_receivable_payments_feature()
    company_id = require_company_write_access(session, context, "create_transaction")
    user = session.get(User, context.user_id)
    performed_by = user.username if user is not None else None
    try:
        result = record_receivable_payment(
            session,
            company_id=company_id,
            performed_by=performed_by,
            entry_date=body.date,
            amount=body.amount,
            currency=body.currency,
            payment_method=body.payment_method,
            sale_id=body.sale_id,
            customer_id=body.customer_id,
            customer_name=body.customer_name,
            bank_account_id=body.bank_account_id,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _result_to_response(result)
