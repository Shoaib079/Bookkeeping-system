"""Read-only receivables and payables endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import payables_page_to_dict, receivables_page_to_dict
from services import read_ar_ap
from services.context import RequestContext

router = APIRouter(tags=["ar-ap"])


@router.get("/receivables")
def get_receivables(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    search: str | None = None,
    customer: str = "all",
    status: str = "all",
) -> dict:
    company_id = require_company_read_access(
        session, context, "view_receivables", "view_management_reports",
    )
    page = read_ar_ap.compute_receivables_page(
        session,
        company_id=company_id,
        search_keyword=search,
        customer_filter=customer,
        status_filter=status,
    )
    return receivables_page_to_dict(page)


@router.get("/payables")
def get_payables(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    search: str | None = None,
    vendor: str = "all",
    paid_filter: str = "all",
    show_voided: Annotated[bool, Query()] = False,
) -> dict:
    company_id = require_company_read_access(
        session, context, "view_payables", "view_management_reports",
    )
    page = read_ar_ap.compute_payables_page(
        session,
        company_id=company_id,
        search_keyword=search,
        vendor_filter=vendor,
        paid_filter=paid_filter,
        show_voided=show_voided,
    )
    return payables_page_to_dict(page)
