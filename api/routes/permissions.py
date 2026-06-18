"""Read-only permission overview endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import (
    effective_permissions_page_to_dict,
    permission_members_page_to_dict,
)
from services import read_permissions
from services.context import RequestContext

router = APIRouter(tags=["permissions"])


def _require_permissions_read(session: Session, context: RequestContext) -> int:
    return require_company_read_access(
        session,
        context,
        "manage_permissions",
    )


@router.get(
    "/members",
    summary="Permission members",
    description="Active members available for permission review (owner read).",
)
def get_permission_members(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = _require_permissions_read(session, context)
    page = read_permissions.compute_permission_members_page(
        session,
        company_id=company_id,
    )
    return permission_members_page_to_dict(page)


@router.get(
    "/effective",
    summary="Effective permissions",
    description="Template/grant/deny provenance for one member (owner read).",
)
def get_effective_permissions(
    user_id: Annotated[int, Query(ge=1, description="Target member user id")],
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = _require_permissions_read(session, context)
    members = read_permissions.compute_permission_members_page(
        session,
        company_id=company_id,
    )
    if not any(row.user_id == user_id for row in members.rows):
        raise HTTPException(status_code=404, detail="Member not found for this company.")
    page = read_permissions.compute_effective_permissions_page(
        session,
        company_id=company_id,
        user_id=user_id,
    )
    return effective_permissions_page_to_dict(page)
