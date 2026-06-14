"""P3.2-D — dual-run parity harness tests (SQLite always; PostgreSQL optional)."""

from __future__ import annotations

from pathlib import Path

import pytest

from p3_dual_run_utils import (
    PARITY_FLOWS,
    dual_engine_parity,
    run_parity_flow_sqlite,
)
from postgres_utils import get_test_postgres_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "P3_2_DUAL_RUN_PARITY_HARNESS.md"


@pytest.mark.parametrize(
    "flow_spec",
    PARITY_FLOWS,
    ids=[spec.name for spec in PARITY_FLOWS],
)
def test_sqlite_parity_flow_produces_balanced_summary(flow_spec):
    summary = run_parity_flow_sqlite(flow_spec.runner, tables=flow_spec.tables)
    assert summary["journal"]["journal_entry_count"] >= 1
    assert summary["journal"]["balanced"] is True
    assert summary["journal"]["debit_total"] > 0
    assert summary["journal"]["credit_total"] > 0
    assert summary["void_counts"]["sales"] == 0
    assert summary["void_counts"]["expenses"] == 0


@pytest.mark.parametrize(
    "flow_spec",
    PARITY_FLOWS,
    ids=[spec.name for spec in PARITY_FLOWS],
)
def test_sqlite_summary_has_expected_table_counts(flow_spec):
    summary = run_parity_flow_sqlite(flow_spec.runner, tables=flow_spec.tables)
    counts = summary["counts"]
    assert counts["journal_entries"] >= 1
    assert counts["journal_entry_lines"] >= 2
    assert counts.get("chart_of_accounts", 0) > 0


@pytest.mark.optional_postgres
@pytest.mark.parametrize(
    "flow_spec",
    PARITY_FLOWS,
    ids=[spec.name for spec in PARITY_FLOWS],
)
def test_sqlite_postgres_parity_matches(flow_spec):
    if get_test_postgres_url() is None:
        pytest.skip("ERP_TEST_POSTGRES_URL not set")
    sqlite_summary, postgres_summary = dual_engine_parity(
        flow_spec.runner,
        tables=flow_spec.tables,
    )
    assert postgres_summary is not None
    assert sqlite_summary == postgres_summary


def test_harness_module_imports_without_db_connection():
    import importlib

    import p3_dual_run_utils

    reloaded = importlib.reload(p3_dual_run_utils)
    assert len(reloaded.PARITY_FLOWS) >= 5


def test_docs_exist_and_cover_topics():
    assert DOC_PATH.exists()
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for topic in (
        "purpose",
        "erp_test_postgres_url",
        "sqlite-only",
        "limitation",
        "p3.3",
        "alembic",
    ):
        assert topic in text, f"Doc missing topic: {topic!r}"
