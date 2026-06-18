"""FASTAPI-REACT-43 — read-only year-end close history DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from models import User, YearEndClose


@dataclass(frozen=True, slots=True)
class YearEndCloseListRow:
    id: int
    fiscal_year: str
    start_date: datetime.date
    end_date: datetime.date
    status: str
    closed_by_name: str | None
    closed_at: datetime.datetime
    notes: str | None
    period_count: int
    allocation_count: int
    net_income_snapshot: Decimal
    re_balance_at_close: Decimal
    is_void: bool
    voided_by_name: str | None
    voided_at: datetime.datetime | None
    void_reason: str | None
    company_id: int


@dataclass(frozen=True, slots=True)
class YearEndClosesListPage:
    rows: tuple[YearEndCloseListRow, ...]
    row_count: int
    company_id: int


def _user_name_map(session: Session) -> dict[int, str]:
    return {
        user.id: user.display_name or user.username
        for user in session.query(User).all()
    }


def compute_year_end_closes_list(
    session: Session,
    *,
    company_id: int,
) -> YearEndClosesListPage:
    users = _user_name_map(session)
    closes = (
        session.query(YearEndClose)
        .filter(YearEndClose.company_id == company_id)
        .order_by(YearEndClose.fiscal_year.desc(), YearEndClose.id.desc())
        .all()
    )
    rows = tuple(
        YearEndCloseListRow(
            id=close.id,
            fiscal_year=close.fiscal_year,
            start_date=close.start_date,
            end_date=close.end_date,
            status=close.status,
            closed_by_name=users.get(close.closed_by_id) if close.closed_by_id else None,
            closed_at=close.closed_at,
            notes=close.notes,
            period_count=close.period_count,
            allocation_count=close.allocation_count,
            net_income_snapshot=close.net_income_snapshot,
            re_balance_at_close=close.re_balance_at_close,
            is_void=bool(close.is_void),
            voided_by_name=users.get(close.voided_by_id) if close.voided_by_id else None,
            voided_at=close.voided_at,
            void_reason=close.void_reason,
            company_id=company_id,
        )
        for close in closes
    )
    return YearEndClosesListPage(
        rows=rows,
        row_count=len(rows),
        company_id=company_id,
    )
