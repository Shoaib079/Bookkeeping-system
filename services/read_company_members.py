"""FASTAPI-REACT-37 — read-only company member roster DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from registry.member_roster import compute_member_stats, query_company_roster


@dataclass(frozen=True, slots=True)
class CompanyMemberListRow:
    membership_id: int
    user_id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    last_login: datetime.datetime | None
    invited_by: str
    member_since: datetime.datetime | None
    company_id: int


@dataclass(frozen=True, slots=True)
class CompanyMemberStats:
    total: int
    active: int
    inactive: int
    by_role: dict[str, int]


@dataclass(frozen=True, slots=True)
class CompanyMembersPage:
    rows: tuple[CompanyMemberListRow, ...]
    row_count: int
    stats: CompanyMemberStats
    company_id: int


def _naive_dt(value: datetime.datetime | None) -> datetime.datetime | None:
    if value is None:
        return None
    if value.tzinfo:
        return value.replace(tzinfo=None)
    return value


def compute_company_members_page(
    session: Session,
    *,
    company_id: int,
) -> CompanyMembersPage:
    entries = query_company_roster(session, company_id)
    stats = compute_member_stats(entries)
    rows = tuple(
        CompanyMemberListRow(
            membership_id=entry.membership.id,
            user_id=entry.user.id,
            username=entry.username,
            display_name=entry.display_name,
            role=entry.role,
            is_active=bool(entry.membership.is_active),
            last_login=_naive_dt(entry.user.last_login),
            invited_by=entry.invited_by_label,
            member_since=_naive_dt(entry.membership.created_at),
            company_id=company_id,
        )
        for entry in entries
    )
    return CompanyMembersPage(
        rows=rows,
        row_count=len(rows),
        stats=CompanyMemberStats(
            total=stats.total,
            active=stats.active,
            inactive=stats.inactive,
            by_role=dict(stats.by_role),
        ),
        company_id=company_id,
    )
