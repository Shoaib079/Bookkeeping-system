"""Read-only reconciliation health endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import recon_health_to_dict
from services import read_recon_health
from services.context import RequestContext

router = APIRouter(tags=["reconciliation-health"])


@router.get(
    "/health",
    summary="Reconciliation health",
    description=(
        "GL-vs-subledger checks for AR/AP, optional company credit card, "
        "bank stored-vs-derived balances, and chart-of-accounts cache drift."
    ),
)
def get_recon_health(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_management_reports",
    )
    page = read_recon_health.compute_recon_health(
        session,
        company_id=company_id,
    )
    return recon_health_to_dict(page)
