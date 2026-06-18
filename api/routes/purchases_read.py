"""Read-only purchases list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import purchases_list_to_dict
from services import read_purchases
from services.context import RequestContext

router = APIRouter(tags=["purchases"])


@router.get(
    "",
    summary="Purchases",
    description="Purchase register for the active company (read-only list).",
)
def get_purchases(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    show_voided: Annotated[
        bool,
        Query(description="When true, include voided purchases"),
    ] = False,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "create_transaction",
        "view_payables",
        "view_management_reports",
    )
    page = read_purchases.compute_purchases_list(
        session,
        company_id=company_id,
        show_voided=show_voided,
    )
    return purchases_list_to_dict(page)
