"""P2-HARDEN-01 — closure doc contract (verification-only slice)."""

from __future__ import annotations

from pathlib import Path

import pytest

CLOSURE_DOC = Path(__file__).resolve().parents[1] / "docs" / "P2_HARDEN_01_AUDIT_CLOSURE.md"
GET_DB_SRC = Path(__file__).resolve().parents[1] / "api" / "dependencies.py"


@pytest.fixture(scope="module")
def closure_text() -> str:
    assert CLOSURE_DOC.exists(), f"Missing closure doc: {CLOSURE_DOC}"
    return CLOSURE_DOC.read_text(encoding="utf-8")


def test_closure_doc_exists():
    assert CLOSURE_DOC.stat().st_size > 500


def test_closure_documents_h01_h02_complete(closure_text: str):
    low = closure_text.lower()
    assert "h-01" in low and "complete" in low
    assert "h-02" in low and "complete" in low


def test_closure_documents_h03_deferred_rejects_autostamp(closure_text: str):
    low = closure_text.lower()
    assert "h-03" in low
    assert "defer" in low
    assert "auto-stamp" in low or "autostamp" in low
    assert "reject" in low or "rejected" in low


def test_closure_explicit_stamping_is_standard(closure_text: str):
    low = closure_text.lower()
    assert "explicit" in low
    assert "before_flush" in low
    assert "no silent" in low or "reject" in low


def test_get_db_has_no_before_flush_listener():
    src = GET_DB_SRC.read_text(encoding="utf-8")
    assert "before_flush" not in src
    assert "def get_db" in src
