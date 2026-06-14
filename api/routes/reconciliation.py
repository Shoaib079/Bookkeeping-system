"""FASTAPI-P2.8 — reconciliation match/unmatch write endpoints."""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_write_access
from models import User
from services.context import RequestContext
from services.write_reconciliation import (
    ReconciliationMatchResult,
    ReconciliationUnmatchResult,
    match_statement_row,
    unmatch_statement_row,
)

router = APIRouter(tags=["writes"])

WRITE_RECONCILIATION_ENV = "ERP_API_WRITE_RECONCILIATION"


class ReconciliationMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement_row_id: int
    match_type: str = Field(
        ...,
        description=(
            "generic_deposit, bank_charge, deposit_clearing, vendor_outflow, "
            "partner, worker, equity, or cc_bill_payment"
        ),
    )
    credit_account_name: str | None = None
    charge_subtype: str | None = None
    sale_ids: list[int] | None = None
    settlement_row_id: int | None = None
    confirm_inferred_fee: bool = False
    vendor_id: int | None = None
    payable_id: int | None = None
    expense_category: str | None = None
    create_expense: bool = False
    partner_id: int | None = None
    movement_type: str | None = None
    worker_id: int | None = None
    gross_salary: float | None = None
    deductions: float | None = None
    advance_recovery: float | None = None
    pay_period: str | None = None
    equity_kind: str | None = None
    credit_card_account_id: int | None = None


class ReconciliationUnmatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement_row_id: int
    reason: str


class ReconciliationMatchResponse(BaseModel):
    statement_row_id: int
    match_id: int
    journal_entry_id: int | None
    message: str
    status: str = "ok"


class ReconciliationUnmatchResponse(BaseModel):
    statement_row_id: int
    message: str
    status: str = "ok"


def _write_reconciliation_enabled() -> bool:
    return os.getenv(WRITE_RECONCILIATION_ENV, "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _require_write_reconciliation_feature() -> None:
    if not _write_reconciliation_enabled():
        raise HTTPException(status_code=404, detail="Not Found")


def _payload_from_body(body: ReconciliationMatchRequest) -> dict[str, Any]:
    return {
        "credit_account_name": body.credit_account_name,
        "charge_subtype": body.charge_subtype,
        "sale_ids": body.sale_ids,
        "settlement_row_id": body.settlement_row_id,
        "confirm_inferred_fee": body.confirm_inferred_fee,
        "vendor_id": body.vendor_id,
        "payable_id": body.payable_id,
        "expense_category": body.expense_category,
        "create_expense": body.create_expense,
        "partner_id": body.partner_id,
        "movement_type": body.movement_type,
        "worker_id": body.worker_id,
        "gross_salary": body.gross_salary,
        "deductions": body.deductions,
        "advance_recovery": body.advance_recovery,
        "pay_period": body.pay_period,
        "equity_kind": body.equity_kind,
        "credit_card_account_id": body.credit_card_account_id,
    }


def _match_to_response(result: ReconciliationMatchResult) -> ReconciliationMatchResponse:
    return ReconciliationMatchResponse(
        statement_row_id=result.statement_row_id,
        match_id=result.match_id,
        journal_entry_id=result.journal_entry_id,
        message=result.message,
    )


def _unmatch_to_response(
    result: ReconciliationUnmatchResult,
) -> ReconciliationUnmatchResponse:
    return ReconciliationUnmatchResponse(
        statement_row_id=result.statement_row_id,
        message=result.message,
    )


@router.post(
    "/match",
    status_code=201,
    summary="Match and post a bank statement row",
    description=(
        "Posts a staged bank statement row using the existing reconciliation "
        "posters. Requires ``ERP_API_WRITE_RECONCILIATION=1``. Imported row "
        "history fields remain immutable; only reconciliation stamp fields change."
    ),
    response_model=ReconciliationMatchResponse,
    responses={
        400: {"description": "Business validation failure."},
        401: {"description": "Missing or invalid bearer token."},
        403: {"description": "Membership or import_bank_statement permission denied."},
        404: {"description": "Write API disabled or not found."},
        422: {"description": "Request schema validation failure."},
    },
)
def post_reconciliation_match(
    body: ReconciliationMatchRequest,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> ReconciliationMatchResponse:
    _require_write_reconciliation_feature()
    company_id = require_company_write_access(
        session, context, "import_bank_statement"
    )
    user = session.get(User, context.user_id)
    performed_by = user.username if user is not None else None
    try:
        result = match_statement_row(
            session,
            company_id=company_id,
            user_id=context.user_id,
            performed_by=performed_by,
            statement_row_id=body.statement_row_id,
            match_type=body.match_type,
            **_payload_from_body(body),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _match_to_response(result)


@router.post(
    "/unmatch",
    summary="Unpost a matched credit card bill payment row",
    description=(
        "Reverses a posted ``cc_bill_payment`` statement row. Requires "
        "``ERP_API_WRITE_RECONCILIATION=1``. Other match types must use their "
        "existing void paths."
    ),
    response_model=ReconciliationUnmatchResponse,
    responses={
        400: {"description": "Business validation failure."},
        401: {"description": "Missing or invalid bearer token."},
        403: {"description": "Membership or import_bank_statement permission denied."},
        404: {"description": "Write API disabled or not found."},
        422: {"description": "Request schema validation failure."},
    },
)
def post_reconciliation_unmatch(
    body: ReconciliationUnmatchRequest,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> ReconciliationUnmatchResponse:
    _require_write_reconciliation_feature()
    company_id = require_company_write_access(
        session, context, "import_bank_statement"
    )
    user = session.get(User, context.user_id)
    performed_by = user.username if user is not None else None
    try:
        result = unmatch_statement_row(
            session,
            company_id=company_id,
            performed_by=performed_by,
            statement_row_id=body.statement_row_id,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _unmatch_to_response(result)
