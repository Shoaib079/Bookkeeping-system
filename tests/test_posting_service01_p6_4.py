"""POSTING-SERVICE-01 PS-P6-4 — fiscal close extraction proof."""

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


def test_close_fiscal_period_shim_delegates():
    block = _fn_block("close_fiscal_period")
    assert "posting_service.close_fiscal_period(" in block
    assert "company_id=current_company_required()" in block
    assert 'log_audit(' in block
    assert '"PeriodClose"' in block
    assert '"FiscalPeriod"' in block
    for leftover in (
        "create_journal_entry(",
        "session.commit()",
        "calculate_account_balance_for_period",
        "raise ValueError",
        "cq(",
    ):
        assert leftover not in block


def test_perform_year_end_close_shim_delegates():
    block = _fn_block("perform_year_end_close")
    assert "posting_service.perform_year_end_close(" in block
    assert "company_id=current_company_required()" in block
    assert 'if err == "" and yec_id is not None:' in block
    assert 'log_audit(' in block
    assert '"YearEndClose"' in block
    for leftover in (
        "session.commit()",
        "YearEndClose(",
        "yec_block_message(",
        "cq(",
        "calculate_account_balance(",
    ):
        assert leftover not in block


def test_check_period_continuity_shim_delegates():
    block = _fn_block("_check_period_continuity")
    assert "posting_service._check_period_continuity(" in block
    assert "company_id=current_company_required()" in block
    assert "cq(" not in block


def test_get_year_bounds_shim_delegates():
    block = _fn_block("_get_year_bounds")
    assert "posting_service._get_year_bounds(" in block


def test_posting_service_has_fiscal_close_functions():
    assert "def _get_year_bounds(" in POSTING_SRC
    assert "def _check_period_continuity(" in POSTING_SRC
    assert "def close_fiscal_period(" in POSTING_SRC
    assert "def perform_year_end_close(" in POSTING_SRC
    assert "def _calculate_account_balance_for_period(" in POSTING_SRC
    assert "def _calculate_account_balance(" in POSTING_SRC
    assert '"PeriodClose"' in POSTING_SRC
    assert 'exclude_refs=["PeriodClose"]' in POSTING_SRC
    assert "allocation_count=len(periods_in_year)" in POSTING_SRC


def test_posting_service_import_purity_ps_p6_4():
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
