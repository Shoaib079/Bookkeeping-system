"""Read-only year-end close history endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import year_end_closes_list_to_dict
from services import read_year_end_closes
from services.context import RequestContext

router = APIRouter(tags=["year-end-closes"])


@router.get(
    "",
    summary="Year-end closes",
    description=(
        "Year-end close history for the active company. "
        "Close and void actions remain Streamlit-only."
    ),
)
def get_year_end_closes(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_year_end_close",
    )
    page = read_year_end_closes.compute_year_end_closes_list(
        session,
        company_id=company_id,
    )
    return year_end_closes_list_to_dict(page)
