"""Shared API permission and company guards."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from services import permissions as perms
from services.context import RequestContext
from services.permissions import PermissionDenied
from services.user_access import PERMISSION_REGISTRY

_FALLBACK_PERMISSION = "view_management_reports"


def _registered_preferences(*preferred: str) -> tuple[str, ...]:
    return tuple(key for key in preferred if key in PERMISSION_REGISTRY)


def require_company_read_access(
    session: Session,
    context: RequestContext,
    *preferred_permissions: str,
) -> int:
    """Enforce membership, company scope, and a read permission with fallback."""
    try:
        perms.require_company_membership(session, context)
        company_id = perms.require_company(context)
        registered = _registered_preferences(*preferred_permissions)
        if not registered:
            perms.require_permission(context, _FALLBACK_PERMISSION)
        elif not any(context.can(key) for key in registered):
            perms.require_permission(context, registered[0])
        return company_id
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        msg = str(exc)
        if "require_company_membership" in msg:
            raise HTTPException(status_code=403, detail=msg) from exc
        raise HTTPException(status_code=400, detail=msg) from exc
