"""Member roster queries and filters — Phase 14D-F."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

import pandas as pd

from models import CompanyUser, User

from registry.company_members import COMPANY_ROLES


@dataclass(frozen=True)
class RosterEntry:
    membership: CompanyUser
    user: User
    username: str
    display_name: str
    role: str
    status: str
    last_login_label: str
    invited_by_label: str
    member_since_label: str


@dataclass(frozen=True)
class MemberStats:
    total: int
    active: int
    inactive: int
    by_role: dict[str, int]


def format_datetime_label(value: datetime.datetime | None) -> str:
    if not value:
        return "—"
    if isinstance(value, datetime.datetime) and value.tzinfo:
        value = value.replace(tzinfo=None)
    return value.strftime("%d %b %Y %H:%M")


def query_company_roster(session, company_id: int) -> list[RosterEntry]:
    rows = (
        session.query(CompanyUser, User)
        .join(User, CompanyUser.user_id == User.id)
        .filter(CompanyUser.company_id == company_id)
        .order_by(User.username)
        .all()
    )
    inviter_ids = {m.invited_by_id for m, _ in rows if m.invited_by_id}
    inviter_labels: dict[int, str] = {}
    if inviter_ids:
        for inv in session.query(User).filter(User.id.in_(inviter_ids)).all():
            inviter_labels[inv.id] = inv.display_name or inv.username

    entries: list[RosterEntry] = []
    for membership, user in rows:
        entries.append(
            RosterEntry(
                membership=membership,
                user=user,
                username=user.username,
                display_name=user.display_name or user.username,
                role=membership.role,
                status="Active" if membership.is_active else "Inactive",
                last_login_label=format_datetime_label(user.last_login),
                invited_by_label=inviter_labels.get(membership.invited_by_id, "—"),
                member_since_label=format_datetime_label(membership.created_at),
            )
        )
    return entries


def compute_member_stats(entries: list[RosterEntry]) -> MemberStats:
    by_role: dict[str, int] = {r: 0 for r in COMPANY_ROLES}
    active = inactive = 0
    for e in entries:
        if e.membership.is_active:
            active += 1
        else:
            inactive += 1
        by_role[e.role] = by_role.get(e.role, 0) + 1
    return MemberStats(
        total=len(entries),
        active=active,
        inactive=inactive,
        by_role=by_role,
    )


def filter_roster_entries(
    entries: list[RosterEntry],
    *,
    role: str = "all",
    status: str = "all",
    search: str = "",
) -> list[RosterEntry]:
    q = (search or "").strip().lower()
    out: list[RosterEntry] = []
    for e in entries:
        if role != "all" and e.role != role:
            continue
        if status == "active_only" and not e.membership.is_active:
            continue
        if status == "inactive_only" and e.membership.is_active:
            continue
        if q and q not in e.username.lower() and q not in e.display_name.lower():
            continue
        out.append(e)
    return out


def roster_to_dataframe(entries: list[RosterEntry]) -> pd.DataFrame:
    if not entries:
        return pd.DataFrame(
            columns=[
                "Username",
                "Display Name",
                "Role",
                "Status",
                "Last Login",
                "Added By",
                "Member Since",
            ]
        )
    return pd.DataFrame(
        [
            {
                "Username": e.username,
                "Display Name": e.display_name,
                "Role": e.role.title(),
                "Status": e.status,
                "Last Login": e.last_login_label,
                "Added By": e.invited_by_label,
                "Member Since": e.member_since_label,
            }
            for e in entries
        ]
    )


def company_overview_dict(
    *,
    company_name: str,
    company_slug: str,
    settings: dict[str, Any],
    stats: MemberStats,
) -> dict[str, str]:
    role_bits = ", ".join(
        f"{r.title()} {stats.by_role.get(r, 0)}"
        for r in COMPANY_ROLES
        if stats.by_role.get(r, 0)
    ) or "—"
    return {
        "company_name": company_name or "—",
        "slug": company_slug or "—",
        "currency": settings.get("currency", "—"),
        "financial_year": str(settings.get("financial_year", "—")),
        "tax_rate": f"{float(settings.get('tax_rate', 0)):g}%",
        "members_active": str(stats.active),
        "members_inactive": str(stats.inactive),
        "members_by_role": role_bits,
    }
