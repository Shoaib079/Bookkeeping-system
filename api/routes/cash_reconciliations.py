"""Read-only daily cash reconciliation history endpoint."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import cash_reconciliations_list_to_dict
from services import read_cash_reconciliations
from services.context import RequestContext

router = APIRouter(tags=["cash-reconciliations"])


@router.get(
    "",
    summary="Cash reconciliations",
    description=(
        "Daily cash reconciliation history for the active company. "
        "Submit, approve, and void actions remain Streamlit-only."
    ),
)
def get_cash_reconciliations(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    start_date: Annotated[
        datetime.date | None,
        Query(description="Inclusive start date filter"),
    ] = None,
    end_date: Annotated[
        datetime.date | None,
        Query(description="Inclusive end date filter"),
    ] = None,
    status: Annotated[
        str | None,
        Query(description="Optional status filter (omit or 'all' for any)"),
    ] = None,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "create_reconciliation",
    )
    page = read_cash_reconciliations.compute_cash_reconciliations_list(
        session,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    return cash_reconciliations_list_to_dict(page)
