"""P3.4-C — contract tests for the baseline schema equivalence harness.

Verifies create_all vs migrate_schema drift is detected and documented as expected
pre-0001. Does not require Alembic 0001 or touch production DB.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from p3_schema_equivalence_utils import (
    ACCOUNTING_INTEGRITY_UNIQUES,
    COMPOSITE_MIGRATE_ONLY_INDEXES,
    PRE_0001_PHASE,
    assert_known_pre_0001_drift_detected,
    build_create_all_schema_summary,
    build_migrate_evolved_schema_summary,
    compute_schema_drift,
    format_pre_0001_drift_report,
    run_pre_0001_baseline_equivalence,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_4_C_BASELINE_EQUIVALENCE_HARNESS.md"


def test_doc_exists():
    assert DOC_PATH.exists(), f"Harness doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0


def test_doc_covers_required_topics():
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for topic in (
        "purpose",
        "create_all",
        "migrate_schema",
        "0001",
        "known expected drift",
        "acceptance gate",
        "limitations",
        "how to run",
    ):
        assert topic in text, f"Doc missing topic: {topic!r}"


def test_no_alembic_revision_file_exists():
    version_files: list[Path] = []
    for versions_dir in ROOT.glob("**/versions"):
        if versions_dir.is_dir():
            version_files.extend(
                p for p in versions_dir.glob("*.py") if p.name != "__init__.py"
            )
    assert not version_files, f"No Alembic revision files yet, found: {version_files}"


def test_harness_does_not_use_runtime_db_engine():
    """Harness uses isolated in-memory SQLite, not paths.DATABASE_URL."""
    import db
    from paths import DATABASE_URL

    utils_path = Path(__file__).with_name("p3_schema_equivalence_utils.py")
    text = utils_path.read_text(encoding="utf-8")
    assert "from paths import" not in text
    assert "from db import Base" in text

    summary = build_create_all_schema_summary()
    assert summary["tables"]
    assert DATABASE_URL.endswith("erp_data.db")
    assert db.engine.dialect.name == "sqlite"


def test_create_all_summary_has_tables_and_columns():
    summary = build_create_all_schema_summary()
    assert len(summary["tables"]) > 20
    assert "journal_entries" in summary["tables"]
    assert "journal_entries" in summary["columns"]
    assert any(c["name"] == "company_id" for c in summary["columns"]["journal_entries"])


def test_migrate_evolved_summary_has_more_indexes():
    create_all = build_create_all_schema_summary()
    migrated = build_migrate_evolved_schema_summary()
    assert len(migrated["indexes"]) > len(create_all["indexes"])


def test_drift_detects_known_pre_0001_gaps():
    create_all = build_create_all_schema_summary()
    migrated = build_migrate_evolved_schema_summary()
    drift = compute_schema_drift(create_all, migrated)

    assert drift["phase"] == PRE_0001_PHASE
    assert drift["indexes_only_in_migrated"]
    assert not drift["equivalent"]

    for name in ACCOUNTING_INTEGRITY_UNIQUES:
        assert name in drift["indexes_only_in_migrated"]

    for name in COMPOSITE_MIGRATE_ONLY_INDEXES:
        assert name in drift["indexes_only_in_migrated"]

    assert len(drift["company_id_indexes_only_in_migrated"]) >= 10


def test_assert_known_pre_0001_drift_detected_passes():
    result = run_pre_0001_baseline_equivalence()
    assert_known_pre_0001_drift_detected(result["drift"])


def test_report_identifies_expected_pre_0001_drift():
    result = run_pre_0001_baseline_equivalence()
    report = result["report"]
    lowered = report.lower()
    assert "expected" in lowered or "pre-0001" in lowered
    assert "migrate" in lowered or "migrated" in lowered
    assert format_pre_0001_drift_report(result["drift"]) == report


def test_partial_indexes_captured_in_migrated_summary():
    migrated = build_migrate_evolved_schema_summary()
    partial = [
        name
        for name, meta in migrated["indexes"].items()
        if meta.get("partial")
    ]
    assert "uq_yec_year" in partial or "uq_palloc_period" in partial


def test_foreign_keys_extracted():
    summary = build_create_all_schema_summary()
    assert summary["foreign_keys"], "ORM models should declare foreign keys"
