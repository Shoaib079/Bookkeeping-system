"""Read-only company settings endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import company_settings_page_to_dict
from services import read_company_settings
from services.context import RequestContext

router = APIRouter(tags=["company-settings"])


@router.get(
    "",
    summary="Company settings",
    description=(
        "Owner-facing company profile and financial settings snapshot. "
        "Settings writes remain Streamlit-only."
    ),
)
def get_company_settings(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "manage_settings",
    )
    page = read_company_settings.compute_company_settings_page(
        session,
        company_id=company_id,
    )
    return company_settings_page_to_dict(page)
