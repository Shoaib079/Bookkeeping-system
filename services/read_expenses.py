"""FASTAPI-REACT-26 — read-only expenses list DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import ExpenseRecord
from services.money import money_to_float


@dataclass(frozen=True, slots=True)
class ExpenseListRow:
    id: int
    date: datetime.date
    expense_type: str
    category: str | None
    description: str
    amount: float
    payment_method: str | None
    employee_name: str | None
    is_void: bool
    currency: str | None
    company_id: int


@dataclass(frozen=True, slots=True)
class ExpensesListPage:
    rows: tuple[ExpenseListRow, ...]
    row_count: int


def compute_expenses_list(
    session: Session,
    *,
    company_id: int,
    show_voided: bool = False,
) -> ExpensesListPage:
    query = (
        session.query(ExpenseRecord)
        .filter(ExpenseRecord.company_id == company_id)
        .order_by(ExpenseRecord.date.desc(), ExpenseRecord.id.desc())
    )
    if not show_voided:
        query = query.filter(ExpenseRecord.is_void == False)  # noqa: E712
    rows = tuple(
        ExpenseListRow(
            id=record.id,
            date=record.date,
            expense_type=record.expense_type,
            category=record.category,
            description=record.description or "",
            amount=money_to_float(record.amount),
            payment_method=record.payment_method,
            employee_name=record.employee_name,
            is_void=bool(record.is_void),
            currency=record.currency,
            company_id=company_id,
        )
        for record in query.all()
    )
    return ExpensesListPage(rows=rows, row_count=len(rows))
