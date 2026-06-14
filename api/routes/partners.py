"""Read-only partner statement endpoint."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import partner_statement_to_dict
from services import read_partner_statement
from services.context import RequestContext

router = APIRouter(tags=["partners"])


@router.get("/{partner_id}/statement")
def get_partner_statement(
    partner_id: int,
    from_date: datetime.date,
    to_date: datetime.date,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_partner_statements",
        "view_partner_accounts",
        "view_statement",
        "view_management_reports",
    )
    data = read_partner_statement.compute_partner_statement(
        session,
        company_id=company_id,
        partner_id=partner_id,
        from_date=from_date,
        to_date=to_date,
    )
    if data is None:
        raise HTTPException(status_code=404, detail="Partner statement not found.")
    return partner_statement_to_dict(data)
