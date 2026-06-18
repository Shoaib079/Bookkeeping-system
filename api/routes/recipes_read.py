"""Read-only recipe list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import recipes_list_to_dict
from services import read_recipe_costing
from services.context import RequestContext

router = APIRouter(tags=["recipes"])


@router.get(
    "",
    summary="Recipes",
    description=(
        "Recipe summaries for the active company. "
        "Save/deactivate actions remain Streamlit-only."
    ),
)
def get_recipes(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    active_only: Annotated[
        bool | None,
        Query(description="When true, return active recipes only"),
    ] = True,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_recipe_costing",
    )
    page = read_recipe_costing.compute_recipes_list(
        session,
        company_id=company_id,
        active_only=active_only,
    )
    return recipes_list_to_dict(page)
