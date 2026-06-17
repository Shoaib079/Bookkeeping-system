"""FASTAPI-REACT-23 — read-only bank statement row list DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import BankStatementImport, BankStatementRow

DEFAULT_MATCHABLE_STATUSES = frozenset({"staging", "duplicate_flagged"})
_LIST_LIMIT_MAX = 200


@dataclass(frozen=True, slots=True)
class BankStatementRowListItem:
    id: int
    import_row_index: int
    date: datetime.date | None
    description: str
    amount: float
    status: str
    currency: str
    bank_statement_import_id: int
    company_id: int


@dataclass(frozen=True, slots=True)
class BankStatementRowsListPage:
    rows: tuple[BankStatementRowListItem, ...]
    row_count: int


def compute_bank_statement_rows_list(
    session: Session,
    *,
    company_id: int,
    statuses: frozenset[str] | None = None,
    import_id: int | None = None,
    limit: int = 100,
) -> BankStatementRowsListPage:
    effective_statuses = statuses or DEFAULT_MATCHABLE_STATUSES
    capped_limit = min(max(limit, 1), _LIST_LIMIT_MAX)
    query = (
        session.query(BankStatementRow, BankStatementImport)
        .join(
            BankStatementImport,
            BankStatementRow.bank_statement_import_id == BankStatementImport.id,
        )
        .filter(BankStatementImport.company_id == company_id)
        .filter(BankStatementRow.status.in_(effective_statuses))
        .filter(BankStatementRow.parsed_successfully == True)  # noqa: E712
        .order_by(BankStatementRow.date.desc(), BankStatementRow.id.desc())
    )
    if import_id is not None:
        query = query.filter(BankStatementImport.id == import_id)
    query = query.limit(capped_limit)
    rows = tuple(
        BankStatementRowListItem(
            id=row.id,
            import_row_index=row.import_row_index,
            date=row.date,
            description=row.description or "",
            amount=float(row.amount or 0),
            status=row.status,
            currency=row.currency,
            bank_statement_import_id=row.bank_statement_import_id,
            company_id=company_id,
        )
        for row, _import in query.all()
    )
    return BankStatementRowsListPage(rows=rows, row_count=len(rows))
