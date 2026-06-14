"""FASTAPI-P2.6 — worker payment write endpoint."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_write_access
from api.routes.partner_worker_common import require_write_partner_worker_feature
from models import User
from services.context import RequestContext
from services.write_partner_worker import (
    WorkerPaymentWriteResult,
    post_worker_payment_record,
)

router = APIRouter(tags=["writes"])


class CreateWorkerPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worker_id: int
    movement_type: str = Field(..., description="Salary, Advance, or Repayment")
    date: datetime.date
    bank_account_id: int
    amount: float | None = Field(
        default=None,
        description="Required for Advance and Repayment",
    )
    gross_salary: float | None = Field(
        default=None,
        description="Required for Salary",
    )
    deductions: float | None = None
    advance_recovery: float | None = None
    pay_period: str | None = None
    notes: str | None = None


class CreateWorkerPaymentResponse(BaseModel):
    payment_id: int
    journal_entry_id: int
    message: str
    status: str = "ok"


def _result_to_response(
    result: WorkerPaymentWriteResult,
) -> CreateWorkerPaymentResponse:
    return CreateWorkerPaymentResponse(
        payment_id=result.payment_id,
        journal_entry_id=result.journal_entry_id,
        message=result.message,
    )


@router.post(
    "",
    status_code=201,
    summary="Post a worker payment",
    description=(
        "Records salary, advance, or repayment for a worker. "
        "Requires ``ERP_API_WRITE_PARTNER_WORKER=1``. Company scope comes from "
        "``X-Company-Id`` only."
    ),
    response_model=CreateWorkerPaymentResponse,
    responses={
        400: {"description": "Business validation failure."},
        401: {"description": "Missing or invalid bearer token."},
        403: {"description": "Membership or post_worker_movement permission denied."},
        404: {"description": "Write API disabled or not found."},
        422: {"description": "Request schema validation failure."},
    },
)
def post_worker_payment(
    body: CreateWorkerPaymentRequest,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> CreateWorkerPaymentResponse:
    require_write_partner_worker_feature()
    company_id = require_company_write_access(
        session, context, "post_worker_movement"
    )
    user = session.get(User, context.user_id)
    performed_by = user.username if user is not None else None
    try:
        result = post_worker_payment_record(
            session,
            company_id=company_id,
            performed_by=performed_by,
            created_by_id=context.user_id,
            worker_id=body.worker_id,
            movement_type=body.movement_type,
            entry_date=body.date,
            bank_account_id=body.bank_account_id,
            amount=body.amount,
            gross_salary=body.gross_salary,
            deductions=body.deductions,
            advance_recovery=body.advance_recovery,
            pay_period=body.pay_period,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _result_to_response(result)
