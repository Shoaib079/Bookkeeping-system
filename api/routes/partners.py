"""Read-only partner statement endpoint."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.errors import NOT_FOUND_PARTNER_STATEMENT
from api.guards import require_company_read_access
from api.serialization import coa_list_to_dict, partner_statement_to_dict, partners_list_to_dict
from services import read_coa, read_partner_statement, read_partners
from services.context import RequestContext

router = APIRouter(tags=["partners"])


@router.get(
    "",
    summary="Partner directory",
    description="Partners for the active company (picker / list read).",
)
def get_partners(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    active_only: Annotated[
        bool,
        Query(description="When true, return only active partners"),
    ] = True,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_partner_accounts",
        "view_partner_statements",
        "view_management_reports",
    )
    page = read_partners.compute_partners_list(
        session,
        company_id=company_id,
        active_only=active_only,
    )
    return partners_list_to_dict(page)


@router.get(
    "/{partner_id}/statement",
    summary="Partner settlement statement",
    description="Opening/closing position and movement detail for one partner.",
    responses={404: {"description": "Partner not found or not in company scope."}},
)
def get_partner_statement(
    partner_id: int,
    from_date: datetime.date,
    to_date: datetime.date,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_partner_statements",
        "view_partner_accounts",
        "view_statement",
        "view_management_reports",
    )
    data = read_partner_statement.compute_partner_statement(
        session,
        company_id=company_id,
        partner_id=partner_id,
        from_date=from_date,
        to_date=to_date,
    )
    if data is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND_PARTNER_STATEMENT)
    return partner_statement_to_dict(data)
