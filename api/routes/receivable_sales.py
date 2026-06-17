"""Read-only open credit sales list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import receivable_sales_list_to_dict
from services import read_receivable_sales
from services.context import RequestContext

router = APIRouter(tags=["receivable-sales"])


@router.get(
    "",
    summary="Open credit sales",
    description="Credit sales with outstanding balance for receivable payment pickers.",
)
def get_receivable_sales(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    open_only: Annotated[
        bool,
        Query(description="When true, return only sales with balance > 0"),
    ] = True,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_receivables",
        "create_transaction",
        "view_management_reports",
    )
    page = read_receivable_sales.compute_receivable_sales_list(
        session,
        company_id=company_id,
        open_only=open_only,
    )
    return receivable_sales_list_to_dict(page)
