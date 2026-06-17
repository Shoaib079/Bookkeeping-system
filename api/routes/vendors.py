"""Read-only vendors list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import vendors_list_to_dict
from services import read_vendors
from services.context import RequestContext

router = APIRouter(tags=["vendors"])


@router.get(
    "",
    summary="Vendors",
    description="Vendor directory for the active company (reconciliation picker / list read).",
)
def get_vendors(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    active_only: Annotated[
        bool,
        Query(description="When true, return only active vendors"),
    ] = True,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "create_customer_vendor",
        "view_payables",
        "import_bank_statement",
        "view_management_reports",
    )
    page = read_vendors.compute_vendors_list(
        session,
        company_id=company_id,
        active_only=active_only,
    )
    return vendors_list_to_dict(page)
