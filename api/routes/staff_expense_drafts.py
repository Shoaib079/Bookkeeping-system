"""Read-only staff expense draft submissions and inbox endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import staff_expense_drafts_page_to_dict
from services import read_staff_expense_drafts
from services.context import RequestContext

router = APIRouter(tags=["staff-expense-drafts"])


@router.get(
    "",
    summary="Staff expense drafts",
    description=(
        "Own expense draft submissions and approval inbox for the active company. "
        "Submit, approve, reject, and return actions remain Streamlit-only."
    ),
)
def get_staff_expense_drafts(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "submit_expense_drafts",
        "approve_expense_drafts",
    )
    page = read_staff_expense_drafts.compute_staff_expense_drafts_page(
        session,
        company_id=company_id,
        user_id=context.user_id,
        can_submit=context.can("submit_expense_drafts"),
        can_approve=context.can("approve_expense_drafts"),
    )
    return staff_expense_drafts_page_to_dict(page)
