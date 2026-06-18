"""Read-only product catalog endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import products_list_to_dict
from services import read_products
from services.context import RequestContext

router = APIRouter(tags=["products"])


@router.get(
    "",
    summary="Products",
    description=(
        "Product catalog for the active company (inventory read). "
        "Stock adjustments and product writes remain Streamlit-only."
    ),
)
def get_products(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    active_only: Annotated[
        bool,
        Query(description="When true, return only active products"),
    ] = True,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "manage_inventory",
        "view_management_reports",
    )
    page = read_products.compute_products_list(
        session,
        company_id=company_id,
        active_only=active_only,
    )
    return products_list_to_dict(page)
