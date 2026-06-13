"""POSTING-SERVICE-01 — GL posting kernel and incremental extraction.

PS-P1: `create_journal_entry` + period/year-end guard (verbatim from app.py).
PS-P2a: `get_account_by_name`, sales `post_*` trio, `card_settlement_on`.

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

from models import ChartOfAccounts, FiscalPeriod, JournalEntry, JournalEntryLine, YearEndClose
from registry.service import get_setting


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
