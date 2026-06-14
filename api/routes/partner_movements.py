"""FASTAPI-P2.6 — partner movement write endpoint."""

from __future__ import annotations

import datetime
import os
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
    PartnerMovementWriteResult,
    post_partner_movement_record,
)

router = APIRouter(tags=["writes"])


class CreatePartnerMovementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partner_id: int
    movement_type: str = Field(
        ...,
        description=(
            "CapitalContribution, Drawing, Salary, Advance, Repayment, or AdvanceOffset"
        ),
    )
    amount: float
    date: datetime.date
    bank_account_id: int | None = Field(
        default=None,
        description="Required except for AdvanceOffset",
    )
    notes: str | None = None


class CreatePartnerMovementResponse(BaseModel):
    movement_id: int
    journal_entry_id: int
    message: str
    status: str = "ok"


def _result_to_response(
    result: PartnerMovementWriteResult,
) -> CreatePartnerMovementResponse:
    return CreatePartnerMovementResponse(
        movement_id=result.movement_id,
        journal_entry_id=result.journal_entry_id,
        message=result.message,
    )


@router.post(
    "",
    status_code=201,
    summary="Post a partner movement",
    description=(
        "Records capital contribution, drawing, salary, advance, repayment, or "
        "advance offset for a partner. Requires ``ERP_API_WRITE_PARTNER_WORKER=1``. "
        "Company scope comes from ``X-Company-Id`` only."
    ),
    response_model=CreatePartnerMovementResponse,
    responses={
        400: {"description": "Business validation failure."},
        401: {"description": "Missing or invalid bearer token."},
        403: {"description": "Membership or post_partner_movement permission denied."},
        404: {"description": "Write API disabled or not found."},
        422: {"description": "Request schema validation failure."},
    },
)
def post_partner_movement(
    body: CreatePartnerMovementRequest,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> CreatePartnerMovementResponse:
    require_write_partner_worker_feature()
    company_id = require_company_write_access(
        session, context, "post_partner_movement"
    )
    user = session.get(User, context.user_id)
    performed_by = user.username if user is not None else None
    try:
        result = post_partner_movement_record(
            session,
            company_id=company_id,
            performed_by=performed_by,
            created_by_id=context.user_id,
            partner_id=body.partner_id,
            movement_type=body.movement_type,
            amount=body.amount,
            entry_date=body.date,
            bank_account_id=body.bank_account_id,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _result_to_response(result)
