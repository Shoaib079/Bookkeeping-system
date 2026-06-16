"""POSTGRES-CUTOVER-PREP — runtime cutover prep audit + test-only data migration harness.

Characterization slice: SQLite→PG copy on disposable test DBs + money snapshot verify.
No production ``DATABASE_URL`` switch; ``erp_data.db`` never touched.

Cross-ref: docs/POSTGRES_RUNTIME_CUTOVER_PREP.md
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

import app  # noqa: F401 — bootstrap import graph before posting/reconciliation

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

from postgres_utils import get_test_postgres_url, require_test_postgres_url
from tests.pg_sqlite_data_migration_utils import (
    build_seeded_sqlite_at_head,
    migrate_smoke_sqlite_to_postgres,
    validate_sqlite_test_url,
)
from tests.md05_migration_smoke_utils import (
    capture_money_snapshot,
    session_for_url,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "POSTGRES_RUNTIME_CUTOVER_PREP.md"
GATE_MODULE = ROOT / "services" / "postgres_runtime_cutover.py"


class TestCutoverPrepDoc:
    def test_prep_doc_exists(self):
        assert DOC_PATH.exists()
        text = DOC_PATH.read_text(encoding="utf-8").lower()
        assert "prep" in text
        assert "not ready" in text or "blocked" in text
        assert "erp_test_postgres_url" in text
        assert "no production runtime switch" in text or "production remains" in text


class TestSqliteUrlSafety:
    @pytest.mark.parametrize(
        "url",
        [
            "sqlite:///tmp/test_copy.db",
            "sqlite:////var/folders/abc/md05_smoke.db",
        ],
    )
    def test_disposable_sqlite_allowed(self, url: str):
        assert validate_sqlite_test_url(url).startswith("sqlite:")

    @pytest.mark.parametrize(
        "url",
        [
            "sqlite:///erp_data.db",
            "sqlite:///:memory:",
            "postgresql://localhost/erp_pytest",
        ],
    )
    def test_unsafe_urls_rejected(self, url: str):
        with pytest.raises(ValueError):
            validate_sqlite_test_url(url)


class TestSeededSqliteBuild:
    def test_build_seeded_sqlite_at_head_produces_money(self, tmp_path):
        db_path = tmp_path / "prep_source.db"
        sqlite_url = build_seeded_sqlite_at_head(db_path)
        with session_for_url(sqlite_url) as session:
            snap = capture_money_snapshot(session)
        assert snap.total_debit > 0
        assert snap.cash_balance > 0
        assert snap.pl_net > 0


@pytest.mark.optional_postgres
class TestSqliteToPostgresDataMigration:
    def test_smoke_copy_preserves_money_snapshot(self, tmp_path):
        if get_test_postgres_url() is None:
            pytest.skip("ERP_TEST_POSTGRES_URL not set")
        pg_url = require_test_postgres_url()
        db_path = tmp_path / "prep_migrate.db"
        counts, before, after = migrate_smoke_sqlite_to_postgres(
            sqlite_path=db_path,
            pg_url=pg_url,
        )
        assert counts.get("companies", 0) >= 1
        assert counts.get("journal_entries", 0) >= 1
        assert before == after
        assert before["total_debit"] == before["total_credit"]


class TestRuntimeCutoverGateModule:
    def test_gate_module_exists_and_defaults_off(self):
        assert GATE_MODULE.exists()
        src = GATE_MODULE.read_text(encoding="utf-8")
        assert "ERP_POSTGRES_RUNTIME_CUTOVER" in src
        assert "default off" in src.lower() or "defaults off" in src.lower()
        assert "paths.DATABASE_URL" not in src or "does not mutate" in src.lower()
