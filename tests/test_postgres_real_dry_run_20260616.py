"""POSTGRES real dry run 2026-06-16 — doc contract (operator-verified; docs only)."""

from __future__ import annotations

from pathlib import Path

import pytest

DOC = Path(__file__).resolve().parents[1] / "docs" / "POSTGRES_REAL_DRY_RUN_20260616.md"


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC.exists(), f"Missing dry run doc: {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_dry_run_doc_exists():
    assert DOC.stat().st_size > 400


def test_records_copy_path_and_masked_url(doc_text: str):
    assert "erp_data_pg_dry_run_source_20260616_201308.db" in doc_text
    assert "postgresql+psycopg://***@localhost:5432/erp_pytest" in doc_text


def test_records_clean_parity_results(doc_text: str):
    low = doc_text.lower()
    assert "row_count_mismatches" in low
    assert "trial_balance_mismatches" in low
    assert "report_mismatches" in low
    assert "production_erp_data_touched" in low
    assert "false" in low
    assert "companies" in low
    for cid in ("1", "2", "3", "4"):
        assert cid in doc_text


def test_production_cutover_still_blocked(doc_text: str):
    low = doc_text.lower()
    assert "blocked" in low or "not approved" in low
    assert "database_url" in low
    assert "unchanged" in low or "remains sqlite" in low


def test_safe_for_cutover_is_data_parity_only(doc_text: str):
    low = doc_text.lower()
    assert "safe_for_production_cutover" in low
    assert "not an approval" in low or "does not approve" in low
