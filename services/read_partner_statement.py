"""FASTAPI-P0.2-F — read-only partner statement DTOs and compute."""

from __future__ import annotations

import datetime
from typing import Callable

from sqlalchemy.orm import Session

from models import ChartOfAccounts
from registry.partner_statement import (
    AllPartnersSettlementSummary,
    PartnerStatementData,
    build_all_partners_settlement_summary,
    build_partner_statement,
)
from services import read_balances as rb

BalanceForPeriodFn = Callable[
    [Session, ChartOfAccounts, datetime.date, datetime.date], float
]


def balance_for_period_fn(company_id: int) -> BalanceForPeriodFn:
    """Company-scoped balance callback for partner statement compute."""

    def _fn(
        session: Session,
        account: ChartOfAccounts,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> float:
        return rb.calculate_account_balance_for_period(
            session,
            account,
            start_date,
            end_date,
            company_id=company_id,
        )

    return _fn


def compute_partner_statement(
    session: Session,
    *,
    company_id: int,
    partner_id: int,
    from_date: datetime.date,
    to_date: datetime.date,
) -> PartnerStatementData | None:
    """Single-partner settlement statement with explicit company scope."""
    return build_partner_statement(
        session,
        partner_id,
        from_date,
        to_date,
        balance_for_period_fn(company_id),
        company_id=company_id,
    )


def compute_all_partners_settlement_summary(
    session: Session,
    *,
    company_id: int,
    from_date: datetime.date,
    to_date: datetime.date,
    include_inactive: bool = True,
    hide_settled: bool = False,
) -> AllPartnersSettlementSummary | None:
    """All-partners rollup with explicit company scope."""
    return build_all_partners_settlement_summary(
        session,
        from_date,
        to_date,
        balance_for_period_fn(company_id),
        company_id=company_id,
        include_inactive=include_inactive,
        hide_settled=hide_settled,
    )
