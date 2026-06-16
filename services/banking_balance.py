"""BANKING-SERVICE-01 BS-05 — cached BankAccount.balance delta helpers."""

from __future__ import annotations

from models import BankAccount
from services.money import parse_money, quantize_money


def _is_credit_card_account(ba: BankAccount | None) -> bool:
    if not ba:
        return False
    return (getattr(ba, "kind", None) or "bank") == "credit_card"


def apply_account_balance_delta(ba: BankAccount, txn_type: str, amount: float) -> None:
    """Update cached BankAccount.balance (bank asset vs credit-card liability)."""
    amt = quantize_money(amount)
    bal = parse_money(ba.balance)
    if _is_credit_card_account(ba):
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
    if _is_credit_card_account(ba):
        if txn_type in ("withdrawal", "transfer"):
            ba.balance = quantize_money(bal - amt)
        else:
            ba.balance = quantize_money(bal + amt)
    elif txn_type == "deposit":
        ba.balance = quantize_money(bal - amt)
    else:
        ba.balance = quantize_money(bal + amt)
