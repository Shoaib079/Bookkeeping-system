"""POSTING-SERVICE-01 PS-P5-1 — receivables extraction proof."""

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


def test_compute_sale_balance_status_shim_delegates():
    block = _fn_block("compute_sale_balance_status")
    assert "posting_service.compute_sale_balance_status(" in block
    for leftover in ('status = "Paid"', 'status = "Partial"', 'status = "Open"'):
        assert leftover not in block


def test_post_receivable_payment_shim_delegates():
    block = _fn_block("post_receivable_payment")
    assert "posting_service.post_receivable_payment(" in block
    assert "company_id=_current_company_id()" in block
    for leftover in (
        "ReceivablePayment",
        "FX Gain",
        "FX Loss",
        "create_journal_entry(",
        "sale.paid_amount",
        "compute_sale_balance_status(",
    ):
        assert leftover not in block


def test_posting_service_has_compute_sale_balance_status_and_post_receivable_payment():
    assert "def compute_sale_balance_status(" in POSTING_SRC
    assert "def post_receivable_payment(" in POSTING_SRC
    assert '"ReceivablePayment"' in POSTING_SRC
    assert '"FX Gain"' in POSTING_SRC
    assert '"FX Loss"' in POSTING_SRC


def test_posting_service_import_purity_ps_p5_1():
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
