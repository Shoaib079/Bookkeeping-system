"""Read-only banking reconciliation readiness endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import statement_readiness_list_to_dict
from services import read_reconciliation
from services.context import RequestContext

router = APIRouter(tags=["banking"])


@router.get("/readiness")
def get_banking_readiness(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_banking",
        "view_reconciliation",
        "view_management_reports",
    )
    items = read_reconciliation.compute_company_statement_readiness(
        session,
        company_id,
        limit=limit,
    )
    return statement_readiness_list_to_dict(items)
