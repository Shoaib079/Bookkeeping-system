"""FASTAPI-P0.2-H — read-only chart of accounts list DTOs and compute."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import ChartOfAccounts


@dataclass(frozen=True, slots=True)
class CoaRow:
    id: int
    account_code: str
    account_name: str
    account_type: str
    currency: str | None
    is_active: bool
    company_id: int


@dataclass(frozen=True, slots=True)
class CoaListPage:
    rows: tuple[CoaRow, ...]
    row_count: int


def compute_chart_of_accounts_list(
    session: Session,
    *,
    company_id: int,
    active_only: bool = True,
) -> CoaListPage:
    query = (
        session.query(ChartOfAccounts)
        .filter(ChartOfAccounts.company_id == company_id)
        .order_by(ChartOfAccounts.account_code)
    )
    if active_only:
        query = query.filter(ChartOfAccounts.is_active == True)  # noqa: E712
    rows = tuple(
        CoaRow(
            id=account.id,
            account_code=account.account_code,
            account_name=account.account_name,
            account_type=account.account_type,
            currency=account.currency,
            is_active=bool(account.is_active),
            company_id=company_id,
        )
        for account in query.all()
    )
    return CoaListPage(rows=rows, row_count=len(rows))
