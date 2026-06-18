"""FASTAPI-REACT-39 — read-only budget vs actual DTOs and compute."""

from __future__ import annotations

import calendar
import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Budget, ChartOfAccounts
from services.read_balances import calculate_account_balance_for_period


@dataclass(frozen=True, slots=True)
class BudgetVsActualRow:
    account_id: int
    account_code: str
    account_name: str
    budgeted: float
    actual: float
    variance: float
    used_pct: float | None
    status: str


@dataclass(frozen=True, slots=True)
class BudgetVsActualPage:
    year: int
    month: int
    month_start: datetime.date
    month_end: datetime.date
    rows: tuple[BudgetVsActualRow, ...]
    row_count: int
    total_budgeted: float
    total_actual: float
    total_variance: float
    company_id: int


def _row_status(budgeted: float, actual: float) -> str:
    if actual > budgeted > 0:
        return "over"
    if budgeted > 0:
        return "on_track"
    return "no_budget"


def compute_budget_vs_actual(
    session: Session,
    *,
    company_id: int,
    year: int,
    month: int,
) -> BudgetVsActualPage:
    month_start = datetime.date(year, month, 1)
    month_end = datetime.date(year, month, calendar.monthrange(year, month)[1])

    budgets = (
        session.query(Budget)
        .filter(
            Budget.company_id == company_id,
            Budget.year == year,
            Budget.month == month,
        )
        .all()
    )
    budget_by_account = {row.account_id: row for row in budgets if row.account_id}

    expense_accounts = (
        session.query(ChartOfAccounts)
        .filter(
            ChartOfAccounts.company_id == company_id,
            ChartOfAccounts.account_type == "Expense",
            ChartOfAccounts.is_active == True,  # noqa: E712
        )
        .order_by(ChartOfAccounts.account_code)
        .all()
    )

    rows: list[BudgetVsActualRow] = []
    total_budgeted = total_actual = 0.0
    for account in expense_accounts:
        actual = calculate_account_balance_for_period(
            session,
            account,
            month_start,
            month_end,
            exclude_refs=["PeriodClose"],
            company_id=company_id,
        )
        budget_row = budget_by_account.get(account.id)
        budgeted = float(budget_row.amount) if budget_row else 0.0
        actual_f = float(actual)
        variance = budgeted - actual_f
        used_pct = round(actual_f / budgeted * 100, 1) if budgeted else None
        rows.append(
            BudgetVsActualRow(
                account_id=account.id,
                account_code=account.account_code,
                account_name=account.account_name,
                budgeted=round(budgeted, 2),
                actual=round(actual_f, 2),
                variance=round(variance, 2),
                used_pct=used_pct,
                status=_row_status(budgeted, actual_f),
            )
        )
        total_budgeted += budgeted
        total_actual += actual_f

    return BudgetVsActualPage(
        year=year,
        month=month,
        month_start=month_start,
        month_end=month_end,
        rows=tuple(rows),
        row_count=len(rows),
        total_budgeted=round(total_budgeted, 2),
        total_actual=round(total_actual, 2),
        total_variance=round(total_budgeted - total_actual, 2),
        company_id=company_id,
    )
