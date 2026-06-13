"""POSTING-SERVICE-01 PS-P3-1 — reversal primitive extraction proof."""

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


def test_create_reversing_journal_entry_shim_delegates():
    block = _fn_block("create_reversing_journal_entry")
    assert "posting_service.create_reversing_journal_entry(" in block
    assert "company_id=_current_company_id()" in block
    for leftover in (
        "reversed_lines",
        "VOID:",
        "create_journal_entry(",
        "datetime.date.today()",
    ):
        assert leftover not in block


def test_reverse_journal_entries_for_shim_delegates():
    block = _fn_block("reverse_journal_entries_for")
    assert "posting_service.reverse_journal_entries_for(" in block
    assert "company_id=current_company_required()" in block
    for leftover in (
        "cq(session",
        "create_reversing_journal_entry(",
        "filter_by(reference_type",
    ):
        assert leftover not in block


def test_posting_service_has_reversal_primitives():
    assert "def create_reversing_journal_entry(" in POSTING_SRC
    assert "def reverse_journal_entries_for(" in POSTING_SRC
    assert 'f"VOID: {original_entry.description} — {void_reason}"' in POSTING_SRC
    assert '"Reversal"' in POSTING_SRC


def test_posting_service_import_purity_ps_p3_1():
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
    ]
    for pattern in forbidden:
        assert re.search(pattern, POSTING_SRC, re.M) is None, pattern
