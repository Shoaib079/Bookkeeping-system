"""POSTING-SERVICE-01 PS-P3-3a — purchase cascade helper extraction proof."""

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


def test_linked_purchase_payable_shim_delegates():
    block = _fn_block("_linked_purchase_payable")
    assert "posting_service.linked_purchase_payable(" in block
    assert "company_id=current_company_required()" in block
    for leftover in (
        "cq(session",
        "filter_by(purchase_id",
        "session.query(Payable",
    ):
        assert leftover not in block


def test_void_purchase_linked_payable_shim_delegates():
    block = _fn_block("_void_purchase_linked_payable")
    assert "posting_service.void_purchase_linked_payable(" in block
    assert "company_id=current_company_required()" in block
    for leftover in (
        "reverse_cc_subledgers_for_gl_reference",
        "reverse_journal_entries_for",
        "linked.is_void",
        "session.commit()",
        "log_audit",
        "_linked_purchase_payable(",
    ):
        assert leftover not in block


def test_posting_service_has_purchase_cascade_helpers():
    assert "def linked_purchase_payable(" in POSTING_SRC
    assert "def void_purchase_linked_payable(" in POSTING_SRC
    assert "Payable.company_id == company_id" in POSTING_SRC
    assert "Payable.purchase_id == purchase_id" in POSTING_SRC
    assert '"PayablePayment"' in POSTING_SRC


def test_posting_service_import_purity_ps_p3_3a():
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
