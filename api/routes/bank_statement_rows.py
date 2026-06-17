"""Read-only bank statement rows list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import bank_statement_rows_list_to_dict
from services import read_bank_statement_rows
from services.context import RequestContext

router = APIRouter(tags=["bank-statement-rows"])

_LIMIT_MAX = read_bank_statement_rows._LIST_LIMIT_MAX


@router.get(
    "",
    summary="Bank statement rows",
    description=(
        "Matchable imported statement rows for the active company (picker / list read). "
        f"``limit`` is capped at {_LIMIT_MAX}."
    ),
)
def get_bank_statement_rows(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    import_id: Annotated[
        int | None,
        Query(description="Optional bank statement import id filter"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=_LIMIT_MAX, description="Max rows to return"),
    ] = 100,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_reconciliation",
        "view_bank_statement_import",
        "import_bank_statement",
        "view_management_reports",
    )
    page = read_bank_statement_rows.compute_bank_statement_rows_list(
        session,
        company_id=company_id,
        import_id=import_id,
        limit=limit,
    )
    return bank_statement_rows_list_to_dict(page)
