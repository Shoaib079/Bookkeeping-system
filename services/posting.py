"""POSTING-SERVICE-01 — GL posting kernel and incremental extraction.

PS-P1: `create_journal_entry` + period/year-end guard (verbatim from app.py).
PS-P2a: `get_account_by_name`, sales `post_*` trio, `card_settlement_on`.
PS-P2b: `resolve_payment_credit_account`, `post_payable_creation`.
PS-P2c-1: `sync_company_cc_subledger`.
PS-P2c-2: `post_expense`, `post_payable_payment`.
PS-P2c-3: `post_purchase`, `resolve_purchase_debit_account`, `purchase_ref_type`.
PS-P3-1: `create_reversing_journal_entry`, `reverse_journal_entries_for`.
PS-P3-2a: `void_expense`, `void_payable`.
PS-P3-2b: `void_sale`.
PS-P3-3a: `linked_purchase_payable`, `void_purchase_linked_payable`.
PS-P3-3b: `void_purchase`.
PS-P4-1: `post_bank_transaction`, `post_bank_transfer`.
PS-P4-2: `void_bank_transaction`.
PS-P5-1: `compute_sale_balance_status`, `post_receivable_payment`.
PS-P5-2: `void_inventory_transaction`.
PS-P5-3: `post_capital_contribution`, `post_owner_drawing`, `post_salary`, `void_equity_movement`.
PS-P5-4: `void_reconciliation`, `void_eod_close`, `void_year_end_close`.
PS-P6-0a: `yec_block_message` (pure TD-POSTING-05 query helper; no callers yet).
PS-P6-1: `post_partner_movement`, `void_partner_movement`.
PS-P6-2: `post_worker_movement`, `void_worker_movement`.
PS-P6-3: `allocate_profit_to_partners`, `void_profit_allocation`, `_allocate_all_pending`.
PS-P6-4: `_get_year_bounds`, `_check_period_continuity`, `close_fiscal_period`, `perform_year_end_close`.

app.py keeps compatibility shims under the original names so all existing
call sites remain behaviourally untouched.

Deliberate deviations from the MIGRATION-READINESS-01 end state —
preserved on purpose and logged in TECH_DEBT (TD-PS-01 / TD-PS-02):

- **Commits internally** (`session.commit()` on success, `session.rollback()`
  before raising) — exactly as the app.py original did. Boundary-owned
  transactions arrive with PS-P2+; changing commit ownership is explicitly
  out of scope for extraction waves.
- **company_id is an explicit parameter** on service functions. app.py shims
  supply it from the ambient session helper, preserving company/session
  behaviour for every legacy caller. `None` keeps the pre-14C unscoped
  behaviour (startup/migration callers).

No Streamlit, no app.py imports — enforced by contract tests.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from typing import Any

from models import (
    BankAccount,
    BankTransaction,
    ChartOfAccounts,
    DailyCashReconciliation,
    EndOfDayClose,
    ExpenseRecord,
    FiscalPeriod,
    InventoryTransaction,
    JournalEntry,
    JournalEntryLine,
    Payable,
    Partner,
    PartnerMovement,
    PartnerProfitAllocation,
    PartnerProfitAllocationLine,
    Product,
    Purchase,
    Sale,
    Worker,
    WorkerMovement,
    YearEndClose,
)
from reconciliation.company_card import (
    CompanyCardError,
    company_card_enabled,
    post_cc_subledger_charge,
    resolve_company_credit_card_account_id,
    reverse_cc_subledgers_for_gl_reference,
    reverse_account_balance_delta,
)
from registry.service import get_setting
from services.commit_modes import (
    PERIOD_CLOSE_FAMILY,
    POST_CASH_SALE_FAMILY,
    POST_EQUITY_MOVEMENT_FAMILY,
    POST_EXPENSE_FAMILY,
    POST_PARTNER_MOVEMENT_FAMILY,
    POST_PAYABLE_PAYMENT_FAMILY,
    POST_PURCHASE_FAMILY,
    POST_RECEIVABLE_PAYMENT_FAMILY,
    POST_WORKER_MOVEMENT_FAMILY,
    PROFIT_ALLOCATION_FAMILY,
    VOID_CASCADE_FAMILY,
    YEAR_END_CLOSE_FAMILY,
    is_boundary_mode,
)

# Pinned by PS-P2b-CHAR — must match registry/locales/transactional.py EN strings.
_CC_DISABLED_MSG = (
    "Company Credit Card is not enabled. Enable it in Banking → Settings first."
)
_CC_GL_MISSING_MSG = "Credit Card Payable GL account is missing."
_CC_NO_CARDS_MSG = (
    "No active company credit card account. Add one under Banking → Accounts."
)
_COMPANY_CC_METHOD = "Credit Card"
_DEFAULT_PURCHASE_GL_DEBIT = "Inventory"  # app.py NAV_INVENTORY default

_PARTNER_REF_TYPES = {
    "CapitalContribution": "PartnerCapital",
    "Drawing":             "PartnerDrawing",
    "Salary":              "PartnerSalary",
    "Advance":             "PartnerAdvance",
    "Repayment":           "PartnerRepayment",
    "AdvanceOffset":       "PartnerAdvanceOffset",
}

_WORKER_REF_TYPES = {
    "Salary": "WorkerSalary",
    "Advance": "WorkerAdvance",
    "Repayment": "WorkerRepayment",
}


# ── FASTAPI-P0.5a — posting result DTOs (additive; legacy returns unchanged) ───


@dataclass(frozen=True, slots=True)
class PostingLineResult:
    account_id: int
    debit: float
    credit: float
    currency: str | None = None
    amount_native: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "debit": self.debit,
            "credit": self.credit,
            "currency": self.currency,
            "amount_native": self.amount_native,
        }


@dataclass(frozen=True, slots=True)
class PostingResult:
    je_id: int
    reference_type: str | None
    reference_id: int | None
    entry_date: datetime.date
    company_id: int | None
    lines: tuple[PostingLineResult, ...]
    currency: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "je_id": self.je_id,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "entry_date": self.entry_date.isoformat(),
            "company_id": self.company_id,
            "currency": self.currency,
            "description": self.description,
            "lines": [ln.to_dict() for ln in self.lines],
        }


@dataclass(frozen=True, slots=True)
class VoidResult:
    voided: bool
    reversal_je_ids: tuple[int, ...]
    cascade: tuple[str, ...]
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "voided": self.voided,
            "reversal_je_ids": list(self.reversal_je_ids),
            "cascade": list(self.cascade),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class PaymentResult:
    je_id: int | None
    applied_amount: float | None
    fx_gain_loss: float | None
    sale_balance_after: float | None
    error: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "je_id": self.je_id,
            "applied_amount": self.applied_amount,
            "fx_gain_loss": self.fx_gain_loss,
            "sale_balance_after": self.sale_balance_after,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class PartnerAllocationLineResult:
    partner_id: int
    share_pct: float
    amount: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "partner_id": self.partner_id,
            "share_pct": self.share_pct,
            "amount": self.amount,
        }


@dataclass(frozen=True, slots=True)
class AllocationResult:
    allocation_id: int | None
    je_id: int | None
    per_partner: tuple[PartnerAllocationLineResult, ...]
    net_income: float | None
    error: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allocation_id": self.allocation_id,
            "je_id": self.je_id,
            "per_partner": [ln.to_dict() for ln in self.per_partner],
            "net_income": self.net_income,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class YearEndCloseResult:
    yec_id: int | None
    warnings: tuple[tuple[str, str], ...]
    error: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "yec_id": self.yec_id,
            "warnings": [list(w) for w in self.warnings],
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class PeriodCloseResult:
    je_id: int
    period_id: int
    net_income: float
    closing_je_id: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "je_id": self.je_id,
            "period_id": self.period_id,
            "net_income": self.net_income,
            "closing_je_id": self.closing_je_id,
        }


def _journal_lines_for_entry(session, entry_id: int) -> list[JournalEntryLine]:
    return (
        session.query(JournalEntryLine)
        .filter_by(journal_entry_id=entry_id)
        .order_by(JournalEntryLine.id)
        .all()
    )


def _reversal_je_ids_for_reference(
    session,
    reference_type: str,
    reference_id: int,
    *,
    company_id: int | None = None,
) -> tuple[int, ...]:
    orig_q = session.query(JournalEntry.id).filter_by(
        reference_type=reference_type,
        reference_id=reference_id,
    )
    if company_id is not None:
        orig_q = orig_q.filter(JournalEntry.company_id == company_id)
    orig_ids = [row[0] for row in orig_q.all()]
    if not orig_ids:
        return ()
    rev_q = session.query(JournalEntry.id).filter(
        JournalEntry.reference_type == "Reversal",
        JournalEntry.reference_id.in_(orig_ids),
    )
    if company_id is not None:
        rev_q = rev_q.filter(JournalEntry.company_id == company_id)
    return tuple(row[0] for row in rev_q.order_by(JournalEntry.id).all())


def posting_result_from_entry(
    session,
    entry: JournalEntry,
    *,
    currency: str | None = None,
) -> PostingResult:
    """Build a PostingResult DTO from a persisted JournalEntry."""
    lines = _journal_lines_for_entry(session, entry.id)
    line_dtos = tuple(
        PostingLineResult(
            account_id=ln.account_id,
            debit=ln.debit or 0.0,
            credit=ln.credit or 0.0,
            currency=ln.currency,
            amount_native=ln.amount_native,
        )
        for ln in lines
    )
    entry_currency = currency or (lines[0].currency if lines else None)
    return PostingResult(
        je_id=entry.id,
        reference_type=entry.reference_type,
        reference_id=entry.reference_id,
        entry_date=entry.entry_date,
        company_id=entry.company_id,
        lines=line_dtos,
        currency=entry_currency,
        description=entry.description,
    )


def period_close_result_from_je(
    je: JournalEntry,
    period: FiscalPeriod,
    *,
    net_income: float,
) -> PeriodCloseResult:
    return PeriodCloseResult(
        je_id=je.id,
        period_id=period.id,
        net_income=net_income,
        closing_je_id=period.closing_je_id or je.id,
    )


def allocation_result_from_post(
    session,
    allocation_id: int | None,
    error: str,
) -> AllocationResult:
    if error or allocation_id is None:
        return AllocationResult(
            allocation_id=allocation_id,
            je_id=None,
            per_partner=(),
            net_income=None,
            error=error or "",
        )
    alloc = session.get(PartnerProfitAllocation, allocation_id)
    if not alloc:
        return AllocationResult(
            allocation_id=allocation_id,
            je_id=None,
            per_partner=(),
            net_income=None,
            error="Allocation not found.",
        )
    partner_lines = (
        session.query(PartnerProfitAllocationLine)
        .filter_by(allocation_id=allocation_id)
        .order_by(PartnerProfitAllocationLine.id)
        .all()
    )
    return AllocationResult(
        allocation_id=alloc.id,
        je_id=alloc.journal_entry_id,
        per_partner=tuple(
            PartnerAllocationLineResult(
                partner_id=ln.partner_id,
                share_pct=ln.share_pct,
                amount=ln.amount,
            )
            for ln in partner_lines
        ),
        net_income=alloc.total_net_income,
        error="",
    )


def year_end_close_result_from_tuple(
    yec_id: int | None,
    warnings: list,
    error: str,
) -> YearEndCloseResult:
    return YearEndCloseResult(
        yec_id=yec_id,
        warnings=tuple((str(k), str(v)) for k, v in warnings),
        error=error or "",
    )


def payment_result_from_receivable_post(
    session,
    sale_id: int,
    *,
    error: str | None = None,
    applied_amount: float | None = None,
) -> PaymentResult:
    if error:
        return PaymentResult(
            je_id=None,
            applied_amount=applied_amount,
            fx_gain_loss=None,
            sale_balance_after=None,
            error=error,
        )
    sale = session.get(Sale, sale_id)
    je = (
        session.query(JournalEntry)
        .filter_by(reference_type="ReceivablePayment", reference_id=sale_id)
        .order_by(JournalEntry.id.desc())
        .first()
    )
    fx_gain_loss = None
    if je:
        fx_gain = get_account_by_name(session, "FX Gain")
        fx_loss = get_account_by_name(session, "FX Loss")
        for ln in _journal_lines_for_entry(session, je.id):
            if fx_gain and ln.account_id == fx_gain.id:
                fx_gain_loss = round(ln.credit or 0.0, 2)
            elif fx_loss and ln.account_id == fx_loss.id:
                fx_gain_loss = round(-(ln.debit or 0.0), 2)
    return PaymentResult(
        je_id=je.id if je else None,
        applied_amount=applied_amount,
        fx_gain_loss=fx_gain_loss,
        sale_balance_after=sale.balance if sale else None,
        error="",
    )


def void_result_from_bool(
    voided: bool,
    *,
    reason: str | None = None,
    reversal_je_ids: tuple[int, ...] = (),
    cascade: tuple[str, ...] = (),
) -> VoidResult:
    return VoidResult(
        voided=voided,
        reversal_je_ids=reversal_je_ids,
        cascade=cascade,
        reason=reason,
    )


def void_result_from_expense_void(
    session,
    expense_id: int,
    voided: bool,
    *,
    void_reason: str | None = None,
    company_id: int | None = None,
) -> VoidResult:
    if not voided:
        return void_result_from_bool(False, reason=void_reason)
    return VoidResult(
        voided=True,
        reversal_je_ids=_reversal_je_ids_for_reference(
            session, "Expense", expense_id, company_id=company_id
        ),
        cascade=(),
        reason=void_reason,
    )


def _get_worker_advance_balance(session, worker_id: int, *, company_id: int | None = None):
    """Verbatim from app.py ``get_worker_advance_balance`` with explicit company_id."""
    q = session.query(WorkerMovement).filter_by(worker_id=worker_id, is_void=False)
    if company_id is not None:
        q = q.filter(WorkerMovement.company_id == company_id)
    movements = q.all()
    bal = 0.0
    for mv in movements:
        if mv.movement_type == "Advance":
            bal += float(mv.amount)
        elif mv.movement_type == "Repayment":
            bal -= float(mv.amount)
        elif mv.movement_type == "Salary":
            bal -= float(mv.advance_recovery or 0.0)
    return round(bal, 2)


def _calculate_account_balance(session, account, *, company_id: int | None = None):
    """Verbatim from app.py ``calculate_account_balance`` with explicit company_id."""
    if company_id is not None:
        q = (
            session.query(JournalEntryLine)
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
            .filter(
                JournalEntryLine.account_id == account.id,
                JournalEntry.company_id == company_id,
            )
        )
    else:
        q = session.query(JournalEntryLine).filter_by(account_id=account.id)
    lines = q.all()
    if account.account_type in ["Asset", "Expense"]:
        return sum((line.debit or 0) - (line.credit or 0) for line in lines)
    return sum((line.credit or 0) - (line.debit or 0) for line in lines)


def entry_date_posting_blocked(
    session,
    entry_date,
    *,
    reference_type: str = "Expense",
    company_id: int | None = None,
) -> str | None:
    """Return posting-block message for entry_date (same guards as create_journal_entry).

    Verbatim from app.py `_entry_date_posting_blocked` (PS-P1); message strings
    are pinned byte-identical by the PS-P0 characterization suite.
    """
    _cje_cid = company_id
    if reference_type != "PeriodClose":
        _fp_q = session.query(FiscalPeriod).filter(
            FiscalPeriod.is_closed == True,  # noqa: E712 — verbatim
            FiscalPeriod.start_date <= entry_date,
            FiscalPeriod.end_date >= entry_date,
        )
        if _cje_cid is not None:
            _fp_q = _fp_q.filter(FiscalPeriod.company_id == _cje_cid)
        locked = _fp_q.first()
        if locked:
            return (
                f"Period '{locked.name}' ({locked.start_date} – {locked.end_date}) is closed. "
                f"Cannot post entries to {entry_date}."
            )

    _yec_q = session.query(YearEndClose).filter(
        YearEndClose.is_void == False,  # noqa: E712 — verbatim
        YearEndClose.start_date <= entry_date,
        YearEndClose.end_date >= entry_date,
    )
    if _cje_cid is not None:
        _yec_q = _yec_q.filter(YearEndClose.company_id == _cje_cid)
    locked_year = _yec_q.first()
    if locked_year:
        return f"Year {locked_year.fiscal_year} is closed. Cannot post entries to {entry_date}."
    return None


def yec_block_message(
    session,
    entry_date,
    *,
    mode: str,
    company_id: int | None,
    period_end_date: datetime.date | None = None,
) -> str | None:
    """Return TD-POSTING-05 inline YEC guard message, or None when not blocked.

    PS-P6-0a: pure query helper — duplicates the five inline guard lookups in
    app.py without changing any call sites yet. No commits or side effects.

    ``mode`` selects the message variant:
    - ``"post"`` — movement post guard (point date in closed year)
    - ``"movement_void"`` — partner/worker void guard (original movement date)
    - ``"allocation_void"`` — profit-allocation void guard (fiscal period span
      contained in closed year); requires ``period_end_date``

    Message strings are byte-identical to the inline guards pinned by
    PS-P6-0a-CHAR.
    """
    if mode == "allocation_void":
        if period_end_date is None:
            return None
        _start = entry_date
        _end = period_end_date
    else:
        _start = entry_date
        _end = entry_date

    _yec_q = session.query(YearEndClose).filter(
        YearEndClose.is_void == False,  # noqa: E712 — verbatim inline guard
        YearEndClose.start_date <= _start,
        YearEndClose.end_date >= _end,
    )
    if company_id is not None:
        _yec_q = _yec_q.filter(YearEndClose.company_id == company_id)
    locked = _yec_q.first()
    if not locked:
        return None

    if mode == "post":
        return (
            f"Year {locked.fiscal_year} is closed. "
            "Cannot post movements dated in that year."
        )
    if mode == "movement_void":
        return (
            f"Year {locked.fiscal_year} is closed. Void the year-end close before "
            "voiding movements inside it."
        )
    if mode == "allocation_void":
        return (
            f"Year {locked.fiscal_year} is closed. Void the year-end close before "
            "voiding allocations inside it."
        )
    return None


def _kernel_persist(session, *, commit_family: str | None) -> None:
    """Commit (internal) or flush (boundary) after a successful kernel write."""
    if commit_family and is_boundary_mode(commit_family):
        session.flush()
    else:
        session.commit()


def create_journal_entry(
    session,
    entry_date,
    description,
    reference_type,
    reference_id,
    lines,
    currency: str = None,
    fx_rate: float = 1.0,
    *,
    company_id: int | None = None,
    commit_family: str | None = None,
):
    """
    Create a journal entry with debit/credit pairs.

    lines: list of tuples (account_id, debit, credit)
    currency: transaction currency code (e.g. "USD"). None means reporting currency.
    fx_rate: units of reporting currency per 1 unit of transaction currency.
             Used to store amount_native on each line for multi-currency reporting.

    Raises ValueError if entry_date falls within a closed fiscal period.

    PS-P1: verbatim from app.py — same commit/rollback behaviour, same ORM
    return type, same error message strings, same float accumulation order.
    """
    _block_msg = entry_date_posting_blocked(
        session, entry_date, reference_type=reference_type, company_id=company_id
    )
    if _block_msg:
        session.rollback()
        raise ValueError(_block_msg)

    _cje_cid = company_id
    entry = JournalEntry(
        entry_date=entry_date,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        company_id=_cje_cid,
    )
    session.add(entry)
    session.flush()

    total_debit = 0
    total_credit = 0

    for account_id, debit, credit in lines:
        net = debit - credit  # positive = debit-side, negative = credit-side
        line = JournalEntryLine(
            journal_entry_id=entry.id,
            account_id=account_id,
            debit=debit,
            credit=credit,
            currency=currency,
            amount_native=round(net * fx_rate, 4) if currency else None,
            company_id=_cje_cid,
        )
        session.add(line)
        total_debit += debit
        total_credit += credit

    if abs(total_debit - total_credit) > 0.01:
        session.rollback()
        raise ValueError(f"Journal entry is not balanced: Debit ${total_debit:.2f} vs Credit ${total_credit:.2f}")

    # NOTE: ChartOfAccounts.balance is NOT updated here.
    # All balance reads must go through calculate_account_balance() which
    # derives the correct value from journal lines — the true source of truth.
    # sync_account_balances() is called at startup to keep the cache current.
    _kernel_persist(session, commit_family=commit_family)
    return entry


def get_account_by_name(session, name, currency=None, *, company_id: int | None = None):
    """Get a GL account by name, optionally filtered by currency (Step 3.1).

    Phase 14C: when company_id is set, results are scoped to that company.
    When None (startup/migration), no company filter is applied.

    Resolution order:
      1. Exact match on name AND currency (e.g. "Cash" + "USD" → finds "Cash USD")
      2. The named account with the given currency stored on the row
      3. Fall back to any account whose name matches (backward-compatible)
    """
    cid = company_id

    def _apply_company(q):
        return q.filter(ChartOfAccounts.company_id == cid) if cid is not None else q

    if currency:
        suffixed = _apply_company(
            session.query(ChartOfAccounts).filter_by(
                account_name=f"{name} {currency}", is_active=True
            )
        ).first()
        if suffixed:
            return suffixed
        exact = _apply_company(
            session.query(ChartOfAccounts).filter_by(
                account_name=name, currency=currency, is_active=True
            )
        ).first()
        if exact:
            return exact
    return _apply_company(
        session.query(ChartOfAccounts).filter_by(account_name=name)
    ).first()


def card_settlement_on(session, company_id: int | None) -> bool:
    """Phase 18-MVP-1: True when card sales route through Card Sales Clearing.

    OFF when company_id is None (startup/migrations) or setting is disabled.
    """
    cid = company_id
    if cid is None:
        return False
    try:
        return bool(get_setting(session, "banking.card_settlement_enabled", company_id=cid))
    except Exception:
        return False


def post_cash_sale(
    session, sale_id, amount, sale_date, currency=None, fx_rate=1.0, *, company_id: int | None = None
):
    """Post cash sale: Debit Cash[currency], Credit Sales Revenue"""
    cash_acct = get_account_by_name(session, "Cash", currency=currency, company_id=company_id)
    sales_acct = get_account_by_name(session, "Sales Revenue", company_id=company_id)
    if cash_acct and sales_acct:
        create_journal_entry(
            session, sale_date,
            f"Cash Sale (ID: {sale_id})",
            "CashSale", sale_id,
            [(cash_acct.id, amount, 0), (sales_acct.id, 0, amount)],
            currency=currency, fx_rate=fx_rate,
            company_id=company_id,
            commit_family=POST_CASH_SALE_FAMILY,
        )


def post_card_sale(
    session, sale_id, amount, sale_date, currency=None, fx_rate=1.0, *, company_id: int | None = None
):
    """Post card sale to the GL.

    Default (settlement OFF): Debit Bank, Credit Sales Revenue.
    Settlement ON: Debit Card Sales Clearing, Credit Sales Revenue.
    """
    if card_settlement_on(session, company_id):
        debit_acct = get_account_by_name(session, "Card Sales Clearing", company_id=company_id)
    else:
        debit_acct = get_account_by_name(session, "Bank", company_id=company_id)
    sales_acct = get_account_by_name(session, "Sales Revenue", company_id=company_id)
    if debit_acct and sales_acct:
        create_journal_entry(
            session, sale_date,
            f"Card Sale (ID: {sale_id})",
            "CardSale", sale_id,
            [(debit_acct.id, amount, 0), (sales_acct.id, 0, amount)],
            currency=currency, fx_rate=fx_rate,
            company_id=company_id,
        )


def post_credit_sale(
    session, sale_id, amount, sale_date, currency=None, fx_rate=1.0, *, company_id: int | None = None
):
    """Post credit sale: Debit Accounts Receivable, Credit Sales Revenue"""
    ar_acct = get_account_by_name(session, "Accounts Receivable", company_id=company_id)
    sales_acct = get_account_by_name(session, "Sales Revenue", company_id=company_id)
    if ar_acct and sales_acct:
        create_journal_entry(
            session, sale_date,
            f"Credit Sale (ID: {sale_id})",
            "CreditSale", sale_id,
            [(ar_acct.id, amount, 0), (sales_acct.id, 0, amount)],
            currency=currency, fx_rate=fx_rate,
            company_id=company_id,
        )


def compute_sale_balance_status(amount, paid_amount, due_date):
    """Compute remaining balance and invoice status from amount/paid/due_date.

    PS-P5-1: verbatim pure helper from app.py.
    """
    balance = round(amount - paid_amount, 2)
    today = datetime.date.today()

    if balance <= 0:
        status = "Paid"
    elif due_date and due_date < today:
        status = "Overdue"
    elif paid_amount > 0:
        status = "Partial"
    else:
        status = "Open"

    return max(balance, 0.0), status


def post_receivable_payment(
    session,
    sale_id,
    payment_amount,
    payment_date,
    payment_method="Cash",
    currency=None,
    payment_fx_rate: float = 1.0,
    *,
    company_id: int | None = None,
):
    """Post a customer payment against a credit sale (Step 7.6 / 7.7).

    PS-P5-1: verbatim from app.py. Returns an error string on failure, otherwise None.
    """
    sale = session.get(Sale, sale_id)
    if not sale or sale.sale_type != "Credit":
        return "Sale not found or is not a credit sale."
    if sale.is_void:
        return "Cannot record payment on a voided sale."
    if sale.balance <= 0:
        return "This invoice is already fully paid."
    if payment_amount <= 0:
        return "Payment amount must be greater than zero."
    if payment_amount > sale.balance:
        return "Payment amount exceeds the remaining balance."

    sale.paid_amount = round(sale.paid_amount + payment_amount, 2)
    sale.balance, sale.status = compute_sale_balance_status(
        sale.amount, sale.paid_amount, sale.due_date
    )
    sale.balance = max(sale.balance, 0.0)

    bank_acct = get_account_by_name(session, "Bank", currency=currency, company_id=company_id)
    cash_acct = get_account_by_name(session, "Cash", currency=currency, company_id=company_id)
    debit_acct = bank_acct if payment_method == "Bank" and bank_acct else cash_acct
    ar_acct = get_account_by_name(session, "Accounts Receivable", company_id=company_id)

    if debit_acct and ar_acct:
        sale_fx = sale.fx_rate or 1.0
        booked_ar = round(payment_amount * sale_fx, 2)
        paid_in_reporting = round(payment_amount * payment_fx_rate, 2)
        fx_diff = round(paid_in_reporting - booked_ar, 2)

        je_lines = [(debit_acct.id, paid_in_reporting, 0), (ar_acct.id, 0, booked_ar)]

        if abs(fx_diff) >= 0.01:
            fx_gain_acct = get_account_by_name(session, "FX Gain", company_id=company_id)
            fx_loss_acct = get_account_by_name(session, "FX Loss", company_id=company_id)
            if fx_diff > 0 and fx_gain_acct:
                je_lines.append((fx_gain_acct.id, 0, fx_diff))
            elif fx_diff < 0 and fx_loss_acct:
                je_lines.append((fx_loss_acct.id, abs(fx_diff), 0))
                je_lines[1] = (ar_acct.id, 0, booked_ar)

        create_journal_entry(
            session,
            payment_date,
            f"Payment for Invoice {sale.invoice_number} (Sale ID: {sale.id})"
            + (f" FX rate {payment_fx_rate}" if payment_fx_rate != 1.0 else ""),
            "ReceivablePayment",
            sale.id,
            je_lines,
            company_id=company_id,
            commit_family=POST_RECEIVABLE_PAYMENT_FAMILY,
        )

    _kernel_persist(session, commit_family=POST_RECEIVABLE_PAYMENT_FAMILY)


def resolve_payment_credit_account(
    session,
    payment_method: str,
    *,
    currency=None,
    company_id: int | None = None,
):
    """Cash/Bank/Company Credit Card → GL account to credit on business payment posting.

    FASTAPI-P0.5b: single explicit ``company_id`` for CC enablement gate and GL lookup.
    """
    pm = (payment_method or "").lower().strip()
    if pm == "bank":
        return get_account_by_name(session, "Bank", currency=currency, company_id=company_id)
    if pm == "credit card":
        if not company_id or not company_card_enabled(session, company_id):
            raise ValueError(_CC_DISABLED_MSG)
        cc_acct = get_account_by_name(session, "Credit Card Payable", company_id=company_id)
        if not cc_acct:
            raise ValueError(_CC_GL_MISSING_MSG)
        return cc_acct
    if pm == "cash":
        return get_account_by_name(session, "Cash", currency=currency, company_id=company_id)
    cash_acct = get_account_by_name(session, "Cash", currency=currency, company_id=company_id)
    bank_acct = get_account_by_name(session, "Bank", currency=currency, company_id=company_id)
    return cash_acct or bank_acct


def post_payable_creation(
    session,
    payable_id,
    amount,
    date,
    expense_category="Rent",
    currency=None,
    *,
    company_id: int | None = None,
):
    """Post payable creation: Debit Expense account, Credit Accounts Payable."""
    ap_acct = get_account_by_name(session, "Accounts Payable", company_id=company_id)
    cat = (expense_category or "").lower()
    if "rent" in cat:
        debit_acct = get_account_by_name(session, "Rent Expense", company_id=company_id)
    elif "salary" in cat:
        debit_acct = get_account_by_name(session, "Salary Expense", company_id=company_id)
    elif any(k in cat for k in ("utility", "electricity", "water", "internet")):
        debit_acct = get_account_by_name(session, "Utility Expense", company_id=company_id)
    elif "advertising" in cat:
        debit_acct = get_account_by_name(session, "Advertising Expense", company_id=company_id)
    elif "fuel" in cat:
        debit_acct = get_account_by_name(session, "Fuel Expense", company_id=company_id)
    else:
        debit_acct = get_account_by_name(session, "Office Expense", company_id=company_id)
    if debit_acct and ap_acct:
        create_journal_entry(
            session, date,
            f"Payable Created (ID: {payable_id}) — {expense_category}",
            "PayableCreation", payable_id,
            [(debit_acct.id, amount, 0), (ap_acct.id, 0, amount)],
            currency=currency,
            company_id=company_id,
        )


def sync_company_cc_subledger(
    session,
    payment_method: str | None,
    *,
    company_id: int | None,
    credit_card_account_id: int | None,
    amount: float,
    txn_date,
    description: str,
    reference_type: str,
    reference_id: int,
    record=None,
) -> None:
    """AD-011: mirror GL CC charge on card BankAccount sub-ledger (no extra JE).

    FASTAPI-P0.5b: requires explicit ``company_id`` (no ambient fallback).
    """
    if (payment_method or "") != _COMPANY_CC_METHOD:
        return
    if company_id is None:
        raise ValueError(_CC_NO_CARDS_MSG)
    try:
        cc_id = resolve_company_credit_card_account_id(
            session, company_id, credit_card_account_id
        )
    except CompanyCardError as exc:
        raise ValueError(str(exc)) from exc
    if record is not None and hasattr(record, "credit_card_account_id"):
        record.credit_card_account_id = cc_id
        session.flush()
    post_cc_subledger_charge(
        session,
        credit_card_account_id=cc_id,
        amount=amount,
        txn_date=txn_date,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        company_id=company_id,
    )


def post_expense(
    session,
    expense_id,
    amount,
    expense_date,
    category,
    payment_method="Cash",
    currency=None,
    credit_card_account_id=None,
    *,
    company_id: int | None = None,
    commit_family: str | None = None,
):
    """Post expense: Debit Expense Account, Credit Cash/Bank/Credit Card Payable."""
    expense = session.get(ExpenseRecord, expense_id)
    credit_acct = resolve_payment_credit_account(
        session, payment_method, currency=currency, company_id=company_id
    )
    if not credit_acct:
        return

    expense_acct = None
    if "rent" in category.lower():
        expense_acct = get_account_by_name(session, "Rent Expense", company_id=company_id)
    elif "salary" in category.lower():
        expense_acct = get_account_by_name(session, "Salary Expense", company_id=company_id)
    elif "utility" in category.lower():
        expense_acct = get_account_by_name(session, "Utility Expense", company_id=company_id)
    elif "advertising" in category.lower():
        expense_acct = get_account_by_name(session, "Advertising Expense", company_id=company_id)
    elif "fuel" in category.lower():
        expense_acct = get_account_by_name(session, "Fuel Expense", company_id=company_id)
    elif "office" in category.lower() or "other" in category.lower():
        expense_acct = get_account_by_name(session, "Office Expense", company_id=company_id)
    else:
        expense_acct = get_account_by_name(session, "Office Expense", company_id=company_id)

    if expense_acct:
        create_journal_entry(
            session, expense_date,
            f"{category} Expense (ID: {expense_id})",
            "Expense", expense_id,
            [(expense_acct.id, amount, 0), (credit_acct.id, 0, amount)],
            currency=currency,
            company_id=company_id,
            commit_family=commit_family or POST_EXPENSE_FAMILY,
        )
        sync_company_cc_subledger(
            session,
            payment_method,
            company_id=company_id,
            credit_card_account_id=credit_card_account_id
            or (expense.credit_card_account_id if expense else None),
            amount=amount,
            txn_date=expense_date,
            description=f"CC expense EXP#{expense_id} — {category}",
            reference_type="Expense",
            reference_id=expense_id,
            record=expense,
        )


def post_payable_payment(
    session,
    payable_id,
    amount,
    date,
    payment_method="Cash",
    currency=None,
    credit_card_account_id=None,
    *,
    company_id: int | None = None,
):
    """Post payable payment: Debit AP, Credit Cash/Bank/Credit Card Payable.

    Subledger ``reference_id`` is ``je.id``, not ``payable_id``.
    """
    ap_acct = get_account_by_name(session, "Accounts Payable", company_id=company_id)
    payable = session.get(Payable, payable_id)
    credit_acct = resolve_payment_credit_account(
        session, payment_method, currency=currency, company_id=company_id
    )
    if ap_acct and credit_acct:
        je = create_journal_entry(
            session, date,
            f"Payable Payment (ID: {payable_id})",
            "PayablePayment", payable_id,
            [(ap_acct.id, amount, 0), (credit_acct.id, 0, amount)],
            currency=currency,
            company_id=company_id,
            commit_family=POST_PAYABLE_PAYMENT_FAMILY,
        )
        sync_company_cc_subledger(
            session,
            payment_method,
            company_id=company_id,
            credit_card_account_id=credit_card_account_id
            or (payable.credit_card_account_id if payable else None),
            amount=amount,
            txn_date=date,
            description=f"CC payable payment PAY#{payable_id}",
            reference_type="PayablePayment",
            reference_id=je.id,
            record=payable,
        )


def resolve_purchase_debit_account(session, gl_debit, *, company_id: int | None = None):
    """Return the GL account to debit for a purchase based on gl_debit label."""
    if not gl_debit or gl_debit.lower() in ("inventory", "equipment", "supplies", "general stock",
                                              "equipment purchase", "general supplies"):
        return get_account_by_name(session, "Inventory", company_id=company_id)
    cat = gl_debit.lower()
    if "rent" in cat:
        return get_account_by_name(session, "Rent Expense", company_id=company_id)
    if "salary" in cat:
        return get_account_by_name(session, "Salary Expense", company_id=company_id)
    if any(k in cat for k in ("electricity", "water", "internet", "utility")):
        return get_account_by_name(session, "Utility Expense", company_id=company_id)
    if "advertising" in cat:
        return get_account_by_name(session, "Advertising Expense", company_id=company_id)
    if "fuel" in cat:
        return get_account_by_name(session, "Fuel Expense", company_id=company_id)
    if any(k in cat for k in ("office", "other", "supplies")):
        return get_account_by_name(session, "Office Expense", company_id=company_id)
    # Unknown category — default to Inventory rather than silently misfiling to Office Expense
    return get_account_by_name(session, "Inventory", company_id=company_id)


def purchase_ref_type(purchase_type: str | None) -> str:
    """Map purchase_type to the GL reference_type used by post_purchase / void / edit."""
    pt = purchase_type or "Credit"
    if pt == "Cash":
        return "CashPurchase"
    if pt == "Bank":
        return "BankPurchase"
    if pt == "Credit Card":
        return "CardPurchase"
    return "Purchase"


def post_purchase(
    session,
    purchase_id,
    amount,
    purchase_date,
    purchase_type="Credit",
    gl_debit=_DEFAULT_PURCHASE_GL_DEBIT,
    currency=None,
    fx_rate=1.0,
    credit_card_account_id=None,
    *,
    company_id: int | None = None,
):
    """Post purchase journal entry."""
    debit_acct = resolve_purchase_debit_account(session, gl_debit, company_id=company_id)
    if not debit_acct:
        return

    ref_type = purchase_ref_type(purchase_type)
    if purchase_type == "Cash":
        credit_acct = get_account_by_name(session, "Cash", currency=currency, company_id=company_id)
    elif purchase_type == "Bank":
        credit_acct = get_account_by_name(session, "Bank", currency=currency, company_id=company_id)
    elif purchase_type == "Credit Card":
        credit_acct = resolve_payment_credit_account(
            session, "Credit Card", currency=currency, company_id=company_id
        )
    else:  # Credit
        credit_acct = get_account_by_name(session, "Accounts Payable", company_id=company_id)

    if credit_acct:
        purchase = session.get(Purchase, purchase_id)
        create_journal_entry(
            session, purchase_date,
            f"{purchase_type} Purchase (ID: {purchase_id})",
            ref_type, purchase_id,
            [(debit_acct.id, amount, 0), (credit_acct.id, 0, amount)],
            currency=currency, fx_rate=fx_rate,
            company_id=company_id,
            commit_family=POST_PURCHASE_FAMILY,
        )
        if purchase_type == _COMPANY_CC_METHOD:
            sync_company_cc_subledger(
                session,
                purchase_type,
                company_id=company_id,
                credit_card_account_id=credit_card_account_id
                or (purchase.credit_card_account_id if purchase else None),
                amount=amount,
                txn_date=purchase_date,
                description=f"CC purchase PUR#{purchase_id}",
                reference_type=ref_type,
                reference_id=purchase_id,
                record=purchase,
            )


def post_bank_transaction(
    session, bank_txn_id, amount, txn_date, txn_type, currency=None, *, company_id: int | None = None
):
    """Post bank transaction.

    PS-P4-1: verbatim from app.py. No BankAccount.balance mutation.
    """
    cash_acct = get_account_by_name(session, "Cash", currency=currency, company_id=company_id)
    bank_acct = get_account_by_name(session, "Bank", currency=currency, company_id=company_id)
    if cash_acct and bank_acct:
        if txn_type == "deposit":
            create_journal_entry(
                session, txn_date,
                f"Bank Deposit (ID: {bank_txn_id})",
                "BankDeposit", bank_txn_id,
                [(bank_acct.id, amount, 0), (cash_acct.id, 0, amount)],
                currency=currency,
                company_id=company_id,
            )
        elif txn_type == "withdrawal":
            create_journal_entry(
                session, txn_date,
                f"Bank Withdrawal (ID: {bank_txn_id})",
                "BankWithdrawal", bank_txn_id,
                [(cash_acct.id, amount, 0), (bank_acct.id, 0, amount)],
                currency=currency,
                company_id=company_id,
            )


def post_bank_transfer(
    session, txn_id, amount, txn_date, src_name, dest_name, *, company_id: int | None = None
):
    """Post GL for a bank transfer only when source and destination use different GL accounts.

    With a single 'Bank' GL account, same-GL transfers are internal and have no GL impact.

    PS-P4-1: verbatim from app.py. No BankAccount.balance mutation.
    """
    def gl_for(name):
        if "cash" in name.lower():
            return get_account_by_name(session, "Cash", company_id=company_id)
        return get_account_by_name(session, "Bank", company_id=company_id)

    src_gl = gl_for(src_name)
    dest_gl = gl_for(dest_name)
    if not src_gl or not dest_gl or src_gl.id == dest_gl.id:
        return  # Same GL account — internal sub-account movement; no journal needed
    create_journal_entry(
        session, txn_date,
        f"Bank Transfer (TXN {txn_id}): {src_name} → {dest_name}",
        "BankTransfer", txn_id,
        [(dest_gl.id, amount, 0), (src_gl.id, 0, amount)],
        company_id=company_id,
    )


def post_salary(
    session, salary_id, amount, salary_date, currency=None, *, company_id: int | None = None
):
    """Post salary: Debit Salary Expense, Credit Cash[currency].

    PS-P5-3: verbatim from app.py. GL-only.
    """
    salary_exp = get_account_by_name(session, "Salary Expense", company_id=company_id)
    cash_acct = get_account_by_name(session, "Cash", currency=currency, company_id=company_id)
    if salary_exp and cash_acct:
        create_journal_entry(
            session, salary_date,
            f"Salary Payment (ID: {salary_id})",
            "Salary", salary_id,
            [(salary_exp.id, amount, 0), (cash_acct.id, 0, amount)],
            currency=currency,
            company_id=company_id,
        )


def post_capital_contribution(
    session, btxn_id, amount, date, gl_name, currency=None, notes="", *, company_id: int | None = None
):
    """Dr Bank/Cash  Cr Owner Capital.  gl_name is 'Bank' or 'Cash'.

    PS-P5-3: verbatim from app.py. No BankAccount.balance mutation.
    """
    gl_acct = get_account_by_name(session, gl_name, currency=currency, company_id=company_id)
    cap_acct = get_account_by_name(session, "Owner Capital", company_id=company_id)
    if gl_acct and cap_acct:
        create_journal_entry(
            session, date,
            f"Capital Contribution #{btxn_id}" + (f" — {notes}" if notes else ""),
            "CapitalContribution", btxn_id,
            [(gl_acct.id, amount, 0), (cap_acct.id, 0, amount)],
            currency=currency,
            company_id=company_id,
            commit_family=POST_EQUITY_MOVEMENT_FAMILY,
        )


def post_owner_drawing(
    session, btxn_id, amount, date, gl_name, currency=None, notes="", *, company_id: int | None = None
):
    """Dr Owner Drawings  Cr Bank/Cash.  gl_name is 'Bank' or 'Cash'.

    PS-P5-3: verbatim from app.py. No BankAccount.balance mutation.
    """
    draw_acct = get_account_by_name(session, "Owner Drawings", company_id=company_id)
    gl_acct = get_account_by_name(session, gl_name, currency=currency, company_id=company_id)
    if draw_acct and gl_acct:
        create_journal_entry(
            session, date,
            f"Owner Drawing #{btxn_id}" + (f" — {notes}" if notes else ""),
            "OwnerDrawing", btxn_id,
            [(draw_acct.id, amount, 0), (gl_acct.id, 0, amount)],
            currency=currency,
            company_id=company_id,
            commit_family=POST_EQUITY_MOVEMENT_FAMILY,
        )


def create_reversing_journal_entry(
    session,
    original_entry,
    void_reason,
    *,
    company_id: int | None = None,
    commit_family: str | None = None,
):
    """Swap every debit/credit in original_entry and post as a new entry.

    PS-P3-1: verbatim from app.py. Shim supplies ``company_id`` for
    ``create_journal_entry`` (legacy ambient GL scope).
    """
    reversed_lines = [
        (line.account_id, line.credit or 0, line.debit or 0)
        for line in original_entry.lines
    ]
    if not reversed_lines:
        return None
    return create_journal_entry(
        session,
        datetime.date.today(),
        f"VOID: {original_entry.description} — {void_reason}",
        "Reversal",
        original_entry.id,
        reversed_lines,
        company_id=company_id,
        commit_family=commit_family,
    )


def reverse_journal_entries_for(
    session,
    reference_type,
    reference_id,
    void_reason,
    *,
    company_id: int | None = None,
    commit_family: str | None = None,
):
    """Find all journal entries for a reference and create reversals.

    PS-P3-1: verbatim from app.py company-scoped JournalEntry query. The shim
    supplies ``company_id`` for legacy ambient company scope.
    """
    q = session.query(JournalEntry).filter_by(
        reference_type=reference_type, reference_id=reference_id
    )
    if company_id is not None:
        q = q.filter(JournalEntry.company_id == company_id)
    entries = q.all()
    for entry in entries:
        create_reversing_journal_entry(
            session, entry, void_reason, company_id=company_id, commit_family=commit_family
        )


def void_expense(
    session,
    expense_id,
    void_reason,
    *,
    company_id: int | None = None,
):
    """Reverse CC subledger + Expense GL and flag the expense void.

    PS-P3-2a: verbatim reverse-and-flag core from app.py. Commits entity flags.
    App shim writes the audit row only on ``True``.
    """
    expense = session.get(ExpenseRecord, expense_id)
    if not expense or expense.is_void:
        return False
    reverse_cc_subledgers_for_gl_reference(
        session, "Expense", expense_id, void_reason
    )
    reverse_journal_entries_for(
        session,
        "Expense",
        expense_id,
        void_reason,
        company_id=company_id,
        commit_family=VOID_CASCADE_FAMILY,
    )
    expense.is_void = True
    expense.voided_at = datetime.date.today()
    expense.void_reason = void_reason
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)
    return True


def void_payable(
    session,
    payable_id,
    void_reason,
    *,
    company_id: int | None = None,
):
    """Reverse CC subledger + PayableCreation/PayablePayment GL and flag void.

    PS-P3-2a: verbatim reverse-and-flag core from app.py. Commits entity flags.
    App shim writes the audit row only on ``True``.
    """
    payable = session.get(Payable, payable_id)
    if not payable or payable.is_void:
        return False
    reverse_cc_subledgers_for_gl_reference(
        session, "PayablePayment", payable_id, void_reason
    )
    reverse_journal_entries_for(
        session,
        "PayableCreation",
        payable_id,
        void_reason,
        company_id=company_id,
        commit_family=VOID_CASCADE_FAMILY,
    )
    reverse_journal_entries_for(
        session,
        "PayablePayment",
        payable_id,
        void_reason,
        company_id=company_id,
        commit_family=VOID_CASCADE_FAMILY,
    )
    payable.is_void = True
    payable.voided_at = datetime.date.today()
    payable.void_reason = void_reason
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)
    return True


def linked_purchase_payable(
    session,
    purchase_id: int,
    *,
    company_id: int,
):
    """Return the Payable linked to a purchase, scoped to company.

    PS-P3-3a: verbatim from app.py company-scoped Payable lookup by purchase_id.
    Shim supplies ``company_id`` (legacy company-required scope).
    """
    return (
        session.query(Payable)
        .filter(Payable.company_id == company_id, Payable.purchase_id == purchase_id)
        .first()
    )


def void_purchase_linked_payable(
    session,
    purchase_id: int,
    reason: str,
    *,
    company_id: int | None = None,
    commit_family: str | None = None,
) -> None:
    """Void payable linked to a purchase; reverse PayablePayment GL if paid.

    PS-P3-3a: commit-free helper from app.py. No audit.
    """
    linked = linked_purchase_payable(session, purchase_id, company_id=company_id)
    if not linked or linked.is_void:
        return
    if linked.paid:
        reverse_cc_subledgers_for_gl_reference(
            session, "PayablePayment", linked.id, reason
        )
        reverse_journal_entries_for(
            session,
            "PayablePayment",
            linked.id,
            reason,
            company_id=company_id,
            commit_family=commit_family,
        )
    linked.is_void = True
    linked.voided_at = datetime.date.today()
    linked.void_reason = reason


def void_purchase(
    session,
    purchase_id,
    void_reason,
    *,
    company_id: int | None = None,
):
    """Reverse purchase GL + cascade linked payable void; commit purchase flags.

    PS-P3-3b: verbatim reverse-and-flag core from app.py. Commits purchase and
    linked-payable flags. App shim writes the audit row only on ``True``.
    """
    purchase = session.get(Purchase, purchase_id)
    if not purchase or purchase.is_void:
        return False
    ref_type = purchase_ref_type(purchase.purchase_type)
    reverse_cc_subledgers_for_gl_reference(
        session, ref_type, purchase_id, void_reason
    )
    reverse_journal_entries_for(
        session, ref_type, purchase_id, void_reason, company_id=company_id,
        commit_family=VOID_CASCADE_FAMILY,
    )
    purchase.is_void = True
    purchase.voided_at = datetime.date.today()
    purchase.void_reason = void_reason
    void_purchase_linked_payable(
        session,
        purchase_id,
        f"Purchase #{purchase_id} voided: {void_reason}",
        company_id=company_id,
        commit_family=VOID_CASCADE_FAMILY,
    )
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)
    return True


def void_sale(
    session,
    sale_id,
    void_reason,
    *,
    company_id: int | None = None,
):
    """Reverse sale GL refs and flag the sale void.

    PS-P3-2b: verbatim reverse-and-flag core from app.py. Commits sale flags.
    App shim writes the audit row only on ``True``.
    """
    sale = session.get(Sale, sale_id)
    if not sale or sale.is_void:
        return False
    for ref_type in ("CashSale", "CardSale", "CreditSale", "ReceivablePayment"):
        reverse_journal_entries_for(
            session,
            ref_type,
            sale_id,
            void_reason,
            company_id=company_id,
            commit_family=VOID_CASCADE_FAMILY,
        )
    sale.is_void = True
    sale.voided_at = datetime.date.today()
    sale.void_reason = void_reason
    sale.status = "Void"
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)
    return True


def void_bank_transaction(
    session,
    txn_id,
    void_reason,
    *,
    company_id: int | None = None,
):
    """Reverse bank GL refs, restore bank balances, and flag the transaction void.

    PS-P4-2: verbatim reverse-and-flag core from app.py. Commits entity flags.
    App shim writes the audit row only on ``True``.
    """
    txn = session.get(BankTransaction, txn_id)
    if not txn or txn.is_void:
        return False
    if (txn.statement_ref or "").startswith("bsr:"):
        raise ValueError(
            "Statement-linked transactions must be unposted from Bank Reconciliation."
        )
    # Card-sale deposits are created by the Sale workflow and must be reversed
    # by voiding the originating Sale — not through Banking.
    if (txn.description or "").startswith("Card Sale "):
        return False
    # Equity movements must be reversed through Accounting → Equity Movements.
    _desc = txn.description or ""
    if _desc.startswith("Capital Contribution #") or _desc.startswith("Owner Drawing #"):
        return False
    for ref_type in ("BankDeposit", "BankWithdrawal", "BankTransfer"):
        reverse_journal_entries_for(
            session,
            ref_type,
            txn_id,
            void_reason,
            company_id=company_id,
            commit_family=VOID_CASCADE_FAMILY,
        )
    acct = session.get(BankAccount, txn.account_id)
    if acct:
        if txn.type in ("deposit", "withdrawal"):
            reverse_account_balance_delta(acct, txn.type, txn.amount)
        elif txn.type == "transfer":
            if txn.description and txn.description.startswith("Transfer from"):
                # This is the destination record: balance was increased, now reduce
                acct.balance = (acct.balance or 0) - txn.amount
            else:
                # This is the source record: balance was reduced, now restore.
                # Also void the paired destination record so its balance is reversed too.
                acct.balance = (acct.balance or 0) + txn.amount
                paired_q = session.query(BankTransaction).filter(
                    BankTransaction.date == txn.date,
                    BankTransaction.amount == txn.amount,
                    BankTransaction.type == "transfer",
                    BankTransaction.id != txn.id,
                    BankTransaction.is_void == False,
                    BankTransaction.description.like(f"Transfer from {acct.name}%"),
                )
                if company_id is not None:
                    paired_q = paired_q.filter(BankTransaction.company_id == company_id)
                paired = paired_q.first()
                if paired:
                    dest_acct = session.get(BankAccount, paired.account_id)
                    if dest_acct:
                        dest_acct.balance = (dest_acct.balance or 0) - paired.amount
                    paired.is_void = True
                    paired.voided_at = datetime.date.today()
                    paired.void_reason = f"Paired with voided transfer TXN#{txn_id}: {void_reason}"
    txn.is_void = True
    txn.voided_at = datetime.date.today()
    txn.void_reason = void_reason
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)
    return True


def void_inventory_transaction(session, txn_id, void_reason):
    """Reverse product quantity and flag an inventory adjustment void.

    PS-P5-2: verbatim reverse-and-flag core from app.py. No GL reversal.
    App shim writes the audit row only on ``True``.
    """
    txn = session.get(InventoryTransaction, txn_id)
    if not txn or txn.is_void:
        return False
    product = session.get(Product, txn.product_id)
    if product:
        product.quantity = (product.quantity or 0) - txn.change
    txn.is_void = True
    txn.voided_at = datetime.date.today()
    txn.void_reason = void_reason
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)
    return True


def void_equity_movement(
    session,
    ref_type,
    btxn_id,
    void_reason,
    *,
    company_id: int | None = None,
):
    """Reverse an equity movement GL entry and void the linked BankTransaction.

    PS-P5-3: verbatim from app.py. App shim writes the audit row after success.
    """
    reverse_journal_entries_for(
        session,
        ref_type,
        btxn_id,
        void_reason,
        company_id=company_id,
        commit_family=VOID_CASCADE_FAMILY,
    )
    btxn = session.get(BankTransaction, btxn_id)
    if btxn and not btxn.is_void:
        acct = session.get(BankAccount, btxn.account_id)
        if acct:
            if btxn.type == "deposit":
                acct.balance = (acct.balance or 0) - btxn.amount
            elif btxn.type == "withdrawal":
                acct.balance = (acct.balance or 0) + btxn.amount
        btxn.is_void = True
        btxn.voided_at = datetime.date.today()
        btxn.void_reason = void_reason
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)


def void_reconciliation(
    session,
    reconciliation_id: int,
    owner_id: int,
    reason: str,
    *,
    company_id: int | None = None,
) -> str:
    """Owner voids a reconciliation and reverses its variance JE.

    PS-P5-4: verbatim from app.py. App shim writes the audit row on success (``""``).
    """
    reconciliation = session.get(DailyCashReconciliation, reconciliation_id)
    if not reconciliation:
        return "Reconciliation not found."
    if reconciliation.is_void:
        return "Reconciliation already voided."
    if reconciliation.status == "draft":
        return "Cannot void a draft reconciliation; delete it instead."

    if reconciliation.journal_entry_id:
        original_je = session.get(JournalEntry, reconciliation.journal_entry_id)
        if original_je:
            reverse_journal_entries_for(
                session,
                "CashReconciliation",
                reconciliation_id,
                reason,
                company_id=company_id,
                commit_family=VOID_CASCADE_FAMILY,
            )
            reversal_q = session.query(JournalEntry).filter(
                JournalEntry.reference_type == "Reversal",
                JournalEntry.reference_id == original_je.id,
            )
            if company_id is not None:
                reversal_q = reversal_q.filter(JournalEntry.company_id == company_id)
            reversal = reversal_q.order_by(JournalEntry.id.desc()).first()
            if reversal:
                reconciliation.reversed_je_id = reversal.id
    reconciliation.is_void = True
    reconciliation.voided_by_id = owner_id
    reconciliation.voided_at = datetime.datetime.now()
    reconciliation.void_reason = reason
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)
    return ""


def void_eod_close(session, close_id: int, owner_id: int, reason: str) -> str:
    """Owner voids an end-of-day close record.

    PS-P5-4: verbatim from app.py. No GL reversal. App shim writes audit on success.
    """
    eod = session.get(EndOfDayClose, close_id)
    if not eod:
        return "End-of-day close record not found."
    if eod.is_void:
        return "This close has already been voided."

    eod.is_void = True
    eod.voided_by_id = owner_id
    eod.voided_at = datetime.datetime.now()
    eod.void_reason = reason
    eod.status = "voided"
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)
    return ""


def void_year_end_close(session, yec_id: int, voider_id: int, reason: str) -> str:
    """Void a year-end close, removing the year lock.

    PS-P5-4: verbatim from app.py. App shim writes audit on success.
    """
    yec = session.get(YearEndClose, yec_id)
    if not yec:
        return "Year-end close record not found."
    if yec.is_void:
        return "Year-end close is already voided."
    if not reason.strip():
        return "Void reason is required."

    yec.is_void = True
    yec.status = "voided"
    yec.voided_by_id = voider_id
    yec.voided_at = datetime.datetime.now()
    yec.void_reason = reason
    session.commit()
    return ""


def post_partner_movement(
    session,
    partner_id: int,
    movement_type: str,
    amount: float,
    date: datetime.date,
    bank_account_id: int = None,
    notes: str = None,
    created_by_id: int = None,
    *,
    company_id: int | None = None,
):
    """Post a partner movement and its GL journal entry.

    PS-P6-1: verbatim from app.py. App shim writes the audit row on ``""`` success.
    Returns (movement_id, error_string). Error is "" on success.
    AdvanceOffset requires no bank_account_id; all other types require one.
    """
    if amount <= 0:
        return None, "Amount must be greater than zero."
    if movement_type not in _PARTNER_REF_TYPES:
        return None, f"Unknown movement type: {movement_type}"

    _yec4_msg = yec_block_message(session, date, mode="post", company_id=company_id)
    if _yec4_msg:
        return None, _yec4_msg

    partner = session.get(Partner, partner_id)
    if not partner or not partner.is_active:
        return None, "Partner not found or inactive."

    cap_acct = session.get(ChartOfAccounts, partner.capital_account_id)
    cur_acct = session.get(ChartOfAccounts, partner.current_account_id)
    adv_acct = session.get(ChartOfAccounts, partner.advance_account_id)
    if not all([cap_acct, cur_acct, adv_acct]):
        return None, "Partner CoA accounts missing — re-create the partner."

    if movement_type == "AdvanceOffset":
        adv_bal = _calculate_account_balance(session, adv_acct, company_id=company_id)
        if amount > adv_bal + 0.01:
            return None, (
                f"Offset amount {amount:,.2f} exceeds outstanding advance "
                f"balance {adv_bal:,.2f}."
            )

    needs_bank = movement_type != "AdvanceOffset"
    ba_obj, gl_acct, btxn = None, None, None
    if needs_bank:
        if not bank_account_id:
            return None, "Bank account is required for this movement type."
        ba_obj = session.get(BankAccount, bank_account_id)
        if not ba_obj:
            return None, "Bank account not found."
        gl_name = "Cash" if "cash" in (ba_obj.name or "").lower() else "Bank"
        gl_acct = get_account_by_name(
            session, gl_name, currency=ba_obj.currency, company_id=company_id
        )
        if not gl_acct:
            return None, f"GL account '{gl_name}' not found for currency '{ba_obj.currency}'."

        txn_type = (
            "deposit" if movement_type in ("CapitalContribution", "Repayment") else "withdrawal"
        )
        btxn = BankTransaction(
            account_id=ba_obj.id,
            date=date,
            amount=amount,
            type=txn_type,
            description=f"Partner {movement_type} #TBD",
        )
        session.add(btxn)
        session.flush()
        btxn.description = f"Partner {movement_type} #{btxn.id}"
        ba_obj.balance = (ba_obj.balance or 0.0) + (
            amount if txn_type == "deposit" else -amount
        )

    movement = PartnerMovement(
        partner_id=partner_id,
        movement_type=movement_type,
        amount=amount,
        date=date,
        bank_transaction_id=btxn.id if btxn else None,
        notes=notes.strip() if notes else None,
        is_void=False,
        created_by_id=created_by_id,
        created_at=datetime.datetime.now(),
    )
    session.add(movement)
    session.flush()

    if movement_type == "CapitalContribution":
        lines = [(gl_acct.id, amount, 0), (cap_acct.id, 0, amount)]
    elif movement_type in ("Drawing", "Salary"):
        lines = [(cur_acct.id, amount, 0), (gl_acct.id, 0, amount)]
    elif movement_type == "Advance":
        lines = [(adv_acct.id, amount, 0), (gl_acct.id, 0, amount)]
    elif movement_type == "Repayment":
        lines = [(gl_acct.id, amount, 0), (adv_acct.id, 0, amount)]
    else:
        lines = [(cur_acct.id, amount, 0), (adv_acct.id, 0, amount)]

    desc = f"Partner {movement_type}: {partner.name}"
    if notes and notes.strip():
        desc += f" — {notes.strip()}"

    je = create_journal_entry(
        session,
        date,
        desc,
        _PARTNER_REF_TYPES[movement_type],
        movement.id,
        lines,
        company_id=company_id,
        commit_family=POST_PARTNER_MOVEMENT_FAMILY,
    )
    movement.journal_entry_id = je.id
    _kernel_persist(session, commit_family=POST_PARTNER_MOVEMENT_FAMILY)
    return movement.id, ""


def void_partner_movement(
    session,
    movement_id: int,
    voider_id: int,
    reason: str,
    *,
    company_id: int | None = None,
) -> str:
    """Void a partner movement and reverse its JE.

    PS-P6-1: verbatim from app.py. App shim writes the audit row on ``""`` success.
    """
    movement = session.get(PartnerMovement, movement_id)
    if not movement or movement.is_void:
        return "Movement not found or already voided."
    if not reason.strip():
        return "Void reason is required."

    _yec5_msg = yec_block_message(
        session, movement.date, mode="movement_void", company_id=company_id
    )
    if _yec5_msg:
        return _yec5_msg

    if movement.journal_entry_id:
        je = session.get(JournalEntry, movement.journal_entry_id)
        if je:
            create_reversing_journal_entry(
                session, je, reason, company_id=company_id, commit_family=VOID_CASCADE_FAMILY
            )

    if movement.bank_transaction_id:
        btxn = session.get(BankTransaction, movement.bank_transaction_id)
        if btxn and not btxn.is_void:
            btxn.is_void = True
            btxn.void_reason = reason
            btxn.voided_at = datetime.datetime.now()
            ba = session.get(BankAccount, btxn.account_id)
            if ba:
                ba.balance = (ba.balance or 0.0) + (
                    btxn.amount if btxn.type == "withdrawal" else -btxn.amount
                )

    movement.is_void = True
    movement.voided_by_id = voider_id
    movement.voided_at = datetime.datetime.now()
    movement.void_reason = reason
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)
    return ""


def post_worker_movement(
    session,
    worker_id: int,
    movement_type: str,
    date: datetime.date,
    *,
    bank_account_id: int,
    amount: float = None,
    gross_salary: float = None,
    deductions: float = None,
    advance_recovery: float = None,
    pay_period: str = None,
    notes: str = None,
    created_by_id: int = None,
    company_id: int | None = None,
):
    """Post a worker salary, advance, or repayment.

    PS-P6-2: verbatim from app.py. App shim writes the audit row on ``""`` success.
    Returns (movement_id, error).
    """
    if movement_type not in _WORKER_REF_TYPES:
        return None, f"Unknown movement type: {movement_type}"

    worker = session.get(Worker, worker_id)
    if not worker or not worker.is_active:
        return None, "Worker not found or inactive."

    _yec_msg = yec_block_message(session, date, mode="post", company_id=company_id)
    if _yec_msg:
        return None, _yec_msg

    salary_exp = get_account_by_name(session, "Salary Expense", company_id=company_id)
    adv_acct = get_account_by_name(session, "Employee Advances", company_id=company_id)
    if movement_type == "Salary" and not salary_exp:
        return None, "Salary Expense account missing."
    if movement_type in ("Advance", "Repayment", "Salary") and not adv_acct:
        return None, "Employee Advances account missing — restart the app to apply migration."

    gross_salary = round(float(gross_salary or 0.0), 2)
    deductions = round(float(deductions or 0.0), 2)
    advance_recovery = round(float(advance_recovery or 0.0), 2)
    net_salary = 0.0
    net_paid = 0.0
    mv_amount = 0.0

    if movement_type == "Salary":
        if gross_salary <= 0:
            return None, "Gross salary must be greater than zero."
        if deductions < 0 or advance_recovery < 0:
            return None, "Deductions and advance recovery cannot be negative."
        net_salary = round(gross_salary - deductions, 2)
        if net_salary <= 0:
            return None, "Net salary after deductions must be greater than zero."
        net_paid = round(net_salary - advance_recovery, 2)
        if net_paid < -0.01:
            return None, "Advance recovery exceeds net salary."
        if advance_recovery > 0:
            adv_bal = _get_worker_advance_balance(session, worker_id, company_id=company_id)
            if advance_recovery > adv_bal + 0.01:
                return None, (
                    f"Advance recovery {advance_recovery:,.2f} exceeds outstanding "
                    f"advance {adv_bal:,.2f}."
                )
        mv_amount = net_salary
        txn_type = "withdrawal"
    else:
        mv_amount = round(float(amount or 0.0), 2)
        if mv_amount <= 0:
            return None, "Amount must be greater than zero."
        if movement_type == "Advance":
            txn_type = "withdrawal"
        else:
            adv_bal = _get_worker_advance_balance(session, worker_id, company_id=company_id)
            if mv_amount > adv_bal + 0.01:
                return None, (
                    f"Repayment {mv_amount:,.2f} exceeds outstanding advance {adv_bal:,.2f}."
                )
            txn_type = "deposit"

    cash_out = mv_amount if movement_type != "Salary" else net_paid
    ba_obj = gl_acct = None
    if cash_out > 0.01:
        if not bank_account_id:
            return None, "Bank account is required."
        ba_obj = session.get(BankAccount, bank_account_id)
        if not ba_obj:
            return None, "Bank account not found."
        gl_name = "Cash" if "cash" in (ba_obj.name or "").lower() else "Bank"
        gl_acct = get_account_by_name(
            session, gl_name, currency=ba_obj.currency, company_id=company_id
        )
        if not gl_acct:
            return None, f"GL account '{gl_name}' not found for currency '{ba_obj.currency}'."

    if movement_type == "Salary":
        lines = [(salary_exp.id, net_salary, 0)]
        if advance_recovery > 0.01:
            lines.append((adv_acct.id, 0, advance_recovery))
        if net_paid > 0.01:
            lines.append((gl_acct.id, 0, net_paid))
    elif movement_type == "Advance":
        lines = [(adv_acct.id, mv_amount, 0), (gl_acct.id, 0, mv_amount)]
    else:
        lines = [(gl_acct.id, mv_amount, 0), (adv_acct.id, 0, mv_amount)]

    btxn = None
    if cash_out > 0.01:
        btxn = BankTransaction(
            account_id=ba_obj.id,
            date=date,
            amount=cash_out,
            type=txn_type,
            description=f"Worker {movement_type} #TBD",
        )
        session.add(btxn)
        session.flush()
        btxn.description = f"Worker {movement_type} #{btxn.id}"
        ba_obj.balance = (ba_obj.balance or 0.0) + (
            btxn.amount if txn_type == "deposit" else -btxn.amount
        )
    elif movement_type == "Salary":
        pass
    else:
        return None, "Amount must be greater than zero."

    movement = WorkerMovement(
        worker_id=worker_id,
        movement_type=movement_type,
        amount=mv_amount,
        date=date,
        pay_period=pay_period.strip() if pay_period else None,
        gross_salary=gross_salary,
        deductions=deductions,
        advance_recovery=advance_recovery,
        net_paid=net_paid,
        bank_transaction_id=btxn.id if btxn else None,
        notes=notes.strip() if notes else None,
        is_void=False,
        created_by_id=created_by_id,
        created_at=datetime.datetime.now(),
        company_id=company_id,
    )
    session.add(movement)
    session.flush()

    desc = f"Worker {movement_type}: {worker.name}"
    if notes and notes.strip():
        desc += f" — {notes.strip()}"
    je = create_journal_entry(
        session,
        date,
        desc,
        _WORKER_REF_TYPES[movement_type],
        movement.id,
        lines,
        company_id=company_id,
        commit_family=POST_WORKER_MOVEMENT_FAMILY,
    )
    movement.journal_entry_id = je.id
    _kernel_persist(session, commit_family=POST_WORKER_MOVEMENT_FAMILY)
    return movement.id, ""


def void_worker_movement(
    session,
    movement_id: int,
    voider_id: int,
    reason: str,
    *,
    company_id: int | None = None,
) -> str:
    """Void a worker movement and reverse its JE.

    PS-P6-2: verbatim from app.py. App shim writes the audit row on ``""`` success.
    """
    movement = session.get(WorkerMovement, movement_id)
    if not movement or movement.is_void:
        return "Movement not found or already voided."
    if not reason.strip():
        return "Void reason is required."

    _yec_msg = yec_block_message(
        session, movement.date, mode="movement_void", company_id=company_id
    )
    if _yec_msg:
        return _yec_msg

    if movement.journal_entry_id:
        je = session.get(JournalEntry, movement.journal_entry_id)
        if je:
            create_reversing_journal_entry(
                session, je, reason, company_id=company_id, commit_family=VOID_CASCADE_FAMILY
            )

    if movement.bank_transaction_id:
        btxn = session.get(BankTransaction, movement.bank_transaction_id)
        if btxn and not btxn.is_void:
            btxn.is_void = True
            btxn.void_reason = reason
            btxn.voided_at = datetime.datetime.now()
            ba = session.get(BankAccount, btxn.account_id)
            if ba:
                ba.balance = (ba.balance or 0.0) + (
                    btxn.amount if btxn.type == "withdrawal" else -btxn.amount
                )

    movement.is_void = True
    movement.voided_by_id = voider_id
    movement.voided_at = datetime.datetime.now()
    movement.void_reason = reason
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)
    return ""


def _validate_partner_shares(session, *, company_id: int | None = None):
    """Check active partners sum to 100 ± 0.01%.

    Returns (is_valid, total_pct, error_string).
    """
    q = session.query(Partner).filter_by(is_active=True)
    if company_id is not None:
        q = q.filter(Partner.company_id == company_id)
    active = q.all()
    if not active:
        return False, 0.0, "No active partners defined."
    total = sum(p.profit_share_pct for p in active)
    if not (99.99 <= total <= 100.01):
        return False, total, f"Partner shares sum to {total:.2f}% — must equal 100%."
    return True, total, ""


def _get_period_net_income_from_je(session, period, *, company_id: int | None = None) -> float:
    """Read the exact net income posted to RE by the period's closing JE.

    Returns credit − debit on the RE line: positive = profit, negative = loss.
    Returns 0.0 if the period has no closing JE or no RE line.
    """
    if not period.closing_je_id:
        return 0.0
    closing_je = session.get(JournalEntry, period.closing_je_id)
    if not closing_je:
        return 0.0
    re_acct = get_account_by_name(session, "Retained Earnings", company_id=company_id)
    if not re_acct:
        return 0.0
    for line in closing_je.lines:
        if line.account_id == re_acct.id:
            return (line.credit or 0.0) - (line.debit or 0.0)
    return 0.0


def allocate_profit_to_partners(
    session,
    period_id: int,
    allocated_by_id: int,
    notes: str = None,
    *,
    company_id: int | None = None,
):
    """Allocate a period's net income to partner current accounts (Option B).

    PS-P6-3: verbatim from app.py. App shim writes the audit row on ``""`` success.
    Derives amount from the period's closing JE — never from the live RE balance.
    Returns (allocation_id, error_string). Error is "" on success.
    """
    period = session.get(FiscalPeriod, period_id)
    if not period:
        return None, "Fiscal period not found."
    if not period.is_closed:
        return None, "Period must be closed before allocating profit."
    if not period.closing_je_id:
        return None, "Period has no closing JE. Close the period first."

    _alloc_q = session.query(PartnerProfitAllocation).filter_by(
        fiscal_period_id=period_id, is_void=False
    )
    if company_id is not None:
        _alloc_q = _alloc_q.filter(PartnerProfitAllocation.company_id == company_id)
    existing = _alloc_q.first()
    if existing:
        return None, f"Period '{period.name}' already has an active allocation (#{existing.id})."

    valid, total_pct, err = _validate_partner_shares(session, company_id=company_id)
    if not valid:
        return None, err

    net_income = _get_period_net_income_from_je(session, period, company_id=company_id)
    if abs(net_income) < 0.005:
        return None, f"Net income for '{period.name}' is zero — nothing to allocate."

    re_acct = get_account_by_name(session, "Retained Earnings", company_id=company_id)
    if not re_acct:
        return None, "Retained Earnings account not found."

    _partner_q = session.query(Partner).filter_by(is_active=True).order_by(Partner.id)
    if company_id is not None:
        _partner_q = _partner_q.filter(Partner.company_id == company_id)
    active_partners = _partner_q.all()

    abs_income = abs(net_income)
    shares, running = [], 0.0
    for i, p in enumerate(active_partners):
        if i == len(active_partners) - 1:
            share = round(abs_income - running, 2)
        else:
            share = round(abs_income * p.profit_share_pct / 100.0, 2)
            running += share
        shares.append(share)

    if net_income > 0:
        lines = [(re_acct.id, abs_income, 0)]
        for p, s in zip(active_partners, shares):
            lines.append((p.current_account_id, 0, s))
    else:
        lines = [(re_acct.id, 0, abs_income)]
        for p, s in zip(active_partners, shares):
            lines.append((p.current_account_id, s, 0))

    allocation = PartnerProfitAllocation(
        fiscal_period_id=period_id,
        allocated_at=datetime.datetime.now(),
        allocated_by_id=allocated_by_id,
        total_net_income=net_income,
        notes=notes.strip() if notes else None,
        is_void=False,
        created_at=datetime.datetime.now(),
    )
    session.add(allocation)
    session.flush()

    je = create_journal_entry(
        session,
        datetime.date.today(),
        f"Profit Allocation: {period.name}",
        "ProfitAllocation",
        allocation.id,
        lines,
        company_id=company_id,
        commit_family=PROFIT_ALLOCATION_FAMILY,
    )
    allocation.journal_entry_id = je.id

    for p, s in zip(active_partners, shares):
        session.add(
            PartnerProfitAllocationLine(
                allocation_id=allocation.id,
                partner_id=p.id,
                share_pct=p.profit_share_pct,
                amount=s if net_income > 0 else -s,
            )
        )
    _kernel_persist(session, commit_family=PROFIT_ALLOCATION_FAMILY)
    return allocation.id, ""


def void_profit_allocation(
    session,
    allocation_id: int,
    voider_id: int,
    reason: str,
    *,
    company_id: int | None = None,
) -> str:
    """Void a profit allocation and reverse its JE.

    PS-P6-3: verbatim from app.py. App shim writes the audit row on ``""`` success.
    """
    allocation = session.get(PartnerProfitAllocation, allocation_id)
    if not allocation or allocation.is_void:
        return "Allocation not found or already voided."
    if not reason.strip():
        return "Void reason is required."

    period = session.get(FiscalPeriod, allocation.fiscal_period_id)
    if period:
        _yec_msg = yec_block_message(
            session,
            period.start_date,
            mode="allocation_void",
            company_id=company_id,
            period_end_date=period.end_date,
        )
        if _yec_msg:
            return _yec_msg

    if allocation.journal_entry_id:
        je = session.get(JournalEntry, allocation.journal_entry_id)
        if je:
            create_reversing_journal_entry(
                session, je, reason, company_id=company_id, commit_family=VOID_CASCADE_FAMILY
            )

    allocation.is_void = True
    allocation.voided_by_id = voider_id
    allocation.voided_at = datetime.datetime.now()
    allocation.void_reason = reason
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)
    return ""


def _allocate_all_pending(session, allocated_by_id: int, *, company_id: int | None = None) -> list:
    """Allocate all closed, unallocated periods in chronological order.

    Returns list of (period_name, allocation_id_or_None, error_string).
    """
    _period_q = session.query(FiscalPeriod).filter_by(is_closed=True).order_by(
        FiscalPeriod.start_date
    )
    if company_id is not None:
        _period_q = _period_q.filter(FiscalPeriod.company_id == company_id)
    periods = _period_q.all()
    results = []
    for period in periods:
        _alloc_q = session.query(PartnerProfitAllocation).filter_by(
            fiscal_period_id=period.id, is_void=False
        )
        if company_id is not None:
            _alloc_q = _alloc_q.filter(PartnerProfitAllocation.company_id == company_id)
        existing = _alloc_q.first()
        if existing:
            continue
        alloc_id, err = allocate_profit_to_partners(
            session, period.id, allocated_by_id, company_id=company_id
        )
        results.append((period.name, alloc_id, err))
    return results


def _calculate_account_balance_for_period(
    session,
    account,
    start_date,
    end_date,
    exclude_refs=None,
    *,
    company_id: int | None = None,
):
    """Verbatim from app.py ``calculate_account_balance_for_period`` with explicit company_id."""
    q = (
        session.query(JournalEntryLine)
        .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
        .filter(
            JournalEntryLine.account_id == account.id,
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
    )
    if company_id is not None:
        q = q.filter(JournalEntry.company_id == company_id)
    if exclude_refs:
        q = q.filter(~JournalEntry.reference_type.in_(exclude_refs))
    lines = q.all()
    if account.account_type in ["Asset", "Expense"]:
        return sum((line.debit or 0) - (line.credit or 0) for line in lines)
    return sum((line.credit or 0) - (line.debit or 0) for line in lines)


def _calculate_account_balance(session, account, *, company_id: int | None = None):
    """Verbatim from app.py ``calculate_account_balance`` with explicit company_id."""
    if company_id is not None:
        q = (
            session.query(JournalEntryLine)
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
            .filter(
                JournalEntryLine.account_id == account.id,
                JournalEntry.company_id == company_id,
            )
        )
    else:
        q = session.query(JournalEntryLine).filter_by(account_id=account.id)
    lines = q.all()
    if account.account_type in ["Asset", "Expense"]:
        return sum((line.debit or 0) - (line.credit or 0) for line in lines)
    return sum((line.credit or 0) - (line.debit or 0) for line in lines)


def _get_year_bounds(fiscal_year: str) -> tuple[datetime.date, datetime.date]:
    """Return (Jan 1, Dec 31) for the given fiscal_year string (e.g. '2026')."""
    year = int(fiscal_year)
    return datetime.date(year, 1, 1), datetime.date(year, 12, 31)


def _check_period_continuity(
    session,
    year_start: datetime.date,
    year_end: datetime.date,
    *,
    company_id: int | None = None,
) -> str:
    """Check that fiscal periods fully and continuously cover [year_start, year_end]."""
    _period_q = session.query(FiscalPeriod).filter(
        FiscalPeriod.start_date >= year_start,
        FiscalPeriod.end_date <= year_end,
    )
    if company_id is not None:
        _period_q = _period_q.filter(FiscalPeriod.company_id == company_id)
    periods = _period_q.order_by(FiscalPeriod.start_date).all()
    if not periods:
        return f"No fiscal periods exist for this year ({year_start} – {year_end})."

    if periods[0].start_date != year_start:
        return (
            f"Gap at start of year: {year_start} to "
            f"{periods[0].start_date - datetime.timedelta(days=1)} "
            "is not covered by any fiscal period."
        )

    for i in range(len(periods) - 1):
        expected_next = periods[i].end_date + datetime.timedelta(days=1)
        if periods[i + 1].start_date != expected_next:
            gap_start = periods[i].end_date + datetime.timedelta(days=1)
            gap_end = periods[i + 1].start_date - datetime.timedelta(days=1)
            return (
                f"Gap detected: {gap_start} to {gap_end} "
                "is not covered by any fiscal period."
            )

    if periods[-1].end_date != year_end:
        return (
            f"Gap at end of year: "
            f"{periods[-1].end_date + datetime.timedelta(days=1)} to {year_end} "
            "is not covered by any fiscal period."
        )

    return ""


def close_fiscal_period(session, period_id, *, company_id: int | None = None):
    """Post closing entries for the period and mark it locked.

    PS-P6-4: verbatim from app.py. App shim writes the audit row on success.
    Raises ValueError on guard failure. Returns the PeriodClose JournalEntry.
    """
    period = session.get(FiscalPeriod, period_id)
    if not period or period.is_closed:
        raise ValueError("Period not found or already closed.")

    re_acct = get_account_by_name(session, "Retained Earnings", company_id=company_id)
    if not re_acct:
        raise ValueError("Retained Earnings account not found in Chart of Accounts.")

    _acct_q = session.query(ChartOfAccounts).filter_by(is_active=True)
    if company_id is not None:
        _acct_q = _acct_q.filter(ChartOfAccounts.company_id == company_id)
    accounts = _acct_q.all()
    lines = []
    total_income = 0.0
    total_expense = 0.0

    for acct in accounts:
        if acct.account_type == "Income":
            bal = _calculate_account_balance_for_period(
                session,
                acct,
                period.start_date,
                period.end_date,
                exclude_refs=["PeriodClose"],
                company_id=company_id,
            )
            if bal > 0.005:
                lines.append((acct.id, bal, 0))
                total_income += bal
        elif acct.account_type == "Expense":
            bal = _calculate_account_balance_for_period(
                session,
                acct,
                period.start_date,
                period.end_date,
                exclude_refs=["PeriodClose"],
                company_id=company_id,
            )
            if bal > 0.005:
                lines.append((acct.id, 0, bal))
                total_expense += bal

    if not lines:
        raise ValueError("No income or expense activity in this period. Nothing to close.")

    net_income = total_income - total_expense
    if net_income > 0.005:
        lines.append((re_acct.id, 0, net_income))
    elif net_income < -0.005:
        lines.append((re_acct.id, abs(net_income), 0))

    je = create_journal_entry(
        session,
        period.end_date,
        f"Period Close: {period.name}",
        "PeriodClose",
        period_id,
        lines,
        company_id=company_id,
        commit_family=PERIOD_CLOSE_FAMILY,
    )

    period.is_closed = True
    period.closed_at = datetime.date.today()
    period.closing_je_id = je.id
    _kernel_persist(session, commit_family=PERIOD_CLOSE_FAMILY)
    return je


def perform_year_end_close(
    session,
    fiscal_year: str,
    closed_by_id: int = None,
    notes: str = None,
    acknowledged_warnings: list = None,
    *,
    company_id: int | None = None,
) -> tuple[int | None, list, str]:
    """Validate and close a fiscal year.

    PS-P6-4: verbatim from app.py. App shim writes the audit row on ``""`` success.
    """
    if acknowledged_warnings is None:
        acknowledged_warnings = []

    year_start, year_end = _get_year_bounds(fiscal_year)

    gap_err = _check_period_continuity(
        session, year_start, year_end, company_id=company_id
    )
    if gap_err:
        return None, [], gap_err

    _yec_q = session.query(YearEndClose).filter(
        YearEndClose.fiscal_year == fiscal_year,
        YearEndClose.is_void == False,  # noqa: E712 — verbatim
    )
    if company_id is not None:
        _yec_q = _yec_q.filter(YearEndClose.company_id == company_id)
    existing = _yec_q.first()
    if existing:
        return None, [], f"Year {fiscal_year} is already closed (Year-End Close #{existing.id})."

    _period_q = session.query(FiscalPeriod).filter(
        FiscalPeriod.start_date >= year_start,
        FiscalPeriod.end_date <= year_end,
    )
    if company_id is not None:
        _period_q = _period_q.filter(FiscalPeriod.company_id == company_id)
    periods_in_year = _period_q.order_by(FiscalPeriod.start_date).all()
    open_periods = [p for p in periods_in_year if not p.is_closed]
    if open_periods:
        names = ", ".join(p.name for p in open_periods[:3])
        suffix = f" (and {len(open_periods) - 3} more)" if len(open_periods) > 3 else ""
        return None, [], f"Not all periods are closed. Open: {names}{suffix}."

    unallocated = []
    for p in periods_in_year:
        _alloc_q = session.query(PartnerProfitAllocation).filter_by(
            fiscal_period_id=p.id, is_void=False
        )
        if company_id is not None:
            _alloc_q = _alloc_q.filter(PartnerProfitAllocation.company_id == company_id)
        alloc = _alloc_q.first()
        if not alloc:
            unallocated.append(p.name)
    if unallocated:
        names = ", ".join(unallocated[:3])
        suffix = f" (and {len(unallocated) - 3} more)" if len(unallocated) > 3 else ""
        return None, [], f"Periods missing profit allocation: {names}{suffix}."

    valid, total_pct, share_err = _validate_partner_shares(session, company_id=company_id)
    if not valid:
        return None, [], f"Partner shares invalid: {share_err}"

    from sqlalchemy import func as _func

    _tb_q = (
        session.query(JournalEntryLine)
        .with_entities(
            _func.sum(JournalEntryLine.debit).label("total_debit"),
            _func.sum(JournalEntryLine.credit).label("total_credit"),
        )
        .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
        .filter(
            JournalEntry.entry_date >= year_start,
            JournalEntry.entry_date <= year_end,
        )
    )
    if company_id is not None:
        _tb_q = _tb_q.filter(JournalEntry.company_id == company_id)
    tb = _tb_q.one()
    total_debit = tb.total_debit or 0.0
    total_credit = tb.total_credit or 0.0
    if abs(total_debit - total_credit) > 0.01:
        return None, [], (
            f"Trial Balance is not balanced for year {fiscal_year}: "
            f"Debit {total_debit:,.2f} vs Credit {total_credit:,.2f}."
        )

    warnings = []

    re_acct = get_account_by_name(session, "Retained Earnings", company_id=company_id)
    re_balance = (
        _calculate_account_balance(session, re_acct, company_id=company_id)
        if re_acct
        else 0.0
    )
    if abs(re_balance) > 0.01:
        warnings.append(
            (
                "re_residual",
                f"Retained Earnings has a residual balance of {re_balance:,.2f}. "
                "This may indicate rounding or an unallocated amount.",
            )
        )

    obe_acct = get_account_by_name(session, "Opening Balance Equity", company_id=company_id)
    obe_balance = (
        _calculate_account_balance(session, obe_acct, company_id=company_id)
        if obe_acct
        else 0.0
    )
    if abs(obe_balance) > 0.01:
        warnings.append(
            (
                "obe_balance",
                f"Opening Balance Equity (3900) has a non-zero balance of {obe_balance:,.2f}. "
                "It should be zero once all opening balances are entered.",
            )
        )

    _partner_q = session.query(Partner).filter(
        Partner.is_active == True,  # noqa: E712 — verbatim
        Partner.advance_account_id != None,  # noqa: E711 — verbatim
    )
    if company_id is not None:
        _partner_q = _partner_q.filter(Partner.company_id == company_id)
    partners_with_advances = _partner_q.all()
    for p in partners_with_advances:
        adv_acct = session.get(ChartOfAccounts, p.advance_account_id)
        if adv_acct:
            adv_bal = _calculate_account_balance(session, adv_acct, company_id=company_id)
            if abs(adv_bal) > 0.01:
                warnings.append(
                    (
                        f"advance_{p.id}",
                        f"Partner '{p.name}' has an outstanding advance balance of {adv_bal:,.2f}.",
                    )
                )

    legacy_3000 = get_account_by_name(session, "Owner Capital", company_id=company_id)
    legacy_3200 = get_account_by_name(session, "Owner Drawings", company_id=company_id)
    for legacy_acct, key in [(legacy_3000, "legacy_capital"), (legacy_3200, "legacy_drawings")]:
        if legacy_acct:
            bal = _calculate_account_balance(session, legacy_acct, company_id=company_id)
            if abs(bal) > 0.01:
                warnings.append(
                    (
                        key,
                        f"Legacy account '{legacy_acct.account_name}' ({legacy_acct.account_code}) "
                        f"has a non-zero balance of {bal:,.2f}.",
                    )
                )

    _recon_q = session.query(DailyCashReconciliation).filter(
        DailyCashReconciliation.is_void == False,  # noqa: E712 — verbatim
        DailyCashReconciliation.status.in_(["pending_approval", "rejected"]),
        DailyCashReconciliation.date >= year_start,
        DailyCashReconciliation.date <= year_end,
    )
    if company_id is not None:
        _recon_q = _recon_q.filter(DailyCashReconciliation.company_id == company_id)
    unresolved_recons = _recon_q.count()
    if unresolved_recons > 0:
        warnings.append(
            (
                "unresolved_recons",
                f"{unresolved_recons} cash reconciliation(s) in this year are unresolved "
                "(pending approval or rejected).",
            )
        )

    _eod_q = session.query(EndOfDayClose).filter(
        EndOfDayClose.is_void == False,  # noqa: E712 — verbatim
        EndOfDayClose.date >= year_start,
        EndOfDayClose.date <= year_end,
    )
    if company_id is not None:
        _eod_q = _eod_q.filter(EndOfDayClose.company_id == company_id)
    eod_count = _eod_q.count()
    if eod_count == 0:
        warnings.append(("stale_eod", "No End-of-Day closes recorded for this year."))

    unacked = [w for w in warnings if w[0] not in acknowledged_warnings]
    if unacked:
        return None, warnings, ""

    net_income_snapshot = sum(
        _get_period_net_income_from_je(session, p, company_id=company_id)
        for p in periods_in_year
    )

    yec = YearEndClose(
        fiscal_year=fiscal_year,
        start_date=year_start,
        end_date=year_end,
        status="closed",
        closed_by_id=closed_by_id,
        closed_at=datetime.datetime.now(),
        notes=notes.strip() if notes else None,
        period_count=len(periods_in_year),
        allocation_count=len(periods_in_year),
        net_income_snapshot=net_income_snapshot,
        re_balance_at_close=re_balance,
        warnings_acknowledged_json=json.dumps(acknowledged_warnings)
        if acknowledged_warnings
        else None,
        is_void=False,
        created_at=datetime.datetime.now(),
    )
    session.add(yec)
    _kernel_persist(session, commit_family=YEAR_END_CLOSE_FAMILY)
    return yec.id, warnings, ""
