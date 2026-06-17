"""FASTAPI-REACT-24 — read-only profit allocations list DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import FiscalPeriod, PartnerProfitAllocation
from services.money import money_to_float


@dataclass(frozen=True, slots=True)
class ProfitAllocationListRow:
    id: int
    fiscal_period_id: int
    period_name: str
    allocated_at: datetime.datetime
    total_net_income: float
    is_void: bool
    company_id: int


@dataclass(frozen=True, slots=True)
class ProfitAllocationsListPage:
    rows: tuple[ProfitAllocationListRow, ...]
    row_count: int


def compute_profit_allocations_list(
    session: Session,
    *,
    company_id: int,
    active_only: bool = True,
) -> ProfitAllocationsListPage:
    query = (
        session.query(PartnerProfitAllocation, FiscalPeriod)
        .join(
            FiscalPeriod,
            PartnerProfitAllocation.fiscal_period_id == FiscalPeriod.id,
        )
        .filter(PartnerProfitAllocation.company_id == company_id)
        .order_by(PartnerProfitAllocation.allocated_at.desc(), PartnerProfitAllocation.id.desc())
    )
    if active_only:
        query = query.filter(PartnerProfitAllocation.is_void == False)  # noqa: E712
    rows = tuple(
        ProfitAllocationListRow(
            id=allocation.id,
            fiscal_period_id=allocation.fiscal_period_id,
            period_name=period.name,
            allocated_at=allocation.allocated_at,
            total_net_income=money_to_float(allocation.total_net_income),
            is_void=bool(allocation.is_void),
            company_id=company_id,
        )
        for allocation, period in query.all()
    )
    return ProfitAllocationsListPage(rows=rows, row_count=len(rows))
