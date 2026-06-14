"""P3.4-D — contract tests for Alembic baseline revision 0001.

Verifies the authored migration file, source constraints, and ephemeral SQLite
equivalence against migrate_schema-evolved schema. Does not run ``alembic upgrade``
against production ``erp_data.db`` or stamp any database.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from p3_schema_equivalence_utils import (
    ACCOUNTING_INTEGRITY_UNIQUES,
    BASELINE_0001_PATH,
    COMPOSITE_MIGRATE_ONLY_INDEXES,
    POST_0001_PHASE,
    assert_alembic_0001_matches_migrate_schema,
    build_alembic_0001_schema_summary,
    run_post_0001_baseline_equivalence,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_4_D_BASELINE_MIGRATION.md"
PRODUCTION_DB = ROOT / "erp_data.db"


@pytest.fixture(scope="module")
def baseline_source() -> str:
    assert BASELINE_0001_PATH.exists(), f"Missing baseline revision: {BASELINE_0001_PATH}"
    return BASELINE_0001_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Missing doc: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0


def test_doc_covers_required_topics():
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for topic in (
        "0001",
        "authored",
        "not applied",
        "not stamped",
        "migrate_schema",
        "authoritative",
        "acceptance",
        "remaining",
    ):
        assert topic in text, f"Doc missing topic: {topic!r}"


def test_0001_baseline_file_exists():
    assert BASELINE_0001_PATH.name == "0001_baseline.py"
    assert BASELINE_0001_PATH.stat().st_size > 1000


def test_revision_metadata(baseline_source):
    assert 'revision = "0001"' in baseline_source
    assert "down_revision = None" in baseline_source


def test_upgrade_has_no_drop(baseline_source):
    upgrade_body = baseline_source.split("def upgrade")[1].split("def downgrade")[0]
    lowered = upgrade_body.lower()
    assert "drop " not in lowered
    assert "drop_" not in lowered
    assert "drop_table" not in lowered
    assert "drop_index" not in lowered
    assert "drop_column" not in lowered


def test_required_indexes_present_in_source(baseline_source):
    for name in ACCOUNTING_INTEGRITY_UNIQUES:
        assert name in baseline_source, f"missing accounting unique {name!r}"
    for name in COMPOSITE_MIGRATE_ONLY_INDEXES:
        assert name in baseline_source, f"missing composite index {name!r}"
    assert "_company_id" in baseline_source
    assert "COALESCE(branch_location, '')" in baseline_source


def test_pg_safe_is_void_predicate(baseline_source):
    ddl_section = baseline_source.split("_SUPPLEMENTAL_INDEX_SQL")[1].split(
        "def _create_orm_schema"
    )[0]
    assert "is_void IS FALSE" in ddl_section
    assert re.search(r"is_void\s*=\s*0", ddl_section) is None


def test_no_float_to_decimal_conversion(baseline_source):
    lowered = baseline_source.lower()
    assert "numeric(" not in lowered
    assert "decimal(" not in lowered
    assert "alter_column" not in lowered


def test_production_db_not_touched_by_harness():
    """Harness uses in-memory SQLite only; never paths.DATABASE_URL."""
    utils_path = Path(__file__).with_name("p3_schema_equivalence_utils.py")
    text = utils_path.read_text(encoding="utf-8")
    assert "from paths import" not in text
    summary = build_alembic_0001_schema_summary()
    assert summary["tables"]
    assert "journal_entries" in summary["tables"]


def test_alembic_0001_matches_migrate_schema_evolved():
    result = run_post_0001_baseline_equivalence()
    drift = result["drift"]
    assert drift["phase"] == POST_0001_PHASE
    assert_alembic_0001_matches_migrate_schema(drift)


def test_post_0001_report_is_generated():
    result = run_post_0001_baseline_equivalence()
    assert "post-0001" in result["report"].lower()
    assert result["drift"]["equivalent"]
