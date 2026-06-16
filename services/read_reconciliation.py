"""FASTAPI-P0.2-D — read-only bank statement readiness / tie-out."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.orm import Session

from models import BankStatementImport, BankStatementRow
from services.money import money_to_float

TIE_OUT_TOLERANCE = 0.01
TERMINAL_ROW_STATUSES = frozenset({"posted", "skipped", "voided"})
NON_TERMINAL_ROW_STATUSES = frozenset({"staging", "duplicate_flagged", "parse_error"})

TieOutState = Literal["ok", "mismatch", "unavailable"]
TriState = Literal["ok", "attention", "unavailable"]


def statement_row_signed_amount(row) -> float:
    """Credits increase balance; debits decrease (signed movement)."""
    if row.credit_amount:
        return money_to_float(row.credit_amount)
    if row.debit_amount:
        return -money_to_float(row.debit_amount)
    return 0.0


def statement_row_signed_total(rows) -> float:
    return money_to_float(sum(statement_row_signed_amount(r) for r in rows))


@dataclass(frozen=True, slots=True)
class TieOutStatus:
    state: TieOutState
    available: bool
    declared_movement: float | None
    row_signed_total: float
    delta: float | None


@dataclass(frozen=True, slots=True)
class ReadinessCounts:
    remaining_rows: int
    review_pending: int
    failed_blocked: int
    row_counts_by_status: dict[str, int]


@dataclass(frozen=True, slots=True)
class ReadinessBlocker:
    kind: str
    count: int


@dataclass(frozen=True, slots=True)
class StatementReadiness:
    import_id: int
    file_name: str
    period: str
    company_id: int
    complete: bool
    complete_tri: TriState
    reconciled: bool
    reconciled_tri: TriState
    tie_out: TieOutStatus
    counts: ReadinessCounts
    drill_section: str
    blockers: tuple[ReadinessBlocker, ...]

    def to_dict(self) -> dict[str, Any]:
        """Backward-compatible dict for Streamlit banking UI."""
        return {
            "import_id": self.import_id,
            "file_name": self.file_name,
            "period": self.period,
            "complete": self.complete,
            "complete_tri": self.complete_tri,
            "reconciled": self.reconciled,
            "reconciled_tri": self.reconciled_tri,
            "tie_out": self.tie_out.state,
            "tie_out_available": self.tie_out.available,
            "declared_movement": self.tie_out.declared_movement,
            "row_signed_total": self.tie_out.row_signed_total,
            "tie_out_delta": self.tie_out.delta,
            "remaining_rows": self.counts.remaining_rows,
            "review_pending": self.counts.review_pending,
            "failed_blocked": self.counts.failed_blocked,
            "row_counts_by_status": dict(self.counts.row_counts_by_status),
            "drill_section": self.drill_section,
            "company_id": self.company_id,
        }


def _load_import_rows(
    session: Session,
    import_record: BankStatementImport,
    *,
    rows: list | None,
) -> list:
    if rows is not None:
        return rows
    return (
        session.query(BankStatementRow)
        .filter_by(bank_statement_import_id=import_record.id)
        .order_by(BankStatementRow.import_row_index)
        .all()
    )


def _format_period(import_record: BankStatementImport) -> str:
    if import_record.start_date and import_record.end_date:
        return f"{import_record.start_date} – {import_record.end_date}"
    if import_record.start_date:
        return str(import_record.start_date)
    return ""


def compute_statement_readiness(
    session: Session,
    import_record: BankStatementImport,
    *,
    company_id: int,
    rows: list | None = None,
) -> StatementReadiness | None:
    """Read-only per-statement workflow + tie-out readiness (advisory only)."""
    imp = import_record
    if imp.company_id != company_id:
        return None

    rows = _load_import_rows(session, imp, rows=rows)
    by_status: dict[str, int] = {}
    for row in rows:
        by_status[row.status] = by_status.get(row.status, 0) + 1

    non_terminal = sum(by_status.get(s, 0) for s in NON_TERMINAL_ROW_STATUSES)
    complete = non_terminal == 0
    remaining_rows = by_status.get("staging", 0) + by_status.get("duplicate_flagged", 0)
    review_pending = by_status.get("duplicate_flagged", 0)
    failed_blocked = by_status.get("parse_error", 0)

    has_start = imp.starting_balance is not None
    has_end = imp.ending_balance is not None
    tie_out_available = has_start and has_end
    row_signed_total = statement_row_signed_total(rows)
    declared_movement: float | None = None
    tie_out_delta: float | None = None
    if tie_out_available:
        declared_movement = money_to_float(
            money_to_float(imp.ending_balance) - money_to_float(imp.starting_balance)
        )
        tie_out_delta = money_to_float(declared_movement - row_signed_total)
        tie_out_state: TieOutState = (
            "ok"
            if abs(tie_out_delta) < TIE_OUT_TOLERANCE
            else "mismatch"
        )
    else:
        tie_out_state = "unavailable"

    reconciled = complete and tie_out_available and tie_out_state == "ok"
    if not tie_out_available:
        reconciled_tri: TriState = "unavailable"
    elif reconciled:
        reconciled_tri = "ok"
    else:
        reconciled_tri = "attention"

    drill_section = "review" if (review_pending or failed_blocked) else "match"

    blockers: list[ReadinessBlocker] = []
    if remaining_rows:
        blockers.append(ReadinessBlocker(kind="remaining", count=remaining_rows))
    if review_pending:
        blockers.append(ReadinessBlocker(kind="review_pending", count=review_pending))
    if failed_blocked:
        blockers.append(ReadinessBlocker(kind="failed_blocked", count=failed_blocked))
    if tie_out_state == "mismatch":
        blockers.append(ReadinessBlocker(kind="tie_out_mismatch", count=1))

    return StatementReadiness(
        import_id=imp.id,
        file_name=imp.file_name,
        period=_format_period(imp),
        company_id=imp.company_id,
        complete=complete,
        complete_tri="ok" if complete else "attention",
        reconciled=reconciled,
        reconciled_tri=reconciled_tri,
        tie_out=TieOutStatus(
            state=tie_out_state,
            available=tie_out_available,
            declared_movement=declared_movement,
            row_signed_total=row_signed_total,
            delta=tie_out_delta,
        ),
        counts=ReadinessCounts(
            remaining_rows=remaining_rows,
            review_pending=review_pending,
            failed_blocked=failed_blocked,
            row_counts_by_status=by_status,
        ),
        drill_section=drill_section,
        blockers=tuple(blockers),
    )


def compute_company_statement_readiness(
    session: Session,
    company_id: int,
    *,
    limit: int = 10,
) -> tuple[StatementReadiness, ...]:
    """Recent imports with per-statement readiness (company-scoped)."""
    imports = (
        session.query(BankStatementImport)
        .filter(BankStatementImport.company_id == company_id)
        .order_by(BankStatementImport.created_at.desc())
        .limit(limit)
        .all()
    )
    out: list[StatementReadiness] = []
    for imp in imports:
        readiness = compute_statement_readiness(
            session, imp, company_id=company_id,
        )
        if readiness is not None:
            out.append(readiness)
    return tuple(out)
