"""Read-only transaction history endpoint."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import transaction_history_page_to_dict
from services import read_transaction_history
from services.context import RequestContext

router = APIRouter(tags=["transactions"])


@router.get(
    "",
    summary="Transaction history",
    description=(
        "Filtered sales, expenses, purchases, banking, and payables for a date range."
    ),
)
def get_transactions(
    start_date: datetime.date,
    end_date: datetime.date,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    search: Annotated[str | None, Query(description="Keyword search")] = None,
    type_filter: Annotated[
        str,
        Query(description="Sale, Expense, Purchase, Banking, Payable, or all"),
    ] = "all",
    show_voided: Annotated[bool, Query(description="Include voided rows")] = False,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_management_reports",
    )
    page = read_transaction_history.compute_transaction_history_page(
        session,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        search_keyword=search,
        type_filter=type_filter,
        show_voided=show_voided,
    )
    return transaction_history_page_to_dict(page)
