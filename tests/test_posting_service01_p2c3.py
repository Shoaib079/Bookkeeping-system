"""POSTING-SERVICE-01 PS-P2c-3 — post_purchase + purchase helper extraction proof."""

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


def test_resolve_purchase_debit_account_shim_delegates():
    block = _fn_block("_resolve_purchase_debit_account")
    assert "posting_service.resolve_purchase_debit_account(" in block
    assert "company_id=_current_company_id()" in block
    for leftover in ("Rent Expense", "get_account_by_name(", "Inventory"):
        assert leftover not in block


def test_purchase_ref_type_shim_delegates():
    block = _fn_block("_purchase_ref_type")
    assert "posting_service.purchase_ref_type(" in block
    for leftover in ("CashPurchase", "CardPurchase", '== "Cash"'):
        assert leftover not in block


def test_post_purchase_shim_delegates():
    block = _fn_block("post_purchase")
    assert "posting_service.post_purchase(" in block
    assert "gl_company_id=_current_company_id()" in block
    assert "ambient_company_id=_current_company_id()" in block
    for leftover in (
        "resolve_purchase_debit_account",
        "purchase_ref_type",
        "resolve_payment_credit_account",
        "create_journal_entry(",
        "sync_company_cc_subledger",
        "_sync_company_cc_subledger",
        "Purchase",
    ):
        assert leftover not in block


def test_posting_service_has_post_purchase_and_helpers():
    assert "def resolve_purchase_debit_account(" in POSTING_SRC
    assert "def purchase_ref_type(" in POSTING_SRC
    assert "def post_purchase(" in POSTING_SRC
    assert "CardPurchase" in POSTING_SRC
    assert "reference_id=purchase_id" in POSTING_SRC


def test_posting_service_import_purity_ps_p2c3():
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
