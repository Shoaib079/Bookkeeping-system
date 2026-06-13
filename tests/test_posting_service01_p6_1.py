"""POSTING-SERVICE-01 PS-P6-1 — partner movement extraction proof."""

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


def test_post_partner_movement_shim_delegates():
    block = _fn_block("post_partner_movement")
    assert "posting_service.post_partner_movement(" in block
    assert "company_id=current_company_required()" in block
    assert 'if err == "":' in block
    assert 'log_audit(' in block
    assert '"PartnerMovement"' in block
    for leftover in (
        "PartnerCapital",
        "PartnerDrawing",
        "BankTransaction(",
        "session.commit()",
        "yec_block_message(",
        "create_journal_entry(",
    ):
        assert leftover not in block


def test_void_partner_movement_shim_delegates():
    block = _fn_block("void_partner_movement")
    assert "posting_service.void_partner_movement(" in block
    assert "company_id=current_company_required()" in block
    assert 'if err == "":' in block
    assert 'log_audit(' in block
    assert '"PartnerMovement"' in block
    for leftover in (
        "create_reversing_journal_entry",
        "session.commit()",
        "yec_block_message(",
        "btxn.is_void",
        "movement.is_void",
    ):
        assert leftover not in block


def test_posting_service_has_partner_movement_functions():
    assert "def post_partner_movement(" in POSTING_SRC
    assert "def void_partner_movement(" in POSTING_SRC
    assert '"PartnerCapital"' in POSTING_SRC
    assert '"PartnerDrawing"' in POSTING_SRC
    assert '"PartnerSalary"' in POSTING_SRC
    assert '"PartnerAdvance"' in POSTING_SRC
    assert '"PartnerAdvanceOffset"' in POSTING_SRC
    assert "yec_block_message(" in POSTING_SRC


def test_posting_service_import_purity_ps_p6_1():
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
