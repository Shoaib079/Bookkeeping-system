"""POSTING-SERVICE-01 PS-P4-2 — void_bank_transaction extraction proof."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")
POSTING_SRC = (ROOT / "services" / "posting.py").read_text(encoding="utf-8")


def _fn_block(name: str) -> str:
    i = APP_SRC.index(f"def {name}(")
    j = APP_SRC.index("\ndef ", i + 10)
    return APP_SRC[i:j]


def test_void_bank_transaction_shim_delegates():
    block = _fn_block("void_bank_transaction")
    assert "posting_service.void_bank_transaction(" in block
    assert "company_id=current_company_required()" in block
    assert "if ok:" in block
    assert 'log_audit(' in block
    assert '"BankTransaction"' in block
    for leftover in (
        "reverse_journal_entries_for",
        "reverse_account_balance_delta",
        "session.commit()",
        "txn.is_void",
        "cq(",
        'BankTransaction.description.like',
        "Paired with voided transfer",
    ):
        assert leftover not in block


def test_posting_service_has_void_bank_transaction():
    assert "def void_bank_transaction(" in POSTING_SRC
    assert (
        '("BankDeposit", "BankWithdrawal", "BankTransfer")'
        in POSTING_SRC
    )
    assert "Paired with voided transfer TXN#" in POSTING_SRC
    assert "reverse_account_balance_delta" in POSTING_SRC


def test_posting_service_import_purity_ps_p4_2():
    forbidden = [
        r"^\s*import streamlit\b",
        r"^\s*from streamlit\b",
        r"\bst\.session_state\b",
        r"\b_current_company_id\b",
        r"\bcurrent_company_required\b",
        r"^\s*from app import\b",
        r"^\s*import app\b",
        r"\bdef _t\b",
        r"\bcq\(",
        r"\blog_audit\b",
    ]
    for pattern in forbidden:
        assert re.search(pattern, POSTING_SRC, re.M) is None, pattern
