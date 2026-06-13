"""POSTING-SERVICE-01 PS-P2c-1 — sync_company_cc_subledger extraction proof."""

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


def test_sync_company_cc_subledger_shim_delegates():
    block = _fn_block("_sync_company_cc_subledger")
    assert "posting_service.sync_company_cc_subledger(" in block
    assert "ambient_company_id=_current_company_id()" in block
    for leftover in (
        "resolve_company_credit_card_account_id",
        "post_cc_subledger_charge",
        "CompanyCardError",
        "_COMPANY_CC_METHOD",
        'form.err.company_cc_no_cards',
    ):
        assert leftover not in block


def test_posting_service_has_sync_company_cc_subledger():
    assert "def sync_company_cc_subledger(" in POSTING_SRC
    assert "resolve_company_credit_card_account_id" in POSTING_SRC
    assert "post_cc_subledger_charge" in POSTING_SRC
    assert "_CC_NO_CARDS_MSG" in POSTING_SRC
    assert "ambient_company_id" in POSTING_SRC


def test_posting_service_import_purity_ps_p2c1():
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
