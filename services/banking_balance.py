"""BANKING-SERVICE-01 BS-05 — cached BankAccount.balance delta helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import BankAccount, BankTransaction
from services.money import money_to_float, parse_money, quantize_money


def is_credit_card_account(ba: BankAccount | None) -> bool:
    if not ba:
        return False
    return (getattr(ba, "kind", None) or "bank") == "credit_card"


def apply_account_balance_delta(ba: BankAccount, txn_type: str, amount: float) -> None:
    """Update cached BankAccount.balance (bank asset vs credit-card liability)."""
    amt = quantize_money(amount)
    bal = parse_money(ba.balance)
    if is_credit_card_account(ba):
        if txn_type in ("withdrawal", "transfer"):
            ba.balance = quantize_money(bal + amt)
        else:
            ba.balance = quantize_money(bal - amt)
    elif txn_type == "deposit":
        ba.balance = quantize_money(bal + amt)
    else:
        ba.balance = quantize_money(bal - amt)


def reverse_account_balance_delta(ba: BankAccount, txn_type: str, amount: float) -> None:
    """Undo a balance change when voiding a BankTransaction."""
    amt = quantize_money(amount)
    bal = parse_money(ba.balance)
    if is_credit_card_account(ba):
        if txn_type in ("withdrawal", "transfer"):
            ba.balance = quantize_money(bal - amt)
        else:
            ba.balance = quantize_money(bal + amt)
    elif txn_type == "deposit":
        ba.balance = quantize_money(bal - amt)
    else:
        ba.balance = quantize_money(bal + amt)


def derive_bank_account_balance(session: Session, ba: BankAccount) -> float:
    """Derive cached balance from non-void BankTransaction sums."""
    txns = (
        session.query(BankTransaction)
        .filter(
            BankTransaction.account_id == ba.id,
            BankTransaction.is_void == False,  # noqa: E712
        )
        .all()
    )
    dep = wd = xfer = 0.0
    xfer_in = xfer_out = 0.0
    for txn in txns:
        amt = money_to_float(txn.amount)
        if txn.type == "deposit":
            dep += amt
        elif txn.type == "withdrawal":
            wd += amt
        elif txn.type == "transfer":
            xfer += amt
            desc = txn.description or ""
            if desc.startswith("Transfer from"):
                xfer_in += amt
            else:
                xfer_out += amt
    if is_credit_card_account(ba):
        return money_to_float(wd + xfer - dep)
    return money_to_float(dep - wd + xfer_in - xfer_out)


def sync_bank_account_balances(session: Session) -> None:
    """Re-sync BankAccount.balance from non-void transaction sums."""
    accounts = session.query(BankAccount).all()
    for ba in accounts:
        ba.balance = quantize_money(derive_bank_account_balance(session, ba))
    session.commit()
