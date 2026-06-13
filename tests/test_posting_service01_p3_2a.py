"""POSTING-SERVICE-01 PS-P3-2a — void_expense + void_payable extraction proof."""

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


def test_void_expense_shim_delegates():
    block = _fn_block("void_expense")
    assert "posting_service.void_expense(" in block
    assert "company_id=current_company_required()" in block
    assert "if ok:" in block
    assert 'log_audit(' in block
    assert '"ExpenseRecord"' in block
    for leftover in (
        "reverse_cc_subledgers_for_gl_reference",
        "reverse_journal_entries_for",
        "session.commit()",
        "expense.is_void",
        "session.get(ExpenseRecord",
    ):
        assert leftover not in block


def test_void_payable_shim_delegates():
    block = _fn_block("void_payable")
    assert "posting_service.void_payable(" in block
    assert "company_id=current_company_required()" in block
    assert "if ok:" in block
    assert 'log_audit(' in block
    assert '"Payable"' in block
    for leftover in (
        "reverse_cc_subledgers_for_gl_reference",
        "reverse_journal_entries_for",
        "session.commit()",
        "payable.is_void",
        "session.get(Payable",
        "PayableCreation",
        "PayablePayment",
    ):
        assert leftover not in block


def test_posting_service_has_void_expense_and_void_payable():
    assert "def void_expense(" in POSTING_SRC
    assert "def void_payable(" in POSTING_SRC
    assert 'reverse_cc_subledgers_for_gl_reference(' in POSTING_SRC
    assert '"Expense"' in POSTING_SRC
    assert '"PayableCreation"' in POSTING_SRC
    assert '"PayablePayment"' in POSTING_SRC


def test_posting_service_import_purity_ps_p3_2a():
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
