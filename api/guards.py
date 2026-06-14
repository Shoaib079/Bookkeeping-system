"""Shared API permission and company guards.

HTTP mapping (P1.3e):
- 401: missing/invalid bearer token (or legacy ``X-User-Id`` when dev fallback enabled)
- 400: ``require_company`` when ``X-Company-Id`` is absent
- 403: membership or permission failure
"""

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


def _enforce_company_access(
    session: Session,
    context: RequestContext,
    *preferred_permissions: str,
    fallback_permission: str,
) -> int:
    try:
        perms.require_company_membership(session, context)
        company_id = perms.require_company(context)
        registered = _registered_preferences(*preferred_permissions)
        if not registered:
            perms.require_permission(context, fallback_permission)
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


def require_company_read_access(
    session: Session,
    context: RequestContext,
    *preferred_permissions: str,
) -> int:
    """Enforce membership, company scope, and a read permission with fallback."""
    return _enforce_company_access(
        session,
        context,
        *preferred_permissions,
        fallback_permission=_FALLBACK_PERMISSION,
    )


def require_company_write_access(
    session: Session,
    context: RequestContext,
    *preferred_permissions: str,
) -> int:
    """Enforce membership, company scope, and a write permission (no read fallback)."""
    if not preferred_permissions:
        raise ValueError("require_company_write_access requires at least one permission")
    return _enforce_company_access(
        session,
        context,
        *preferred_permissions,
        fallback_permission=preferred_permissions[0],
    )
