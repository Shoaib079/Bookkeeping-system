"""FASTAPI-REACT-22 — read-only bank accounts list DTOs and compute."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import BankAccount


@dataclass(frozen=True, slots=True)
class BankAccountListRow:
    id: int
    name: str
    bank_name: str | None
    kind: str
    currency: str | None
    is_active: bool
    company_id: int


@dataclass(frozen=True, slots=True)
class BankAccountsListPage:
    rows: tuple[BankAccountListRow, ...]
    row_count: int


def compute_bank_accounts_list(
    session: Session,
    *,
    company_id: int,
    active_only: bool = True,
    exclude_kind: str | None = None,
    kind: str | None = None,
) -> BankAccountsListPage:
    query = (
        session.query(BankAccount)
        .filter(BankAccount.company_id == company_id)
        .order_by(BankAccount.name, BankAccount.id)
    )
    if active_only:
        query = query.filter(BankAccount.is_active == True)  # noqa: E712
    if exclude_kind:
        query = query.filter(BankAccount.kind != exclude_kind)
    if kind:
        query = query.filter(BankAccount.kind == kind)
    rows = tuple(
        BankAccountListRow(
            id=account.id,
            name=account.name,
            bank_name=account.bank_name,
            kind=account.kind or "bank",
            currency=account.currency,
            is_active=bool(account.is_active),
            company_id=company_id,
        )
        for account in query.all()
    )
    return BankAccountsListPage(rows=rows, row_count=len(rows))
