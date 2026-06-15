"""FULL-SERVICE-READINESS-AUDIT — doc contract test.

Verifies the full-repo service readiness audit exists and pins key status claims.
Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC = Path(__file__).resolve().parents[1] / "docs" / "FULL_SERVICE_READINESS_AUDIT.md"

REQUIRED_SECTIONS = (
    "Full status table",
    "Service inventory",
    "`app.py` dependency map",
    "Test coverage map",
    "Contradictory docs",
    "Recommended next 5 actions",
    "Do-not-touch list",
)

STATUS_CLAIMS = (
    ("POSTING-SERVICE-01", "Complete"),
    ("REPORTS-SERVICE-01", "Partial"),
    ("BANKING-SERVICE-01", "Partial"),
    ("AUTH-SESSION-02", "Partial"),
    ("FastAPI foundation", "Partial"),
    ("PostgreSQL", "Partial"),
    ("React", "Not started"),
)

CORE_SERVICES = (
    "services/posting.py",
    "services/read_reports.py",
    "services/write_banking.py",
    "services/write_reconciliation.py",
    "services/session_policy.py",
    "services/receipt_learning.py",
)

PYTEST_BASELINE = "3925 passed"


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC.exists(), f"Audit doc missing: {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_audit_doc_exists():
    assert DOC.exists()
    assert DOC.stat().st_size > 0


def test_audit_doc_sections(doc_text: str):
    for section in REQUIRED_SECTIONS:
        assert section in doc_text, f"missing section: {section}"


def test_audit_doc_status_table(doc_text: str):
    for _label, status in STATUS_CLAIMS:
        assert status in doc_text


def test_audit_doc_posting_complete(doc_text: str):
    assert "POSTING-SERVICE-01" in doc_text
    assert "services/posting.py" in doc_text
    assert "PS-P7" in doc_text


def test_audit_doc_banking_app_coupling(doc_text: str):
    assert "_app()" in doc_text
    assert "apply_account_balance_delta" in doc_text


def test_audit_doc_auth_idle_not_wired(doc_text: str):
    assert "should_extend_idle" in doc_text
    assert "Not started" in doc_text or "not wired" in doc_text.lower()


def test_audit_doc_fastapi_partial(doc_text: str):
    assert "ERP_API_WRITE_" in doc_text
    assert "Partial" in doc_text


def test_audit_doc_postgres_sqlite_runtime(doc_text: str):
    assert "SQLite" in doc_text
    assert "ERP_ALEMBIC_AUTHORITATIVE" in doc_text


def test_audit_doc_react_not_started(doc_text: str):
    assert "ERP_DS_05" in doc_text
    assert "Not started" in doc_text


def test_audit_doc_pytest_baseline(doc_text: str):
    assert PYTEST_BASELINE in doc_text


def test_core_service_files_exist():
    root = Path(__file__).resolve().parents[1]
    for rel in CORE_SERVICES:
        assert (root / rel).is_file(), f"missing: {rel}"


def test_fastapi_test_suite_exists():
    root = Path(__file__).resolve().parents[1] / "tests"
    matches = list(root.glob("test_fastapi_*.py"))
    assert len(matches) >= 30, f"expected 30+ fastapi tests, got {len(matches)}"


def test_posting_characterization_suite_exists():
    root = Path(__file__).resolve().parents[1] / "tests"
    matches = list(root.glob("test_posting_service01_*.py"))
    assert len(matches) >= 30, f"expected 30+ posting char tests, got {len(matches)}"
