"""POSTING-SERVICE-01 — GL posting kernel and incremental extraction.

PS-P1: `create_journal_entry` + period/year-end guard (verbatim from app.py).
PS-P2a: `get_account_by_name`, sales `post_*` trio, `card_settlement_on`.
PS-P2b: `resolve_payment_credit_account`, `post_payable_creation`.
PS-P2c-1: `sync_company_cc_subledger`.
PS-P2c-2: `post_expense`, `post_payable_payment`.

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

from models import (
    ChartOfAccounts,
    ExpenseRecord,
    FiscalPeriod,
    JournalEntry,
    JournalEntryLine,
    Payable,
    YearEndClose,
)
from reconciliation.company_card import (
    CompanyCardError,
    company_card_enabled,
    post_cc_subledger_charge,
    resolve_company_credit_card_account_id,
)
from registry.service import get_setting

# Pinned by PS-P2b-CHAR — must match registry/locales/transactional.py EN strings.
_CC_DISABLED_MSG = (
    "Company Credit Card is not enabled. Enable it in Banking → Settings first."
)
_CC_GL_MISSING_MSG = "Credit Card Payable GL account is missing."
_CC_NO_CARDS_MSG = (
    "No active company credit card account. Add one under Banking → Accounts."
)
_COMPANY_CC_METHOD = "Credit Card"


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


def resolve_payment_credit_account(
    session,
    payment_method: str,
    *,
    currency=None,
    company_id: int | None = None,
    gl_company_id: int | None = None,
):
    """Cash/Bank/Company Credit Card → GL account to credit on business payment posting.

    PS-P2b: verbatim from app.py ``_resolve_payment_credit_account``. The shim
    supplies ``gl_company_id`` from the ambient session company (legacy
    ``get_account_by_name`` scope). ``company_id`` gates ``company_card_enabled``
    only on the Credit Card branch — see TD-PS-06.
    """
    pm = (payment_method or "").lower().strip()
    if pm == "bank":
        return get_account_by_name(session, "Bank", currency=currency, company_id=gl_company_id)
    if pm == "credit card":
        cid = company_id or gl_company_id
        if not cid or not company_card_enabled(session, cid):
            raise ValueError(_CC_DISABLED_MSG)
        cc_acct = get_account_by_name(session, "Credit Card Payable", company_id=gl_company_id)
        if not cc_acct:
            raise ValueError(_CC_GL_MISSING_MSG)
        return cc_acct
    if pm == "cash":
        return get_account_by_name(session, "Cash", currency=currency, company_id=gl_company_id)
    cash_acct = get_account_by_name(session, "Cash", currency=currency, company_id=gl_company_id)
    bank_acct = get_account_by_name(session, "Bank", currency=currency, company_id=gl_company_id)
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
    ambient_company_id: int | None = None,
) -> None:
    """AD-011: mirror GL CC charge on card BankAccount sub-ledger (no extra JE).

    PS-P2c-1: verbatim from app.py ``_sync_company_cc_subledger``. The shim
    supplies ``ambient_company_id`` from the session company (legacy ambient
    fallback when ``company_id`` is None).
    """
    if (payment_method or "") != _COMPANY_CC_METHOD:
        return
    company_id = company_id or ambient_company_id
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
    gl_company_id: int | None = None,
    ambient_company_id: int | None = None,
):
    """Post expense: Debit Expense Account, Credit Cash/Bank/Credit Card Payable.

    PS-P2c-2: verbatim from app.py. Shim supplies ``gl_company_id`` and
    ``ambient_company_id`` from the session company (legacy ambient GL scope
    and CC subledger fallback). Record ``company_id`` gates CC enablement via
    ``resolve_payment_credit_account`` — see TD-PS-06.
    """
    expense = session.get(ExpenseRecord, expense_id)
    cid = expense.company_id if expense else None
    credit_acct = resolve_payment_credit_account(
        session, payment_method, currency=currency, company_id=cid, gl_company_id=gl_company_id
    )
    if not credit_acct:
        return

    expense_acct = None
    if "rent" in category.lower():
        expense_acct = get_account_by_name(session, "Rent Expense", company_id=gl_company_id)
    elif "salary" in category.lower():
        expense_acct = get_account_by_name(session, "Salary Expense", company_id=gl_company_id)
    elif "utility" in category.lower():
        expense_acct = get_account_by_name(session, "Utility Expense", company_id=gl_company_id)
    elif "advertising" in category.lower():
        expense_acct = get_account_by_name(session, "Advertising Expense", company_id=gl_company_id)
    elif "fuel" in category.lower():
        expense_acct = get_account_by_name(session, "Fuel Expense", company_id=gl_company_id)
    elif "office" in category.lower() or "other" in category.lower():
        expense_acct = get_account_by_name(session, "Office Expense", company_id=gl_company_id)
    else:
        expense_acct = get_account_by_name(session, "Office Expense", company_id=gl_company_id)

    if expense_acct:
        create_journal_entry(
            session, expense_date,
            f"{category} Expense (ID: {expense_id})",
            "Expense", expense_id,
            [(expense_acct.id, amount, 0), (credit_acct.id, 0, amount)],
            currency=currency,
            company_id=gl_company_id,
        )
        sync_company_cc_subledger(
            session,
            payment_method,
            company_id=cid,
            credit_card_account_id=credit_card_account_id
            or (expense.credit_card_account_id if expense else None),
            amount=amount,
            txn_date=expense_date,
            description=f"CC expense EXP#{expense_id} — {category}",
            reference_type="Expense",
            reference_id=expense_id,
            record=expense,
            ambient_company_id=ambient_company_id,
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
    gl_company_id: int | None = None,
    ambient_company_id: int | None = None,
):
    """Post payable payment: Debit AP, Credit Cash/Bank/Credit Card Payable.

    PS-P2c-2: verbatim from app.py. Subledger ``reference_id`` is ``je.id``,
    not ``payable_id``. Shim supplies ambient GL/CC scope — see TD-PS-06.
    """
    ap_acct = get_account_by_name(session, "Accounts Payable", company_id=gl_company_id)
    payable = session.get(Payable, payable_id)
    cid = payable.company_id if payable else None
    credit_acct = resolve_payment_credit_account(
        session, payment_method, currency=currency, company_id=cid, gl_company_id=gl_company_id
    )
    if ap_acct and credit_acct:
        je = create_journal_entry(
            session, date,
            f"Payable Payment (ID: {payable_id})",
            "PayablePayment", payable_id,
            [(ap_acct.id, amount, 0), (credit_acct.id, 0, amount)],
            currency=currency,
            company_id=gl_company_id,
        )
        sync_company_cc_subledger(
            session,
            payment_method,
            company_id=cid,
            credit_card_account_id=credit_card_account_id
            or (payable.credit_card_account_id if payable else None),
            amount=amount,
            txn_date=date,
            description=f"CC payable payment PAY#{payable_id}",
            reference_type="PayablePayment",
            reference_id=je.id,
            record=payable,
            ambient_company_id=ambient_company_id,
        )
