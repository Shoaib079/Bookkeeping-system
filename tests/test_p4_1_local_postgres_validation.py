"""P4.1 — contract test for the local PostgreSQL validation guide.

Doc-only guard: verifies the operator guide exists, documents ERP_TEST_POSTGRES_URL,
optional_postgres tests, dual-run parity, safety rules, and no runtime switch.
No DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "P4_1_LOCAL_POSTGRES_VALIDATION.md"
)

REQUIRED_SECTIONS = (
    "Prerequisites",
    "Create a disposable test database",
    "Set the test URL",
    "Run optional PostgreSQL tests",
    "Run dual-run parity",
    "Run the full SQLite suite",
    "Safety rules",
    "Success criteria",
    "Troubleshooting",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Validation guide missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Validation guide missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Validation guide is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_doc_references_erp_test_postgres_url(doc_text):
    assert "ERP_TEST_POSTGRES_URL" in doc_text


def test_doc_references_postgresql_psycopg_scheme(doc_text):
    lowered = doc_text.lower()
    assert "postgresql+psycopg" in lowered
    assert "pip install psycopg" in lowered


def test_doc_references_optional_postgres_marker(doc_text):
    assert "optional_postgres" in doc_text
    assert "pytest -m optional_postgres" in doc_text


def test_doc_states_database_url_unchanged(doc_text):
    lowered = doc_text.lower()
    assert "database_url" in lowered
    assert "unchanged" in lowered


def test_doc_never_use_production(doc_text):
    lowered = doc_text.lower()
    assert "never use" in lowered and "production" in lowered
    assert "do not" in lowered or "never" in lowered


def test_doc_references_dual_run_parity(doc_text):
    lowered = doc_text.lower()
    assert "dual-run parity" in lowered or "dual run parity" in lowered
    assert "test_p3_2_dual_run_parity.py" in doc_text


def test_doc_no_runtime_switch(doc_text):
    lowered = doc_text.lower()
    assert "no runtime switch" in lowered
    assert "sqlite" in lowered and "runtime" in lowered


def test_doc_full_sqlite_suite_separate(doc_text):
    lowered = doc_text.lower()
    assert "unset erp_test_postgres_url" in lowered or "full sqlite suite" in lowered
    assert "pytest" in lowered
