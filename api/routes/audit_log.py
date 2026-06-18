"""Read-only audit log list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import audit_log_list_to_dict
from services import read_audit_log
from services.context import RequestContext

router = APIRouter(tags=["audit-log"])

_LIMIT_MAX = 2000


@router.get(
    "",
    summary="Audit log",
    description=(
        "Recent company audit log entries, newest first. "
        f"``limit`` is capped at {_LIMIT_MAX}."
    ),
)
def get_audit_log(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    limit: Annotated[
        int,
        Query(ge=1, le=_LIMIT_MAX, description="Max rows to return"),
    ] = 2000,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "edit_transaction",
        "manage_settings",
    )
    page = read_audit_log.compute_audit_log_list(
        session,
        company_id=company_id,
        limit=limit,
    )
    return audit_log_list_to_dict(page)
