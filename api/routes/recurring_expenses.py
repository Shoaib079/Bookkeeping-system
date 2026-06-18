"""Read-only recurring expense templates and drafts endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import recurring_expenses_page_to_dict
from services import read_recurring_expenses
from services.context import RequestContext

router = APIRouter(tags=["recurring-expenses"])


@router.get(
    "",
    summary="Recurring expenses",
    description=(
        "Recurring expense templates, pending drafts, and draft history for the active company. "
        "Post, skip, postpone, and template CRUD remain Streamlit-only."
    ),
)
def get_recurring_expenses(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "manage_recurring_templates",
        "post_recurring_draft",
    )
    page = read_recurring_expenses.compute_recurring_expenses_page(
        session,
        company_id=company_id,
    )
    return recurring_expenses_page_to_dict(page)
