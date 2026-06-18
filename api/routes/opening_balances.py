"""Read-only opening balances status endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import opening_balances_status_to_dict
from services import read_opening_balances
from services.context import RequestContext

router = APIRouter(tags=["opening-balances"])


@router.get(
    "",
    summary="Opening balances status",
    description=(
        "Read-only opening-balance equity summary and per-entity OB posting status."
    ),
)
def get_opening_balances_status(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_management_reports",
    )
    page = read_opening_balances.compute_opening_balances_status(
        session,
        company_id=company_id,
    )
    return opening_balances_status_to_dict(page)
