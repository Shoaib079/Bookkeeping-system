"""FASTAPI-P0.1 — explicit request context (no Streamlit dependency)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from services import user_access as ua

_COMPANY_REQUIRED_MSG = (
    "current_company_required(): no active_company_id in session. "
    "This call reached a company-scoped query before Gate 2 was satisfied."
)


def legacy_permissions_for_role(role: str | None) -> frozenset[str]:
    """Permissions implied by LEGACY_PERMISSION_MATRIX when no company context."""
    if not role:
        return frozenset()
    return frozenset(
        key for key, roles in ua.LEGACY_PERMISSION_MATRIX.items() if role in roles
    )


def resolve_effective_permissions_for_context(
    session: Session,
    *,
    user_id: int,
    company_id: int | None,
    membership_role: str | None,
    fallback_role: str | None,
) -> frozenset[str]:
    """Mirror app._can permission resolution without Streamlit session cache."""
    if company_id is not None:
        view = ua.effective_permissions(
            session,
            company_id,
            user_id,
            membership_role=membership_role,
        )
        return view.effective_keys
    role = membership_role or fallback_role
    return legacy_permissions_for_role(role)


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Explicit caller identity for service-layer calls (replaces ambient session)."""

    user_id: int
    company_id: int | None
    role: str | None
    effective_permissions: frozenset[str]

    def can(self, action: str) -> bool:
        return action in self.effective_permissions

    def require_company_id(self) -> int:
        """Match current_company_required() fail-loud semantics."""
        if self.company_id is None:
            raise RuntimeError(_COMPANY_REQUIRED_MSG)
        return self.company_id


def build_request_context(
    session: Session,
    *,
    user_id: int,
    company_id: int | None,
    membership_role: str | None,
    fallback_role: str | None,
) -> RequestContext:
    """Construct RequestContext from explicit identity fields."""
    role = membership_role or fallback_role
    perms = resolve_effective_permissions_for_context(
        session,
        user_id=user_id,
        company_id=company_id,
        membership_role=membership_role,
        fallback_role=fallback_role,
    )
    return RequestContext(
        user_id=user_id,
        company_id=company_id,
        role=role,
        effective_permissions=perms,
    )
