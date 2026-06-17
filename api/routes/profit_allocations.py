"""Read-only profit allocations list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import profit_allocations_list_to_dict
from services import read_profit_allocations
from services.context import RequestContext

router = APIRouter(tags=["profit-allocations"])


@router.get(
    "",
    summary="Profit allocations",
    description="Partner profit allocations for void-allocation pickers.",
)
def get_profit_allocations(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    active_only: Annotated[
        bool,
        Query(description="When true, return only non-void allocations"),
    ] = True,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "void_profit_allocation",
        "allocate_profit",
        "view_partner_accounts",
        "view_management_reports",
    )
    page = read_profit_allocations.compute_profit_allocations_list(
        session,
        company_id=company_id,
        active_only=active_only,
    )
    return profit_allocations_list_to_dict(page)
