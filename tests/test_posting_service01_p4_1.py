"""POSTING-SERVICE-01 PS-P4-1 — post_bank_transaction + post_bank_transfer extraction proof."""

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


def test_post_bank_transaction_shim_delegates():
    block = _fn_block("post_bank_transaction")
    assert "posting_service.post_bank_transaction(" in block
    assert "company_id=_current_company_id()" in block
    for leftover in (
        "BankDeposit",
        "BankWithdrawal",
        "create_journal_entry(",
        'get_account_by_name(session, "Cash"',
    ):
        assert leftover not in block


def test_post_bank_transfer_shim_delegates():
    block = _fn_block("post_bank_transfer")
    assert "posting_service.post_bank_transfer(" in block
    assert "company_id=_current_company_id()" in block
    for leftover in (
        "BankTransfer",
        "gl_for",
        "create_journal_entry(",
        'get_account_by_name(session, "Cash"',
    ):
        assert leftover not in block


def test_posting_service_has_post_bank_transaction_and_transfer():
    assert "def post_bank_transaction(" in POSTING_SRC
    assert "def post_bank_transfer(" in POSTING_SRC
    assert '"BankDeposit"' in POSTING_SRC
    assert '"BankWithdrawal"' in POSTING_SRC
    assert '"BankTransfer"' in POSTING_SRC


def test_posting_service_import_purity_ps_p4_1():
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
