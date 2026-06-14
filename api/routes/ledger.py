"""Read-only general ledger endpoint."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import ledger_page_to_dict
from services import read_ledger
from services.context import RequestContext

router = APIRouter(tags=["ledger"])


@router.get("")
def get_ledger(
    account_id: Annotated[int, Query()],
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
    search: str | None = None,
) -> dict:
    company_id = require_company_read_access(
        session, context, "view_ledger", "view_management_reports",
    )
    page = read_ledger.compute_ledger_page(
        session,
        company_id=company_id,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        search_keyword=search,
    )
    return ledger_page_to_dict(page)
