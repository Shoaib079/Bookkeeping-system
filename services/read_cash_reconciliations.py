"""FASTAPI-REACT-46 — read-only daily cash reconciliation history DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from models import ChartOfAccounts, DailyCashReconciliation, User


@dataclass(frozen=True, slots=True)
class CashReconciliationListRow:
    id: int
    date: datetime.date
    cash_account_name: str | None
    expected_cash: Decimal
    actual_cash: Decimal
    difference: Decimal
    variance_type: str
    status: str
    submitted_by_name: str | None
    approved_by_name: str | None
    journal_entry_id: int | None
    is_void: bool
    company_id: int


@dataclass(frozen=True, slots=True)
class CashReconciliationsListPage:
    rows: tuple[CashReconciliationListRow, ...]
    row_count: int
    company_id: int
    start_date: datetime.date | None
    end_date: datetime.date | None
    status: str | None


def _user_name_map(session: Session) -> dict[int, str]:
    return {
        user.id: user.display_name or user.username
        for user in session.query(User).all()
    }


def _account_name_map(session: Session, company_id: int) -> dict[int, str]:
    return {
        account.id: account.account_name
        for account in session.query(ChartOfAccounts)
        .filter(ChartOfAccounts.company_id == company_id)
        .all()
    }


def compute_cash_reconciliations_list(
    session: Session,
    *,
    company_id: int,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
    status: str | None = None,
) -> CashReconciliationsListPage:
    users = _user_name_map(session)
    accounts = _account_name_map(session, company_id)
    query = (
        session.query(DailyCashReconciliation)
        .filter(DailyCashReconciliation.company_id == company_id)
        .order_by(
            DailyCashReconciliation.date.desc(),
            DailyCashReconciliation.id.desc(),
        )
    )
    if start_date is not None:
        query = query.filter(DailyCashReconciliation.date >= start_date)
    if end_date is not None:
        query = query.filter(DailyCashReconciliation.date <= end_date)
    if status and status != "all":
        query = query.filter(DailyCashReconciliation.status == status)

    rows = tuple(
        CashReconciliationListRow(
            id=recon.id,
            date=recon.date,
            cash_account_name=accounts.get(recon.cash_account_id),
            expected_cash=recon.expected_cash,
            actual_cash=recon.actual_cash,
            difference=recon.difference,
            variance_type=recon.variance_type,
            status=recon.status,
            submitted_by_name=users.get(recon.created_by_id),
            approved_by_name=users.get(recon.reconciled_by_id)
            if recon.reconciled_by_id
            else None,
            journal_entry_id=recon.journal_entry_id,
            is_void=bool(recon.is_void),
            company_id=company_id,
        )
        for recon in query.all()
    )
    return CashReconciliationsListPage(
        rows=rows,
        row_count=len(rows),
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
