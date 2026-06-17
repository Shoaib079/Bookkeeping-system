"""Read-only workers list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import workers_list_to_dict
from services import read_workers
from services.context import RequestContext

router = APIRouter(tags=["workers"])


@router.get(
    "",
    summary="Workers",
    description="Staff directory for the active company (picker / list read).",
)
def get_workers(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    active_only: Annotated[
        bool,
        Query(description="When true, return only active workers"),
    ] = True,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_workers",
        "post_worker_movement",
        "manage_workers",
        "view_management_reports",
    )
    page = read_workers.compute_workers_list(
        session,
        company_id=company_id,
        active_only=active_only,
    )
    return workers_list_to_dict(page)
