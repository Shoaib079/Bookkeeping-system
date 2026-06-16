"""MONEY-DECIMAL-01 — contract test for Float/money audit doc.

Doc-only guard: verifies audit exists, maps key modules, pins risks,
migration strategy, and do-not-touch rules. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "MONEY_DECIMAL_01_AUDIT.md"

REQUIRED_SECTIONS = (
    "Float inventory",
    "Money field classification",
    "Risk list",
    "Decimal policy recommendation",
    "Migration strategy",
    "Tests to add before implementation",
    "Safe implementation slices",
    "Do-not-touch list",
    "ROADMAP update recommendation",
)

REQUIRED_MODULES = (
    "models.py",
    "services/posting.py",
    "services/banking_balance.py",
    "read_balances.py",
    "read_reports.py",
    "app.py",
)

REQUIRED_RISKS = (
    "MD-01",
    "MD-02",
    "MD-10",
)

REQUIRED_SLICES = (
    "MD-AUDIT-01",
    "MD-02",
    "MD-04",
    "MD-05",
)

DO_NOT_TOUCH_ITEMS = (
    "apply_account_balance_delta",
    "0001_baseline",
    "migrate_schema",
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


def test_audit_doc_maps_core_modules(doc_text: str):
    for mod in REQUIRED_MODULES:
        assert mod in doc_text, f"missing module reference: {mod}"


def test_audit_doc_float_inventory_count(doc_text: str):
    assert "99" in doc_text
    assert "Column(Float" in doc_text or "Float columns" in doc_text


def test_audit_doc_states_no_decimal_in_production_yet(doc_text: str):
    lowered = doc_text.lower()
    assert "zero" in lowered and "decimal" in lowered
    assert "audit only" in lowered


def test_audit_doc_lists_risks(doc_text: str):
    for risk in REQUIRED_RISKS:
        assert risk in doc_text, f"missing risk id: {risk}"


def test_audit_doc_lists_implementation_slices(doc_text: str):
    for slice_id in REQUIRED_SLICES:
        assert slice_id in doc_text, f"missing slice: {slice_id}"


def test_audit_doc_pg_blocker_clarified(doc_text: str):
    assert "PostgreSQL" in doc_text
    assert "MONEY-DECIMAL-01" in doc_text
    assert "P3.1" in doc_text or "P3_1" in doc_text


def test_audit_doc_numeric_precision_recommendation(doc_text: str):
    assert "Numeric(19, 2)" in doc_text or "NUMERIC(19,2)" in doc_text
    assert "0.01" in doc_text


def test_audit_doc_do_not_touch_list(doc_text: str):
    for item in DO_NOT_TOUCH_ITEMS:
        assert item in doc_text, f"missing do-not-touch item: {item}"


def test_models_py_still_uses_float_columns():
    models_src = (
        Path(__file__).resolve().parents[1] / "models.py"
    ).read_text(encoding="utf-8")
    assert "Column(Float" in models_src
    assert "Numeric" not in models_src


def test_posting_kernel_uses_cent_tolerance():
    posting_src = (
        Path(__file__).resolve().parents[1] / "services" / "posting.py"
    ).read_text(encoding="utf-8")
    assert "0.01" in posting_src
    assert "round(" in posting_src
