"""Read-only receivables endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import receivables_page_to_dict
from services import read_ar_ap
from services.context import RequestContext

router = APIRouter(tags=["receivables"])


@router.get(
    "",
    summary="List credit sales (receivables)",
    description=(
        "Returns open and historical credit sales with aging buckets. "
        "Scoped to the active company from ``X-Company-Id``."
    ),
)
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
