"""Read-only customers list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import customers_list_to_dict
from services import read_customers
from services.context import RequestContext

router = APIRouter(tags=["customers"])


@router.get(
    "",
    summary="Customers",
    description="Customer directory for the active company (read-only list).",
)
def get_customers(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    active_only: Annotated[
        bool,
        Query(description="When true, return only active customers"),
    ] = True,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "create_customer_vendor",
        "view_receivables",
        "view_management_reports",
    )
    page = read_customers.compute_customers_list(
        session,
        company_id=company_id,
        active_only=active_only,
    )
    return customers_list_to_dict(page)
