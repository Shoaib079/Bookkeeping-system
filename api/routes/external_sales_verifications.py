"""Read-only external sales verification history endpoint."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import external_sales_verifications_list_to_dict
from services import read_external_sales_verifications
from services.context import RequestContext

router = APIRouter(tags=["external-sales-verifications"])


@router.get(
    "",
    summary="External sales verifications",
    description=(
        "External sales verification history for the active company. "
        "Draft, verify, and void actions remain Streamlit-only."
    ),
)
def get_external_sales_verifications(
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
        "view_external_sales_verification",
    )
    page = read_external_sales_verifications.compute_external_sales_verifications_list(
        session,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
    )
    return external_sales_verifications_list_to_dict(page)
