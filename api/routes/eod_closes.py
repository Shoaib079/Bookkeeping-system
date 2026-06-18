"""Read-only end-of-day close history endpoint."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import eod_closes_list_to_dict
from services import read_eod_closes
from services.context import RequestContext

router = APIRouter(tags=["end-of-day-closes"])


@router.get(
    "",
    summary="End-of-day closes",
    description=(
        "End-of-day close history for the active company. "
        "Close and void actions remain Streamlit-only."
    ),
)
def get_end_of_day_closes(
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
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "close_day",
    )
    page = read_eod_closes.compute_eod_closes_list(
        session,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
    )
    return eod_closes_list_to_dict(page)
