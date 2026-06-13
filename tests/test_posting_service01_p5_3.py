"""POSTING-SERVICE-01 PS-P5-3 — simple equity extraction proof."""

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


def test_post_capital_contribution_shim_delegates():
    block = _fn_block("post_capital_contribution")
    assert "posting_service.post_capital_contribution(" in block
    assert "company_id=_current_company_id()" in block
    for leftover in ("CapitalContribution", "Owner Capital", "create_journal_entry("):
        assert leftover not in block


def test_post_owner_drawing_shim_delegates():
    block = _fn_block("post_owner_drawing")
    assert "posting_service.post_owner_drawing(" in block
    assert "company_id=_current_company_id()" in block
    for leftover in ("OwnerDrawing", "Owner Drawings", "create_journal_entry("):
        assert leftover not in block


def test_post_salary_shim_delegates():
    block = _fn_block("post_salary")
    assert "posting_service.post_salary(" in block
    assert "company_id=_current_company_id()" in block
    for leftover in ("Salary Expense", '"Salary"', "create_journal_entry("):
        assert leftover not in block


def test_void_equity_movement_shim_delegates():
    block = _fn_block("void_equity_movement")
    assert "posting_service.void_equity_movement(" in block
    assert "company_id=current_company_required()" in block
    assert 'log_audit(' in block
    assert '"EquityMovement"' in block
    for leftover in (
        "reverse_journal_entries_for",
        "session.commit()",
        "btxn.is_void",
        "acct.balance",
    ):
        assert leftover not in block


def test_posting_service_has_simple_equity_functions():
    assert "def post_capital_contribution(" in POSTING_SRC
    assert "def post_owner_drawing(" in POSTING_SRC
    assert "def post_salary(" in POSTING_SRC
    assert "def void_equity_movement(" in POSTING_SRC
    assert '"CapitalContribution"' in POSTING_SRC
    assert '"OwnerDrawing"' in POSTING_SRC
    assert '"Salary"' in POSTING_SRC


def test_posting_service_import_purity_ps_p5_3():
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
