"""Read-only recipe cost breakdown endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import recipe_cost_breakdown_to_dict
from services import read_recipe_costing
from services.context import RequestContext

router = APIRouter(tags=["recipe-cost-breakdowns"])


@router.get(
    "",
    summary="Recipe cost breakdown",
    description=(
        "Cost breakdown for a single recipe in the active company. "
        "Recipe editing remains Streamlit-only."
    ),
)
def get_recipe_cost_breakdown(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    recipe_id: Annotated[int, Query(description="Recipe id to break down")],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_recipe_costing",
    )
    breakdown = read_recipe_costing.compute_recipe_cost_breakdown(
        session,
        company_id=company_id,
        recipe_id=recipe_id,
    )
    if breakdown is None:
        raise HTTPException(status_code=404, detail="Recipe not found.")
    return recipe_cost_breakdown_to_dict(breakdown)
