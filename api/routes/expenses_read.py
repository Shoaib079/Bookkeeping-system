"""Read-only expenses list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import expenses_list_to_dict
from services import read_expenses
from services.context import RequestContext

router = APIRouter(tags=["expenses"])


@router.get(
    "",
    summary="Expenses",
    description="Expense register for the active company (read-only list).",
)
def get_expenses(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    show_voided: Annotated[
        bool,
        Query(description="When true, include voided expenses"),
    ] = False,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "create_transaction",
        "view_management_reports",
    )
    page = read_expenses.compute_expenses_list(
        session,
        company_id=company_id,
        show_voided=show_voided,
    )
    return expenses_list_to_dict(page)
