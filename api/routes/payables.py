"""Read-only payables endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import payables_page_to_dict
from services import read_ar_ap
from services.context import RequestContext

router = APIRouter(tags=["payables"])


@router.get(
    "",
    summary="List payables",
    description=(
        "Returns vendor payables with status and aging. "
        "Scoped to the active company from ``X-Company-Id``."
    ),
)
def get_payables(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    search: str | None = None,
    vendor: str = "all",
    paid_filter: str = "all",
    show_voided: Annotated[bool, Query(description="Include voided payables")] = False,
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
