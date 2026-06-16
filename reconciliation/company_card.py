"""Company credit card — Phase 18-MVP-5 + AD-011 sub-ledger sync."""

from __future__ import annotations

import datetime
from typing import Any

from models import BankAccount, BankStatementImport, BankStatementRow, BankTransaction, JournalEntry
from registry.service import get_setting
from services import audit as audit_svc

COMPANY_CC_PAYMENT_METHOD = "Credit Card"


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


def cc_subledger_stmt_ref(reference_type: str, reference_id: int) -> str:
    """Stable key linking a CC charge to its BankTransaction (no GL)."""
    return f"ccc:{reference_type}:{reference_id}"


def resolve_company_credit_card_account_id(
    session,
    company_id: int,
    credit_card_account_id: int | None = None,
) -> int:
    """Auto-select when one active card; require explicit id when multiple."""
    cards = get_company_credit_card_accounts(session, company_id)
    if not cards:
        raise CompanyCardError(
            "No active company credit card account. Add one under Banking → Accounts."
        )
    if len(cards) == 1:
        return cards[0].id
    if credit_card_account_id is None:
        raise CompanyCardError("Select which company credit card this charge applies to.")
    cc_ba = session.get(BankAccount, credit_card_account_id)
    if (
        not cc_ba
        or cc_ba.company_id != company_id
        or not is_credit_card_account(cc_ba)
        or not cc_ba.is_active
    ):
        raise CompanyCardError("Invalid company credit card account.")
    return credit_card_account_id


def post_cc_subledger_charge(
    session,
    *,
    credit_card_account_id: int,
    amount: float,
    txn_date,
    description: str,
    reference_type: str,
    reference_id: int,
    company_id: int | None = None,
) -> int:
    """Record CC charge on card sub-ledger only (withdrawal increases liability cache)."""
    amt = round(float(amount), 2)
    if amt <= 0:
        raise CompanyCardError("Charge amount must be positive.")

    cc_ba = session.get(BankAccount, credit_card_account_id)
    if not cc_ba or not is_credit_card_account(cc_ba):
        raise CompanyCardError("Credit card account not found.")

    stmt_ref = cc_subledger_stmt_ref(reference_type, reference_id)
    existing = (
        session.query(BankTransaction)
        .filter(
            BankTransaction.statement_ref == stmt_ref,
            BankTransaction.is_void == False,  # noqa: E712
        )
        .first()
    )
    if existing:
        raise CompanyCardError(f"Sub-ledger charge already recorded ({stmt_ref}).")

    cc_btxn = BankTransaction(
        account_id=credit_card_account_id,
        date=txn_date,
        amount=amt,
        type="withdrawal",
        description=description,
        company_id=company_id or cc_ba.company_id,
        statement_ref=stmt_ref,
    )
    session.add(cc_btxn)
    session.flush()
    apply_account_balance_delta(cc_ba, "withdrawal", amt)
    session.add(cc_ba)
    return cc_btxn.id


def reverse_cc_subledger_charge(
    session,
    reference_type: str,
    reference_id: int,
    void_reason: str = "Reversal",
) -> bool:
    """Void the BankTransaction for a CC sub-ledger charge and reverse card balance."""
    stmt_ref = cc_subledger_stmt_ref(reference_type, reference_id)
    txn = (
        session.query(BankTransaction)
        .filter(
            BankTransaction.statement_ref == stmt_ref,
            BankTransaction.is_void == False,  # noqa: E712
        )
        .first()
    )
    if not txn:
        return False
    acct = session.get(BankAccount, txn.account_id)
    if acct:
        reverse_account_balance_delta(acct, txn.type, txn.amount)
        session.add(acct)
    txn.is_void = True
    txn.voided_at = datetime.date.today()
    txn.void_reason = void_reason
    return True


def reverse_cc_subledgers_for_gl_reference(
    session,
    reference_type: str,
    reference_id: int,
    void_reason: str = "Reversal",
) -> int:
    """Reverse CC sub-ledger rows for a GL reference (all PayablePayment JEs when voiding payable)."""
    reversed_count = 0
    if reference_type == "PayablePayment":
        entries = (
            session.query(JournalEntry)
            .filter_by(reference_type=reference_type, reference_id=reference_id)
            .all()
        )
        for entry in entries:
            if reverse_cc_subledger_charge(
                session, reference_type, entry.id, void_reason
            ):
                reversed_count += 1
    elif reverse_cc_subledger_charge(
        session, reference_type, reference_id, void_reason
    ):
        reversed_count = 1
    return reversed_count


CC_RECON_TOLERANCE = 0.01


def compute_cc_payable_recon_health(
    session,
    company_id: int,
    *,
    tolerance: float = CC_RECON_TOLERANCE,
) -> dict[str, Any]:
    """Compare GL Credit Card Payable (2110) to sum of active credit_card sub-ledgers.

    Read-only health check for Recon Health page. Does not modify data.
    """
    app = _app()
    enabled = company_card_enabled(session, company_id)
    gl_acct = app.get_account_by_name(session, "Credit Card Payable")
    gl_balance = (
        round(app.calculate_account_balance(session, gl_acct), 2) if gl_acct else 0.0
    )

    cards = get_company_credit_card_accounts(session, company_id)
    subledger_total = round(sum(c.balance or 0.0 for c in cards), 2)
    difference = round(gl_balance - subledger_total, 2)
    status = "ok" if abs(difference) < tolerance else "warning"

    card_rows: list[dict[str, Any]] = []
    for card in cards:
        last_txn = (
            session.query(BankTransaction)
            .filter(
                BankTransaction.account_id == card.id,
                BankTransaction.is_void == False,  # noqa: E712
            )
            .order_by(BankTransaction.date.desc(), BankTransaction.id.desc())
            .first()
        )
        card_rows.append(
            {
                "id": card.id,
                "name": card.name,
                "balance": round(card.balance or 0.0, 2),
                "last_activity_date": last_txn.date if last_txn else None,
                "currency": card.currency,
            }
        )

    return {
        "company_card_enabled": enabled,
        "gl_account_exists": gl_acct is not None,
        "gl_balance": gl_balance,
        "subledger_total": subledger_total,
        "difference": difference,
        "status": status,
        "tolerance": tolerance,
        "cards": card_rows,
    }


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
    from services import posting as posting_svc

    if not company_card_enabled(session, company_id):
        raise MatchPostError(
            "Enable **Company credit card** in Company Setup to post bill payments."
        )

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

    cc_payable = posting_svc.get_account_by_name(
        session, "Credit Card Payable", company_id=company_id
    )
    bank_gl = posting_svc.get_account_by_name(
        session, "Bank", currency=imp.currency, company_id=company_id
    )
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

    je = posting_svc.create_journal_entry(
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
        company_id=company_id,
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


def void_credit_card_bill_payment(
    session,
    row_id: int,
    company_id: int,
    void_reason: str,
    *,
    performed_by: str | None = None,
) -> dict[str, Any]:
    """Atomically void/unpost a posted credit card bill payment statement row."""
    from reconciliation.match_post import MatchPostError

    app = _app()
    row = session.get(BankStatementRow, row_id)
    if not row:
        raise MatchPostError("Statement row not found")
    imp = session.get(BankStatementImport, row.bank_statement_import_id)
    if not imp or imp.company_id != company_id:
        raise MatchPostError("Import not found for this company")
    if row.status == "voided":
        raise MatchPostError("This statement row is already voided.")
    if row.status != "posted":
        raise MatchPostError("Only posted rows can be unposted.")
    if row.match_type != "cc_bill_payment":
        raise MatchPostError(
            "Only credit card bill payment rows can be unposted with this action."
        )

    from services.commit_modes import VOID_CASCADE_FAMILY
    from services.posting import _kernel_persist, reverse_journal_entries_for

    reason = (void_reason or "").strip() or "Unpost bill payment"
    amt = round(float(row.amount), 2)

    reverse_journal_entries_for(
        session,
        "BankStmtCCBillPay",
        row.id,
        reason,
        company_id=company_id,
        commit_family=VOID_CASCADE_FAMILY,
    )

    if row.bank_transaction_id:
        bank_txn = session.get(BankTransaction, row.bank_transaction_id)
        if bank_txn and not bank_txn.is_void:
            bank_acct = session.get(BankAccount, bank_txn.account_id)
            if bank_acct:
                reverse_account_balance_delta(bank_acct, bank_txn.type, bank_txn.amount)
                session.add(bank_acct)
            bank_txn.is_void = True
            bank_txn.voided_at = datetime.date.today()
            bank_txn.void_reason = reason

    cc_stmt_ref = f"bsr:{row.id}:cc"
    cc_txn = (
        session.query(BankTransaction)
        .filter(
            BankTransaction.statement_ref == cc_stmt_ref,
            BankTransaction.is_void == False,  # noqa: E712
        )
        .first()
    )
    cc_txn_id = None
    if cc_txn:
        cc_txn_id = cc_txn.id
        cc_acct = session.get(BankAccount, cc_txn.account_id)
        if cc_acct:
            reverse_account_balance_delta(cc_acct, cc_txn.type, cc_txn.amount)
            session.add(cc_acct)
        cc_txn.is_void = True
        cc_txn.voided_at = datetime.date.today()
        cc_txn.void_reason = reason

    row.status = "voided"
    session.add(row)
    _kernel_persist(session, commit_family=VOID_CASCADE_FAMILY)
    audit_svc.record_audit(
        session,
        action=audit_svc.ACTION_VOID,
        entity_type=audit_svc.ENTITY_BANK_STATEMENT_ROW,
        entity_id=row.id,
        description=f"Unposted CC bill payment · {amt:,.2f}: {reason}",
        performed_by=performed_by,
        company_id=company_id,
    )
    return {
        "row_id": row.id,
        "amount": amt,
        "bank_transaction_id": row.bank_transaction_id,
        "credit_card_transaction_id": cc_txn_id,
        "status": "voided",
    }
