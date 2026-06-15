"""BANKING-SERVICE-01 — contract test for the extraction-readiness audit.

Doc-only guard: verifies audit doc exists, maps key modules, pins risks,
safe slices, and do-not-touch rules. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "BANKING_SERVICE_01_AUDIT.md"
)

REQUIRED_SECTIONS = (
    "Current banking architecture map",
    "Existing tests map",
    "Risk list",
    "Safe extraction slices",
    "Tests to add before each slice",
    "FastAPI impact",
    "PostgreSQL impact",
    "Do-not-touch list",
)

REQUIRED_MODULES = (
    "services/write_banking.py",
    "services/write_reconciliation.py",
    "services/read_reconciliation.py",
    "match_post.py",
    "company_card.py",
    "ui/banking.py",
)

REQUIRED_RISKS = (
    "BS-AUDIT-01",
    "BS-AUDIT-02",
    "BS-AUDIT-03",
    "TD-PS-08",
)

REQUIRED_SLICES = (
    "BS-01",
    "BS-02",
    "BS-03",
    "BS-04",
)

DO_NOT_TOUCH_ITEMS = (
    "apply_account_balance_delta",
    "void_bank_transaction",
    "_finalize_row",
    "post_credit_card_bill_payment",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_audit_doc_has_required_sections(doc_text: str):
    for heading in REQUIRED_SECTIONS:
        assert heading in doc_text, f"missing section: {heading}"


def test_audit_doc_maps_service_modules(doc_text: str):
    for mod in REQUIRED_MODULES:
        assert mod in doc_text, f"missing module reference: {mod}"


def test_audit_doc_states_partial_not_complete(doc_text: str):
    lowered = doc_text.lower()
    assert "partial" in lowered
    assert "not ready for monolithic extraction" in lowered or "partial, not" in lowered


def test_audit_doc_lists_app_coupling_risks(doc_text: str):
    for risk in REQUIRED_RISKS:
        assert risk in doc_text, f"missing risk id: {risk}"
    assert "_app()" in doc_text


def test_audit_doc_lists_safe_slices(doc_text: str):
    for slice_id in REQUIRED_SLICES:
        assert slice_id in doc_text, f"missing slice: {slice_id}"


def test_audit_doc_fastapi_flags(doc_text: str):
    assert "ERP_API_WRITE_BANKING" in doc_text
    assert "ERP_API_WRITE_RECONCILIATION" in doc_text


def test_audit_doc_postgres_test_only(doc_text: str):
    assert "SQLite" in doc_text
    assert "MONEY-DECIMAL-01" in doc_text


def test_audit_doc_do_not_touch_list(doc_text: str):
    for item in DO_NOT_TOUCH_ITEMS:
        assert item in doc_text, f"missing do-not-touch item: {item}"


def test_referenced_service_files_exist():
    root = Path(__file__).resolve().parents[1]
    for rel in (
        "services/write_banking.py",
        "services/write_reconciliation.py",
        "services/read_reconciliation.py",
        "reconciliation/match_post.py",
        "reconciliation/company_card.py",
        "ui/banking.py",
    ):
        path = root / rel
        assert path.is_file(), f"referenced module missing on disk: {rel}"


def test_referenced_fastapi_tests_exist():
    root = Path(__file__).resolve().parents[1] / "tests"
    for name in (
        "test_fastapi_p2_banking_write.py",
        "test_fastapi_p2_reconciliation_write.py",
        "test_fastapi_p0_reconciliation_readiness_service.py",
    ):
        assert (root / name).is_file(), f"missing test file: {name}"
