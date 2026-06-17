"""Read-only fiscal periods list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import fiscal_periods_list_to_dict
from services import read_fiscal_periods
from services.context import RequestContext

router = APIRouter(tags=["fiscal-periods"])


@router.get(
    "",
    summary="Fiscal periods",
    description="Fiscal periods for the active company (closing tab picker / list read).",
)
def get_fiscal_periods(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    open_only: Annotated[
        bool,
        Query(description="When true, return only open periods"),
    ] = False,
    closed_only: Annotated[
        bool,
        Query(description="When true, return only closed periods"),
    ] = False,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "close_fiscal_period",
        "allocate_profit",
        "view_year_end_close",
        "view_management_reports",
    )
    page = read_fiscal_periods.compute_fiscal_periods_list(
        session,
        company_id=company_id,
        open_only=open_only,
        closed_only=closed_only,
    )
    return fiscal_periods_list_to_dict(page)
