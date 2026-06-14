"""FASTAPI-P0.4 — permission boundary (Streamlit-free)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import CompanyUser
from services.context import RequestContext

_MEMBERSHIP_REQUIRED_MSG = (
    "require_company_membership(): user is not an active member of this company."
)


class PermissionDenied(RuntimeError):
    """Raised when require_permission denies an action."""


def check_permission(context: RequestContext, action: str) -> bool:
    """Authorization check — mirrors RequestContext.can / legacy _can resolution."""
    return context.can(action)


def require_permission(context: RequestContext, action: str) -> None:
    """Fail loud when the actor may not perform *action*."""
    if not check_permission(context, action):
        raise PermissionDenied(f"Permission denied: {action}")


def require_company(context: RequestContext) -> int:
    """Tenant scoping — mirrors current_company_required() fail-loud semantics."""
    return context.require_company_id()


def require_company_membership(session: Session, context: RequestContext) -> str:
    """Verify active CompanyUser membership; return membership role."""
    company_id = require_company(context)
    row = (
        session.query(CompanyUser.role)
        .filter(
            CompanyUser.company_id == company_id,
            CompanyUser.user_id == context.user_id,
            CompanyUser.is_active.is_(True),
        )
        .first()
    )
    if not row:
        raise RuntimeError(_MEMBERSHIP_REQUIRED_MSG)
    return row[0]
