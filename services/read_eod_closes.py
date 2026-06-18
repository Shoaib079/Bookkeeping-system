"""FASTAPI-REACT-45 — read-only end-of-day close history DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import EndOfDayClose, JournalEntry, User


@dataclass(frozen=True, slots=True)
class EodCloseListRow:
    id: int
    date: datetime.date
    status: str
    closed_by_name: str | None
    closed_at: datetime.datetime
    had_warnings: bool
    total_sales: Decimal
    total_expenses: Decimal
    net_cash_movement: Decimal
    recon_status: str | None
    notes_preview: str | None
    is_void: bool
    is_stale: bool
    company_id: int


@dataclass(frozen=True, slots=True)
class EodClosesListPage:
    rows: tuple[EodCloseListRow, ...]
    row_count: int
    company_id: int
    start_date: datetime.date | None
    end_date: datetime.date | None


def _user_name_map(session: Session) -> dict[int, str]:
    return {
        user.id: user.display_name or user.username
        for user in session.query(User).all()
    }


def _eod_is_stale(session: Session, close: EndOfDayClose) -> bool:
    current_count = (
        session.query(func.count(JournalEntry.id))
        .filter(
            JournalEntry.entry_date == close.date,
            JournalEntry.company_id == close.company_id,
        )
        .scalar()
        or 0
    )
    return current_count != close.je_count_snapshot


def _status_label(*, is_void: bool, is_stale: bool) -> str:
    if is_void:
        return "voided"
    if is_stale:
        return "stale"
    return "closed"


def compute_eod_closes_list(
    session: Session,
    *,
    company_id: int,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
) -> EodClosesListPage:
    users = _user_name_map(session)
    query = (
        session.query(EndOfDayClose)
        .filter(EndOfDayClose.company_id == company_id)
        .order_by(EndOfDayClose.date.desc(), EndOfDayClose.id.desc())
    )
    if start_date is not None:
        query = query.filter(EndOfDayClose.date >= start_date)
    if end_date is not None:
        query = query.filter(EndOfDayClose.date <= end_date)

    rows: list[EodCloseListRow] = []
    for close in query.all():
        stale = (not close.is_void) and _eod_is_stale(session, close)
        notes = (close.notes or "").strip()
        rows.append(
            EodCloseListRow(
                id=close.id,
                date=close.date,
                status=_status_label(is_void=bool(close.is_void), is_stale=stale),
                closed_by_name=users.get(close.closed_by_id),
                closed_at=close.closed_at,
                had_warnings=bool(close.had_warnings),
                total_sales=close.total_sales,
                total_expenses=close.total_expenses,
                net_cash_movement=close.net_cash_movement,
                recon_status=close.recon_status,
                notes_preview=notes[:60] if notes else None,
                is_void=bool(close.is_void),
                is_stale=stale,
                company_id=company_id,
            )
        )

    return EodClosesListPage(
        rows=tuple(rows),
        row_count=len(rows),
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
    )
