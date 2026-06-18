"""Read-only menu profitability list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import menu_profitability_list_to_dict
from services import read_recipe_costing
from services import recipe_costing as rc_svc
from services.context import RequestContext

router = APIRouter(tags=["menu-profitability"])


@router.get(
    "",
    summary="Menu profitability",
    description=(
        "Menu item profitability for the active company. "
        "Menu CRUD and price history remain Streamlit-only."
    ),
)
def get_menu_profitability(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    active_only: Annotated[
        bool,
        Query(description="When true, return active menu items only"),
    ] = True,
    target_food_cost_pct: Annotated[
        float,
        Query(description="Target food cost percentage for suggested pricing"),
    ] = rc_svc.DEFAULT_TARGET_FOOD_COST_PCT,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_recipe_costing",
    )
    page = read_recipe_costing.compute_menu_profitability_list(
        session,
        company_id=company_id,
        active_only=active_only,
        target_food_cost_pct=target_food_cost_pct,
    )
    return menu_profitability_list_to_dict(page)
