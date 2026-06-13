"""POSTING-SERVICE-01 PS-P2b — payable resolver + post_payable_creation extraction proof."""

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


def test_resolve_payment_credit_account_shim_delegates():
    block = _fn_block("_resolve_payment_credit_account")
    assert "posting_service.resolve_payment_credit_account(" in block
    assert "gl_company_id=_current_company_id()" in block
    for leftover in ("company_card_enabled", "Credit Card Payable", ".lower().strip()"):
        assert leftover not in block


def test_post_payable_creation_shim_delegates():
    block = _fn_block("post_payable_creation")
    assert "posting_service.post_payable_creation(" in block
    assert "company_id=_current_company_id()" in block
    for leftover in ("Rent Expense", "create_journal_entry(", "PayableCreation"):
        assert leftover not in block


def test_posting_service_has_resolve_and_payable_creation():
    assert "def resolve_payment_credit_account(" in POSTING_SRC
    assert "def post_payable_creation(" in POSTING_SRC
    assert "gl_company_id" in POSTING_SRC
    assert "TD-PS-06" in POSTING_SRC or "company_card_enabled" in POSTING_SRC


def test_posting_service_import_purity_ps_p2b():
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
