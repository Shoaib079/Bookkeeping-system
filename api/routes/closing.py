"""FASTAPI-P2.9 — period close / profit allocation / allocation void write endpoints."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_write_access
from models import User
from services import write_closing
from services.context import RequestContext

router = APIRouter(tags=["writes"])

WRITE_CLOSING_ENV = "ERP_API_WRITE_CLOSING"


def _write_closing_enabled() -> bool:
    return os.getenv(WRITE_CLOSING_ENV, "").strip().lower() in ("1", "true", "yes")


def _require_write_closing_feature() -> None:
    if not _write_closing_enabled():
        raise HTTPException(status_code=404, detail="Not Found")


def _performed_by(session: Session, context: RequestContext) -> str | None:
    user = session.get(User, context.user_id)
    return user.username if user is not None else None


class PeriodCloseResponse(BaseModel):
    period_id: int
    journal_entry_id: int
    message: str
    status: str = "ok"


class ProfitAllocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_id: int
    notes: str | None = None


class ProfitAllocationResponse(BaseModel):
    allocation_id: int
    journal_entry_id: int | None
    message: str
    status: str = "ok"


class AllocationVoidRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str


class AllocationVoidResponse(BaseModel):
    allocation_id: int
    journal_entry_id: int | None
    message: str
    status: str = "ok"


_WRITE_RESPONSES = {
    400: {"description": "Validation failure or operation rejected."},
    401: {"description": "Missing or invalid bearer token."},
    403: {"description": "Membership or permission denied."},
    404: {"description": "Write API disabled or not found."},
    422: {"description": "Request schema validation failure."},
}


@router.post(
    "/periods/{period_id}/close",
    summary="Close a fiscal period",
    description=(
        "Posts the period closing journal (Dr income / Cr expense / net to Retained "
        "Earnings) and locks the period. Requires ``ERP_API_WRITE_CLOSING=1``. "
        "Company scope comes from ``X-Company-Id`` only."
    ),
    response_model=PeriodCloseResponse,
    responses=_WRITE_RESPONSES,
)
def post_close_period(
    period_id: int,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> PeriodCloseResponse:
    _require_write_closing_feature()
    company_id = require_company_write_access(session, context, "close_fiscal_period")
    performed_by = _performed_by(session, context)
    try:
        result = write_closing.close_period(
            session,
            company_id=company_id,
            performed_by=performed_by,
            period_id=period_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PeriodCloseResponse(
        period_id=result.period_id,
        journal_entry_id=result.journal_entry_id,
        message=result.message,
    )


@router.post(
    "/profit-allocations",
    summary="Allocate a closed period's profit to partners",
    description=(
        "Allocates the period's net income (read from its closing JE) across active "
        "partner current accounts. Requires ``ERP_API_WRITE_CLOSING=1``. "
        "Company scope comes from ``X-Company-Id`` only."
    ),
    response_model=ProfitAllocationResponse,
    responses=_WRITE_RESPONSES,
)
def post_profit_allocation(
    body: ProfitAllocationRequest,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> ProfitAllocationResponse:
    _require_write_closing_feature()
    company_id = require_company_write_access(session, context, "allocate_profit")
    performed_by = _performed_by(session, context)
    try:
        result = write_closing.allocate(
            session,
            company_id=company_id,
            performed_by=performed_by,
            allocated_by_id=context.user_id,
            period_id=body.period_id,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ProfitAllocationResponse(
        allocation_id=result.allocation_id,
        journal_entry_id=result.journal_entry_id,
        message=result.message,
    )


@router.post(
    "/profit-allocations/{allocation_id}/void",
    summary="Void a profit allocation",
    description=(
        "Reverses the allocation's journal entry and flags it void. "
        "Requires ``ERP_API_WRITE_CLOSING=1``. Never deletes rows. "
        "Company scope comes from ``X-Company-Id`` only."
    ),
    response_model=AllocationVoidResponse,
    responses=_WRITE_RESPONSES,
)
def post_void_allocation(
    allocation_id: int,
    body: AllocationVoidRequest,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> AllocationVoidResponse:
    _require_write_closing_feature()
    company_id = require_company_write_access(session, context, "void_profit_allocation")
    performed_by = _performed_by(session, context)
    try:
        result = write_closing.void_allocation(
            session,
            company_id=company_id,
            performed_by=performed_by,
            voider_id=context.user_id,
            allocation_id=allocation_id,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AllocationVoidResponse(
        allocation_id=result.allocation_id,
        journal_entry_id=result.reversal_journal_entry_id,
        message=result.message,
    )
