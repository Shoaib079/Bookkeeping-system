"""POSTING-SERVICE-01 PS-P6-2 — worker movement extraction proof."""

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


def test_post_worker_movement_shim_delegates():
    block = _fn_block("post_worker_movement")
    assert "posting_service.post_worker_movement(" in block
    assert "company_id=current_company_required()" in block
    assert 'if err == "":' in block
    assert 'log_audit(' in block
    assert '"WorkerMovement"' in block
    for leftover in (
        "WorkerSalary",
        "WorkerAdvance",
        "BankTransaction(",
        "session.commit()",
        "yec_block_message(",
        "create_journal_entry(",
        "get_worker_advance_balance",
    ):
        assert leftover not in block


def test_void_worker_movement_shim_delegates():
    block = _fn_block("void_worker_movement")
    assert "posting_service.void_worker_movement(" in block
    assert "company_id=current_company_required()" in block
    assert 'if err == "":' in block
    assert 'log_audit(' in block
    assert '"WorkerMovement"' in block
    for leftover in (
        "create_reversing_journal_entry",
        "session.commit()",
        "yec_block_message(",
        "btxn.is_void",
        "movement.is_void",
    ):
        assert leftover not in block


def test_posting_service_has_worker_movement_functions():
    assert "def post_worker_movement(" in POSTING_SRC
    assert "def void_worker_movement(" in POSTING_SRC
    assert '"WorkerSalary"' in POSTING_SRC
    assert '"WorkerAdvance"' in POSTING_SRC
    assert '"WorkerRepayment"' in POSTING_SRC
    assert "yec_block_message(" in POSTING_SRC


def test_posting_service_import_purity_ps_p6_2():
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
