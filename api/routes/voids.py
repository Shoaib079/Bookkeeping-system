"""FASTAPI-P2.5 — void write endpoint."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_write_access
from models import User
from services.context import RequestContext
from services.write_voids import VoidWriteResult, void_record

router = APIRouter(tags=["writes"])

WRITE_VOIDS_ENV = "ERP_API_WRITE_VOIDS"


class VoidRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_type: str = Field(
        ...,
        description="Sale, ExpenseRecord, Purchase, Payable, or BankTransaction",
    )
    target_id: int
    reason: str


class VoidResponse(BaseModel):
    target_type: str
    target_id: int
    reversal_journal_entry_id: int | None
    message: str
    status: str = "ok"


def _write_voids_enabled() -> bool:
    return os.getenv(WRITE_VOIDS_ENV, "").strip().lower() in ("1", "true", "yes")


def _require_write_voids_feature() -> None:
    if not _write_voids_enabled():
        raise HTTPException(status_code=404, detail="Not Found")


def _result_to_response(result: VoidWriteResult) -> VoidResponse:
    return VoidResponse(
        target_type=result.target_type,
        target_id=result.target_id,
        reversal_journal_entry_id=result.reversal_journal_entry_id,
        message=result.message,
    )


@router.post(
    "",
    summary="Void a transactional record",
    description=(
        "Reverses GL entries, flags the target void, and writes audit. "
        "Requires ``ERP_API_WRITE_VOIDS=1``. Never deletes rows. "
        "Company scope comes from ``X-Company-Id`` only."
    ),
    response_model=VoidResponse,
    responses={
        400: {"description": "Validation failure or void rejected."},
        401: {"description": "Missing or invalid bearer token."},
        403: {"description": "Membership or void_transaction permission denied."},
        404: {"description": "Write API disabled or not found."},
        422: {"description": "Request schema validation failure."},
    },
)
def post_void(
    body: VoidRequest,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> VoidResponse:
    _require_write_voids_feature()
    company_id = require_company_write_access(session, context, "void_transaction")
    user = session.get(User, context.user_id)
    performed_by = user.username if user is not None else None
    try:
        result = void_record(
            session,
            company_id=company_id,
            performed_by=performed_by,
            target_type=body.target_type,
            target_id=body.target_id,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _result_to_response(result)
