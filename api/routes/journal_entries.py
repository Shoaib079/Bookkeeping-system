"""Read-only journal entries list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import journal_entries_list_to_dict
from services import read_journal_entries
from services.context import RequestContext

router = APIRouter(tags=["journal-entries"])


@router.get(
    "",
    summary="Journal entries",
    description="Posted journal entries with debit/credit lines for the active company.",
)
def get_journal_entries(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_ledger",
        "view_management_reports",
    )
    page = read_journal_entries.compute_journal_entries_list(
        session,
        company_id=company_id,
    )
    return journal_entries_list_to_dict(page)
