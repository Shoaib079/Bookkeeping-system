"""Read-only company member roster endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import company_members_page_to_dict
from services import read_company_members
from services.context import RequestContext

router = APIRouter(tags=["members"])


@router.get(
    "",
    summary="Company members",
    description=(
        "Active company membership roster (owner read). "
        "Member management writes remain Streamlit-only."
    ),
)
def get_company_members(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "manage_users",
    )
    page = read_company_members.compute_company_members_page(
        session,
        company_id=company_id,
    )
    return company_members_page_to_dict(page)
