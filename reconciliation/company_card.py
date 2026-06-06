"""Company credit card — Phase 18-MVP-5."""

from __future__ import annotations

from typing import Any

from models import BankAccount, BankStatementImport, BankStatementRow, BankTransaction
from registry.service import get_setting


class CompanyCardError(Exception):
    """Raised when company-card posting cannot proceed."""


def is_credit_card_account(ba: BankAccount | None) -> bool:
    if not ba:
        return False
    return (getattr(ba, "kind", None) or "bank") == "credit_card"


def company_card_enabled(session, company_id: int) -> bool:
    return bool(
        get_setting(session, "banking.company_card_enabled", company_id=company_id)
    )


def get_company_credit_card_accounts(session, company_id: int) -> list[BankAccount]:
    rows = (
        session.query(BankAccount)
        .filter(
            BankAccount.company_id == company_id,
            BankAccount.is_active == True,  # noqa: E712
            BankAccount.kind == "credit_card",
        )
        .order_by(BankAccount.name)
        .all()
    )
    return rows


def apply_account_balance_delta(ba: BankAccount, txn_type: str, amount: float) -> None:
    """Update cached BankAccount.balance (bank asset vs credit-card liability)."""
    amt = round(float(amount), 2)
    bal = ba.balance or 0
    if is_credit_card_account(ba):
        if txn_type in ("withdrawal", "transfer"):
            ba.balance = bal + amt
        else:
            ba.balance = bal - amt
    elif txn_type == "deposit":
        ba.balance = bal + amt
    else:
        ba.balance = bal - amt


def reverse_account_balance_delta(ba: BankAccount, txn_type: str, amount: float) -> None:
    """Undo a balance change when voiding a BankTransaction."""
    amt = round(float(amount), 2)
    bal = ba.balance or 0
    if is_credit_card_account(ba):
        if txn_type in ("withdrawal", "transfer"):
            ba.balance = bal - amt
        else:
            ba.balance = bal + amt
    elif txn_type == "deposit":
        ba.balance = bal - amt
    else:
        ba.balance = bal + amt


def _app():
    import app as app_module

    return app_module


def _row_context(session, row_id: int, company_id: int) -> tuple[BankStatementRow, BankStatementImport]:
    from reconciliation.match_post import _row_context as _ctx

    return _ctx(session, row_id, company_id)


def post_credit_card_bill_payment(
    session,
    *,
    row_id: int,
    company_id: int,
    credit_card_account_id: int,
    user_id: int | None,
) -> dict[str, Any]:
    """Post a bank-statement debit that pays the company credit card bill.

    GL: DR Credit Card Payable / CR Bank
    Sub-ledger: bank withdrawal + credit-card deposit (debt reduced).
    """
    from reconciliation.match_post import MatchPostError, _create_bank_txn, _finalize_row

    if not company_card_enabled(session, company_id):
        raise MatchPostError(
            "Enable **Company credit card** in Company Setup to post bill payments."
        )

    app = _app()
    row, imp = _row_context(session, row_id, company_id)
    if row.credit_amount and not row.debit_amount:
        raise MatchPostError("This row is a deposit, not a card bill payment")

    cc_ba = session.get(BankAccount, credit_card_account_id)
    if not cc_ba or cc_ba.company_id != company_id:
        raise MatchPostError("Credit card account not found")
    if not is_credit_card_account(cc_ba):
        raise MatchPostError("Selected account is not a company credit card")

    bank_ba = session.get(BankAccount, imp.bank_account_id)
    if not bank_ba or is_credit_card_account(bank_ba):
        raise MatchPostError("Statement import must be linked to a bank account")

    amt = round(float(row.amount), 2)
    if amt <= 0:
        raise MatchPostError("Payment amount must be positive")

    cc_payable = app.get_account_by_name(session, "Credit Card Payable")
    bank_gl = app.get_account_by_name(session, "Bank", currency=imp.currency)
    if not cc_payable or not bank_gl:
        raise MatchPostError("Credit Card Payable or Bank GL account missing")

    btxn = _create_bank_txn(
        session,
        bank_account_id=imp.bank_account_id,
        row=row,
        company_id=company_id,
        txn_type="withdrawal",
    )

    cc_btxn = BankTransaction(
        account_id=credit_card_account_id,
        date=row.date,
        amount=amt,
        type="deposit",
        description=(
            f"Bill payment — stmt row {row.import_row_index} "
            f"({(row.description or '')[:80]})"
        ),
        company_id=company_id,
        is_reconciled=True,
        statement_ref=f"bsr:{row.id}:cc",
    )
    session.add(cc_btxn)
    session.flush()
    apply_account_balance_delta(cc_ba, "deposit", amt)
    session.add(cc_ba)

    je = app.create_journal_entry(
        session,
        row.date,
        (
            f"Credit card bill payment — {cc_ba.name} "
            f"(stmt row {row.import_row_index})"
        ),
        "BankStmtCCBillPay",
        row.id,
        [(cc_payable.id, amt, 0), (bank_gl.id, 0, amt)],
        currency=imp.currency,
    )

    row.credit_card_account_id = credit_card_account_id
    _finalize_row(
        session,
        row,
        match_type="cc_bill_payment",
        journal_entry_id=je.id,
        bank_transaction_id=btxn.id,
        user_id=user_id,
    )
    session.commit()
    return {
        "journal_entry_id": je.id,
        "bank_transaction_id": btxn.id,
        "credit_card_transaction_id": cc_btxn.id,
        "amount": amt,
        "match_type": "cc_bill_payment",
    }
