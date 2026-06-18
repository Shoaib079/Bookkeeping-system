"""FASTAPI-REACT-44 — read-only my-account profile DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Company, User
from services import auth_profile


@dataclass(frozen=True, slots=True)
class MyAccountCompanyRow:
    company_id: int
    company_name: str
    role: str
    is_default: bool


@dataclass(frozen=True, slots=True)
class MyAccountPage:
    user_id: int
    username: str
    display_name: str | None
    email: str | None
    phone: str | None
    company_role: str | None
    active_company_id: int | None
    active_company_name: str | None
    member_since: datetime.datetime | None
    last_login: datetime.datetime | None
    companies: tuple[MyAccountCompanyRow, ...]


def compute_my_account_page(
    session: Session,
    *,
    user_id: int,
    company_id: int | None,
    company_role: str | None,
) -> MyAccountPage:
    user = session.get(User, user_id)
    if user is None:
        raise ValueError(f"user not found: {user_id}")

    active_company_name: str | None = None
    if company_id is not None:
        company = session.get(Company, company_id)
        active_company_name = company.name if company is not None else None

    companies = tuple(
        MyAccountCompanyRow(
            company_id=row.company_id,
            company_name=row.company_name,
            role=row.role,
            is_default=row.is_default,
        )
        for row in auth_profile.list_user_accessible_companies(session, user_id)
    )

    return MyAccountPage(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email,
        phone=user.phone,
        company_role=company_role,
        active_company_id=company_id,
        active_company_name=active_company_name,
        member_since=user.created_at,
        last_login=user.last_login,
        companies=companies,
    )
