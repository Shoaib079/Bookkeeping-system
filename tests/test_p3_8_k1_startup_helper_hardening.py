"""P3.8-K1 — startup wiring helper hardening (R1/R2/R3)."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect, text

from db import Base
import models  # noqa: F401
from paths import DATABASE_URL
from services.schema_migration_gate import (
    ACTION_STAMP,
    ACTION_UPGRADE_HEAD,
    MigrationGateDecision,
    evaluate_migration_gate,
)
from services.schema_startup import (
    ACTION_ALEMBIC_UPGRADE_HEAD,
    ACTION_REQUIRE_STAMP,
    ACTION_VERIFY_ONLY,
    SchemaStartupDecision,
    count_application_tables,
    has_alembic_version_table,
    infer_is_new_database,
    is_production_runner_authorized,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_8_K1_STARTUP_HELPER_HARDENING.md"
APP_PATH = ROOT / "app.py"


def _sqlite_engine(tmp_path: Path, name: str = "test.db"):
    db_path = tmp_path / name
    engine = create_engine(f"sqlite:///{db_path}")
    return engine, db_path


def _sample_decision(action: str) -> SchemaStartupDecision:
    return SchemaStartupDecision(
        action=action,
        message="test",
        blocks_startup=False,
        requires_backup=False,
        requires_confirmation=False,
        schema_status="unstamped",
        db_revision=None,
        head_revision="0001_baseline",
        dialect="sqlite",
        flag_authoritative=True,
    )


def _sample_gate(*, allowed: bool) -> MigrationGateDecision:
    return MigrationGateDecision(
        allowed=allowed,
        message="test gate",
        requires_backup=False,
        requires_confirmation=False,
        backup_valid=True,
        confirmation_valid=True,
        action=ACTION_UPGRADE_HEAD,
        is_populated=False,
        production_database=True,
    )


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_empty_db_with_no_app_tables_and_no_alembic_version_is_new(tmp_path):
    engine, _ = _sqlite_engine(tmp_path, "fresh.db")
    try:
        assert has_alembic_version_table(engine) is False
        assert count_application_tables(engine) == 0
        assert infer_is_new_database(engine) is True
    finally:
        engine.dispose()


def test_db_with_alembic_version_is_not_new(tmp_path):
    engine, _ = _sqlite_engine(tmp_path, "stamped.db")
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"
                )
            )
        assert has_alembic_version_table(engine) is True
        assert infer_is_new_database(engine) is False
    finally:
        engine.dispose()


def test_db_with_one_app_table_is_partial_not_new(tmp_path):
    engine, _ = _sqlite_engine(tmp_path, "partial.db")
    try:
        Base.metadata.tables["migration_flags"].create(engine)
        assert count_application_tables(engine) == 1
        assert infer_is_new_database(engine) is False
    finally:
        engine.dispose()


def test_journal_entries_absent_with_other_app_table_is_not_new(tmp_path):
    engine, _ = _sqlite_engine(tmp_path, "partial_no_journal.db")
    try:
        Base.metadata.tables["companies"].create(engine)
        with engine.connect() as connection:
            assert sa_inspect(connection).has_table("companies") is True
            assert sa_inspect(connection).has_table("journal_entries") is False
        assert infer_is_new_database(engine) is False
    finally:
        engine.dispose()


def test_production_authorization_true_only_when_flag_runner_and_gate_allowed():
    decision = _sample_decision(ACTION_ALEMBIC_UPGRADE_HEAD)
    gate = _sample_gate(allowed=True)
    assert is_production_runner_authorized(True, decision, gate) is True

    assert is_production_runner_authorized(False, decision, gate) is False

    verify_decision = _sample_decision(ACTION_VERIFY_ONLY)
    assert is_production_runner_authorized(True, verify_decision, gate) is False

    stamp_decision = _sample_decision(ACTION_REQUIRE_STAMP)
    assert is_production_runner_authorized(True, stamp_decision, gate) is True


def test_production_authorization_false_when_gate_blocks():
    decision = _sample_decision(ACTION_ALEMBIC_UPGRADE_HEAD)
    gate = _sample_gate(allowed=False)
    assert is_production_runner_authorized(True, decision, gate) is False


def test_strict_new_erp_data_db_upgrade_allowed_without_backup(tmp_path):
    erp_path = tmp_path / "erp_data.db"
    decision = evaluate_migration_gate(
        db_path_or_url=f"sqlite:///{erp_path}",
        action=ACTION_UPGRADE_HEAD,
        is_populated=False,
        is_strict_new_empty=True,
    )
    assert decision.production_database is True
    assert decision.allowed is True
    assert decision.requires_backup is False
    assert decision.requires_confirmation is False


def test_populated_erp_data_db_upgrade_blocked_without_backup(tmp_path):
    erp_path = tmp_path / "erp_data.db"
    decision = evaluate_migration_gate(
        db_path_or_url=f"sqlite:///{erp_path}",
        action=ACTION_UPGRADE_HEAD,
        is_populated=True,
    )
    assert decision.production_database is True
    assert decision.allowed is False
    assert decision.requires_backup is True
    assert decision.requires_confirmation is True


def test_stamp_still_requires_backup_and_confirmation_even_for_strict_new(tmp_path):
    erp_path = tmp_path / "erp_data.db"
    decision = evaluate_migration_gate(
        db_path_or_url=f"sqlite:///{erp_path}",
        action=ACTION_STAMP,
        is_populated=False,
        is_strict_new_empty=True,
    )
    assert decision.requires_backup is True
    assert decision.requires_confirmation is True
    assert decision.allowed is False


def test_production_empty_without_strict_new_still_requires_backup():
    decision = evaluate_migration_gate(
        db_path_or_url=DATABASE_URL,
        action=ACTION_UPGRADE_HEAD,
        is_populated=False,
        is_strict_new_empty=False,
    )
    assert decision.production_database is True
    assert decision.requires_backup is True
    assert decision.requires_confirmation is True
    assert decision.allowed is False


def test_helpers_not_wired_into_app():
    app_text = APP_PATH.read_text(encoding="utf-8")
    for token in (
        "is_production_runner_authorized",
        "is_strict_new_empty",
        "count_application_tables",
    ):
        assert token not in app_text


def test_infer_is_new_database_is_read_only_by_source_contract():
    source = inspect.getsource(infer_is_new_database).lower()
    for token in ("subprocess", "alembic upgrade", "migrate_schema", "os.environ"):
        assert token not in source


def test_production_authorization_is_pure_by_source_contract():
    source = inspect.getsource(is_production_runner_authorized).lower()
    for token in (
        "subprocess",
        "create_engine",
        "os.environ",
        "getenv",
        "migrate_schema",
    ):
        assert token not in source
