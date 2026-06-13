"""POSTING-SERVICE-01 PS-P5-4 — close/reconciliation void extraction proof."""

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


def test_void_reconciliation_shim_delegates():
    block = _fn_block("void_reconciliation")
    assert "posting_service.void_reconciliation(" in block
    assert "company_id=current_company_required()" in block
    assert "if not err:" in block
    assert 'log_audit(' in block
    assert '"DailyCashReconciliation"' in block
    for leftover in (
        "reverse_journal_entries_for",
        "session.commit()",
        "reconciliation.is_void",
        "cq(",
        '"CashReconciliation"',
    ):
        assert leftover not in block


def test_void_eod_close_shim_delegates():
    block = _fn_block("void_eod_close")
    assert "posting_service.void_eod_close(" in block
    assert "if not err:" in block
    assert 'log_audit(' in block
    assert '"EndOfDayClose"' in block
    assert "eod.date" in block
    for leftover in (
        "session.commit()",
        "eod.is_void",
        "eod.status",
    ):
        assert leftover not in block


def test_void_year_end_close_shim_delegates():
    block = _fn_block("void_year_end_close")
    assert "posting_service.void_year_end_close(" in block
    assert "if not err:" in block
    assert 'log_audit(' in block
    assert '"VoidYearEndClose"' in block
    assert "yec.fiscal_year" in block
    for leftover in (
        "session.commit()",
        "yec.is_void",
        "reason.strip()",
    ):
        assert leftover not in block


def test_posting_service_has_close_void_functions():
    assert "def void_reconciliation(" in POSTING_SRC
    assert "def void_eod_close(" in POSTING_SRC
    assert "def void_year_end_close(" in POSTING_SRC
    assert '"CashReconciliation"' in POSTING_SRC
    assert "Void reason is required." in POSTING_SRC


def test_posting_service_import_purity_ps_p5_4():
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
