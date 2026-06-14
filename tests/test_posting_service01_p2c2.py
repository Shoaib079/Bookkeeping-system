"""POSTING-SERVICE-01 PS-P2c-2 — post_expense + post_payable_payment extraction proof."""

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


def test_post_expense_shim_delegates():
    block = _fn_block("post_expense")
    assert "posting_service.post_expense(" in block
    assert "company_id=_current_company_id()" in block
    for leftover in (
        "Rent Expense",
        "resolve_payment_credit_account",
        "create_journal_entry(",
        "sync_company_cc_subledger",
        "_sync_company_cc_subledger",
        "ExpenseRecord",
    ):
        assert leftover not in block


def test_post_payable_payment_shim_delegates():
    block = _fn_block("post_payable_payment")
    assert "posting_service.post_payable_payment(" in block
    assert "company_id=_current_company_id()" in block
    for leftover in (
        "Accounts Payable",
        "resolve_payment_credit_account",
        "create_journal_entry(",
        "sync_company_cc_subledger",
        "_sync_company_cc_subledger",
        "PayablePayment",
        "je.id",
    ):
        assert leftover not in block


def test_posting_service_has_post_expense_and_payable_payment():
    assert "def post_expense(" in POSTING_SRC
    assert "def post_payable_payment(" in POSTING_SRC
    assert "reference_id=je.id" in POSTING_SRC
    assert "sync_company_cc_subledger(" in POSTING_SRC


def test_posting_service_import_purity_ps_p2c2():
    forbidden = [
        r"^\s*import streamlit\b",
        r"^\s*from streamlit\b",
        r"\bst\.session_state\b",
        r"\b_current_company_id\b",
        r"^\s*from app import\b",
        r"^\s*import app\b",
        r"\bdef _t\b",
    ]
    for pattern in forbidden:
        assert re.search(pattern, POSTING_SRC, re.M) is None, pattern
