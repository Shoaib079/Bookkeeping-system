"""PostgreSQL build + dual-run parity — Alembic-backed PG schema + report fingerprints.

Test-only slice: PG disposable DBs built via ``alembic upgrade head`` (0002).
SQLite reference path unchanged (in-memory ORM). No production runtime switch.

Cross-ref: docs/POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from p3_dual_run_utils import (
    AMOUNT,
    PARITY_FLOWS,
    dual_engine_parity,
    flow_cash_sale,
    run_parity_flow_sqlite,
)
from postgres_utils import (
    bootstrap_postgres_via_alembic,
    drop_all_pg_objects,
    get_test_postgres_url,
    postgres_alembic_head_revision,
    require_test_postgres_url,
)
from tests.md05_migration_smoke_utils import pg_numeric_column_scale

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md"
POSTING_PATH = ROOT / "services" / "posting.py"


class TestPgBuildDualRunDoc:
    def test_closure_doc_exists(self):
        assert DOC_PATH.exists()
        text = DOC_PATH.read_text(encoding="utf-8").lower()
        assert "alembic upgrade head" in text
        assert "erp_test_postgres_url" in text
        assert "no production runtime switch" in text or "production remains" in text


class TestDualRunReportFingerprints:
    def test_sqlite_cash_sale_summary_includes_reports(self):
        summary = run_parity_flow_sqlite(
            flow_cash_sale,
            tables=PARITY_FLOWS[0].tables,
        )
        reports = summary["reports"]
        assert reports["pl_net"] == AMOUNT
        assert reports["bs_balanced"] is True
        assert reports["bs_total_assets"] > 0


class TestPostgresAlembicBuildPath:
    @pytest.mark.optional_postgres
    def test_bootstrap_builds_revision_0002(self):
        if get_test_postgres_url() is None:
            pytest.skip("ERP_TEST_POSTGRES_URL not set")
        url = require_test_postgres_url()
        engine = bootstrap_postgres_via_alembic(url)
        try:
            assert postgres_alembic_head_revision(engine) == "0002"
            prec, scale = pg_numeric_column_scale(engine, "journal_entry_lines", "debit")
            assert prec == 19 and scale == 2
        finally:
            drop_all_pg_objects(engine)
            engine.dispose()

    @pytest.mark.optional_postgres
    @pytest.mark.parametrize(
        "flow_spec",
        PARITY_FLOWS,
        ids=[spec.name for spec in PARITY_FLOWS],
    )
    def test_alembic_pg_matches_sqlite_with_reports(self, flow_spec):
        if get_test_postgres_url() is None:
            pytest.skip("ERP_TEST_POSTGRES_URL not set")
        sqlite_summary, postgres_summary = dual_engine_parity(
            flow_spec.runner,
            tables=flow_spec.tables,
        )
        assert postgres_summary is not None
        assert sqlite_summary == postgres_summary
        assert "reports" in sqlite_summary
        assert sqlite_summary["reports"]["bs_balanced"] is True


class TestHarnessSourceContracts:
    def test_dual_run_postgres_uses_alembic_bootstrap(self):
        src = (ROOT / "tests" / "p3_dual_run_utils.py").read_text(encoding="utf-8")
        assert "bootstrap_postgres_via_alembic" in src
        assert "create_test_schema(engine)" not in src.split("isolated_postgres_session")[1]

    def test_postgres_utils_exports_bootstrap(self):
        src = (ROOT / "tests" / "postgres_utils.py").read_text(encoding="utf-8")
        assert "def bootstrap_postgres_via_alembic" in src
        assert "run_upgrade_head" in src
