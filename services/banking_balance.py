"""BANKING-SERVICE-01 BS-05 — cached BankAccount.balance delta helpers."""

from __future__ import annotations

from models import BankAccount


def _is_credit_card_account(ba: BankAccount | None) -> bool:
    if not ba:
        return False
    return (getattr(ba, "kind", None) or "bank") == "credit_card"


def apply_account_balance_delta(ba: BankAccount, txn_type: str, amount: float) -> None:
    """Update cached BankAccount.balance (bank asset vs credit-card liability)."""
    amt = round(float(amount), 2)
    bal = ba.balance or 0
    if _is_credit_card_account(ba):
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
    if _is_credit_card_account(ba):
        if txn_type in ("withdrawal", "transfer"):
            ba.balance = bal - amt
        else:
            ba.balance = bal + amt
    elif txn_type == "deposit":
        ba.balance = bal - amt
    else:
        ba.balance = bal + amt
