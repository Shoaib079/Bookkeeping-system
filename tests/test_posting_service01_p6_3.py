"""POSTING-SERVICE-01 PS-P6-3 — profit allocation extraction proof."""

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


def test_allocate_profit_to_partners_shim_delegates():
    block = _fn_block("allocate_profit_to_partners")
    assert "posting_service.allocate_profit_to_partners(" in block
    assert "company_id=current_company_required()" in block
    assert 'if err == "":' in block
    assert 'log_audit(' in block
    assert '"ProfitAllocation"' in block
    assert '"PartnerProfitAllocation"' in block
    for leftover in (
        "PartnerProfitAllocationLine(",
        "session.commit()",
        "yec_block_message(",
        "create_journal_entry(",
        "datetime.date.today()",
        "_get_period_net_income_from_je(",
    ):
        assert leftover not in block


def test_void_profit_allocation_shim_delegates():
    block = _fn_block("void_profit_allocation")
    assert "posting_service.void_profit_allocation(" in block
    assert "company_id=current_company_required()" in block
    assert 'if err == "":' in block
    assert 'log_audit(' in block
    assert '"PartnerProfitAllocation"' in block
    assert "fiscal_period_id" in block
    for leftover in (
        "create_reversing_journal_entry",
        "session.commit()",
        "yec_block_message(",
        "allocation.is_void",
    ):
        assert leftover not in block


def test_allocate_all_pending_shim_delegates():
    block = _fn_block("_allocate_all_pending")
    assert "posting_service._allocate_all_pending(" in block
    assert "company_id=current_company_required()" in block
    assert "allocate_profit_to_partners(" not in block


def test_posting_service_has_profit_allocation_functions():
    assert "def allocate_profit_to_partners(" in POSTING_SRC
    assert "def void_profit_allocation(" in POSTING_SRC
    assert "def _allocate_all_pending(" in POSTING_SRC
    assert "def _get_period_net_income_from_je(" in POSTING_SRC
    assert "def _validate_partner_shares(" in POSTING_SRC
    assert '"ProfitAllocation"' in POSTING_SRC
    assert "datetime.date.today()" in POSTING_SRC
    assert 'mode="allocation_void"' in POSTING_SRC


def test_posting_service_import_purity_ps_p6_3():
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
