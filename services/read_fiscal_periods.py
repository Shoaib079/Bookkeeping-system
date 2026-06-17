"""FASTAPI-REACT-23 — read-only fiscal periods list DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import FiscalPeriod


@dataclass(frozen=True, slots=True)
class FiscalPeriodListRow:
    id: int
    name: str
    start_date: datetime.date
    end_date: datetime.date
    is_closed: bool
    company_id: int


@dataclass(frozen=True, slots=True)
class FiscalPeriodsListPage:
    rows: tuple[FiscalPeriodListRow, ...]
    row_count: int


def compute_fiscal_periods_list(
    session: Session,
    *,
    company_id: int,
    open_only: bool = False,
    closed_only: bool = False,
) -> FiscalPeriodsListPage:
    query = (
        session.query(FiscalPeriod)
        .filter(FiscalPeriod.company_id == company_id)
        .order_by(FiscalPeriod.end_date.desc(), FiscalPeriod.id.desc())
    )
    if open_only:
        query = query.filter(FiscalPeriod.is_closed == False)  # noqa: E712
    elif closed_only:
        query = query.filter(FiscalPeriod.is_closed == True)  # noqa: E712
    rows = tuple(
        FiscalPeriodListRow(
            id=period.id,
            name=period.name,
            start_date=period.start_date,
            end_date=period.end_date,
            is_closed=bool(period.is_closed),
            company_id=company_id,
        )
        for period in query.all()
    )
    return FiscalPeriodsListPage(rows=rows, row_count=len(rows))
