"""Read-only recipe ingredient list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import recipe_ingredients_list_to_dict
from services import read_recipe_costing
from services.context import RequestContext

router = APIRouter(tags=["recipe-ingredients"])


@router.get(
    "",
    summary="Recipe ingredients",
    description=(
        "Ingredient catalog for the active company. "
        "Create/update/deactivate actions remain Streamlit-only."
    ),
)
def get_recipe_ingredients(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    active_only: Annotated[
        bool | None,
        Query(description="When true, return active ingredients only"),
    ] = True,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_recipe_costing",
    )
    page = read_recipe_costing.compute_recipe_ingredients_list(
        session,
        company_id=company_id,
        active_only=active_only,
    )
    return recipe_ingredients_list_to_dict(page)
