"""FASTAPI-P1.3d — identity and company-access views for bearer auth routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models import AppSetting, Company, CompanyUser, User
from sqlalchemy.orm import Session

USER_PREF_LAST_COMPANY_KEY = "last_active_company_id"


def _user_pref(session: Session, user_id: int, key: str, default: str = "") -> str:
    row = session.get(AppSetting, f"user_pref_{user_id}_{key}")
    return row.value if row and row.value is not None else default


def user_identity_dict(user: User) -> dict[str, Any]:
    """Safe identity fields for ``GET /auth/me``."""
    payload: dict[str, Any] = {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_active": bool(user.is_active),
    }
    token_version = getattr(user, "token_version", None)
    if token_version is not None:
        payload["token_version"] = token_version
    return payload


@dataclass(frozen=True)
class UserCompanyAccess:
    company_id: int
    company_name: str
    role: str
    is_default: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "company_name": self.company_name,
            "role": self.role,
            "is_default": self.is_default,
        }


def list_user_accessible_companies(
    session: Session,
    user_id: int,
) -> list[UserCompanyAccess]:
    """Active company memberships for a user (mirrors Streamlit ``_user_company_memberships``)."""
    rows = (
        session.query(CompanyUser, Company)
        .join(Company, CompanyUser.company_id == Company.id)
        .filter(
            CompanyUser.user_id == user_id,
            CompanyUser.is_active.is_(True),
            Company.is_active.is_(True),
        )
        .order_by(Company.name)
        .all()
    )

    default_company_id: int | None = None
    raw_default = _user_pref(session, user_id, USER_PREF_LAST_COMPANY_KEY, "").strip()
    if raw_default:
        try:
            default_company_id = int(raw_default)
        except ValueError:
            default_company_id = None

    accessible_ids = {company.id for _, company in rows}
    if default_company_id not in accessible_ids:
        default_company_id = None

    return [
        UserCompanyAccess(
            company_id=company.id,
            company_name=company.name,
            role=membership.role,
            is_default=company.id == default_company_id,
        )
        for membership, company in rows
    ]
