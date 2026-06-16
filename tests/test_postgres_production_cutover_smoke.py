"""POSTGRES production cutover smoke — sale/expense/purchase/void/banking/reports on PG."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock(session_state={})

import app  # noqa: F401

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

from p3_dual_run_utils import (
    PARITY_FLOWS,
    dual_engine_parity,
    run_parity_flow_sqlite,
)
from postgres_utils import get_test_postgres_url


class TestPostgresCutoverSmokeDoc:
    def test_smoke_marker_documented(self):
        doc = (
            __import__("pathlib").Path(__file__).resolve().parents[1]
            / "docs"
            / "POSTGRES_PRODUCTION_CUTOVER.md"
        )
        text = doc.read_text(encoding="utf-8").lower()
        assert "smoke" in text
        assert "sale" in text
        assert "void" in text


class TestPostgresCutoverSmokeFlows:
    @pytest.mark.parametrize("flow_spec", PARITY_FLOWS, ids=[s.name for s in PARITY_FLOWS])
    def test_sqlite_reference_flow(self, flow_spec):
        summary = run_parity_flow_sqlite(flow_spec.runner, tables=flow_spec.tables)
        assert summary["journal"]["balanced"] is True
        assert summary["reports"]["bs_balanced"] is True

    @pytest.mark.optional_postgres
    @pytest.mark.parametrize("flow_spec", PARITY_FLOWS, ids=[s.name for s in PARITY_FLOWS])
    def test_pg_matches_sqlite_after_alembic_build(self, flow_spec):
        if get_test_postgres_url() is None:
            pytest.skip("ERP_TEST_POSTGRES_URL not set")
        sqlite_summary, pg_summary = dual_engine_parity(
            flow_spec.runner,
            tables=flow_spec.tables,
        )
        assert pg_summary is not None
        assert sqlite_summary == pg_summary
