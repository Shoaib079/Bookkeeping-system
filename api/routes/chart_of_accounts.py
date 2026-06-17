"""Read-only chart of accounts list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import coa_list_to_dict
from services import read_coa
from services.context import RequestContext

router = APIRouter(tags=["chart-of-accounts"])


@router.get(
    "",
    summary="Chart of accounts",
    description="Active GL accounts for the active company (picker / list read).",
)
def get_chart_of_accounts(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    active_only: Annotated[
        bool,
        Query(description="When true, return only active accounts"),
    ] = True,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_ledger",
        "view_management_reports",
    )
    page = read_coa.compute_chart_of_accounts_list(
        session,
        company_id=company_id,
        active_only=active_only,
    )
    return coa_list_to_dict(page)
