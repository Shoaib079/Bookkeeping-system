"""Read-only backup inventory endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import backup_status_page_to_dict
from services import read_backup_status
from services.context import RequestContext

router = APIRouter(tags=["backup-status"])


@router.get(
    "",
    summary="Backup status",
    description=(
        "Local backup inventory and database size snapshot (owner read). "
        "Backup create/restore actions remain Streamlit-only."
    ),
)
def get_backup_status(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "manage_backup",
    )
    page = read_backup_status.compute_backup_status_page(
        session,
        company_id=company_id,
    )
    return backup_status_page_to_dict(page)
