"""POSTING-SERVICE-01 PS-P1 — journal-entry kernel (verbatim extraction).

Scope (PS-P1 only): `create_journal_entry` and its period/year-end guard,
moved verbatim from app.py. app.py keeps compatibility shims under the
original names so all existing call sites (app.py + reconciliation/) are
behaviourally untouched.

Deliberate PS-P1 deviations from the MIGRATION-READINESS-01 end state —
both preserved on purpose and logged in TECH_DEBT (TD-PS-01 / TD-PS-02):

- **Commits internally** (`session.commit()` on success, `session.rollback()`
  before raising) — exactly as the app.py original did. Boundary-owned
  transactions arrive with PS-P2+; changing commit ownership is explicitly
  out of PS-P1 scope.
- **company_id is an explicit parameter** (the one non-verbatim change —
  the original resolved the active company ambiently from session state).
  The app.py shim supplies it, preserving company/session behaviour for
  every legacy caller. `None` keeps the pre-14C unscoped behaviour
  (startup/migration callers).

No Streamlit, no app.py imports — enforced by contract test.
"""

from __future__ import annotations

from models import FiscalPeriod, JournalEntry, JournalEntryLine, YearEndClose


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
    session.commit()
    return entry
