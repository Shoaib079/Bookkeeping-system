"""P3.8-I — contract tests for backup / confirmation migration gate."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from paths import DATABASE_URL
from services.schema_migration_gate import (
    ACTION_STAMP,
    ACTION_UPGRADE_HEAD,
    ACTION_VERIFY_ONLY,
    REQUIRED_CONFIRMATION_PHRASE,
    evaluate_migration_gate,
    validate_backup_path,
    validate_confirmation_phrase,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_8_I_MIGRATION_GATE.md"
APP_PATH = ROOT / "app.py"
MODULE_PATH = ROOT / "services" / "schema_migration_gate.py"

TEST_DB_URL = "sqlite:///:memory:"


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_doc_covers_required_topics():
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for topic in (
        "validation-only",
        "no backup creation",
        "no alembic",
        "not wired",
        "p3.8-j",
        "migrate_schema",
        "i have backed up this database",
    ):
        assert topic in text, f"Doc missing topic: {topic!r}"


def test_verify_only_allowed():
    decision = evaluate_migration_gate(
        db_path_or_url=TEST_DB_URL,
        action=ACTION_VERIFY_ONLY,
        is_populated=True,
    )
    assert decision.allowed is True
    assert decision.requires_backup is False
    assert decision.requires_confirmation is False


def test_empty_db_upgrade_allowed():
    decision = evaluate_migration_gate(
        db_path_or_url=TEST_DB_URL,
        action=ACTION_UPGRADE_HEAD,
        is_populated=False,
        require_backup=True,
        require_confirmation=True,
    )
    assert decision.allowed is True
    assert decision.requires_backup is False


def test_populated_upgrade_blocked_without_backup():
    decision = evaluate_migration_gate(
        db_path_or_url=TEST_DB_URL,
        action=ACTION_UPGRADE_HEAD,
        is_populated=True,
        require_backup=True,
        require_confirmation=True,
        confirmation_value=REQUIRED_CONFIRMATION_PHRASE,
    )
    assert decision.allowed is False
    assert decision.requires_backup is True
    assert decision.backup_valid is False


def test_populated_upgrade_blocked_without_confirmation(tmp_path):
    backup = tmp_path / "backup.db"
    backup.write_bytes(b"sqlite-backup")
    decision = evaluate_migration_gate(
        db_path_or_url=TEST_DB_URL,
        action=ACTION_UPGRADE_HEAD,
        is_populated=True,
        require_backup=True,
        require_confirmation=True,
        backup_path=backup,
    )
    assert decision.allowed is False
    assert decision.confirmation_valid is False


def test_populated_upgrade_allowed_with_backup_and_confirmation(tmp_path):
    backup = tmp_path / "backup.db"
    backup.write_bytes(b"sqlite-backup")
    decision = evaluate_migration_gate(
        db_path_or_url=TEST_DB_URL,
        action=ACTION_UPGRADE_HEAD,
        is_populated=True,
        require_backup=True,
        require_confirmation=True,
        backup_path=backup,
        confirmation_value=REQUIRED_CONFIRMATION_PHRASE,
    )
    assert decision.allowed is True
    assert decision.backup_valid is True
    assert decision.confirmation_valid is True


def test_legacy_stamp_blocked_without_backup_and_confirmation():
    decision = evaluate_migration_gate(
        db_path_or_url=TEST_DB_URL,
        action=ACTION_STAMP,
        is_populated=True,
    )
    assert decision.allowed is False
    assert decision.requires_backup is True
    assert decision.requires_confirmation is True


def test_invalid_backup_rejected(tmp_path):
    missing = tmp_path / "missing.db"
    status = validate_backup_path(missing)
    assert status.valid is False

    directory = tmp_path / "dir_backup"
    directory.mkdir()
    status_dir = validate_backup_path(directory)
    assert status_dir.valid is False

    empty = tmp_path / "empty.db"
    empty.write_bytes(b"")
    status_empty = validate_backup_path(empty, strict=True)
    assert status_empty.valid is False


def test_confirmation_phrase_exact():
    assert validate_confirmation_phrase(None).valid is False
    assert validate_confirmation_phrase("wrong").valid is False
    assert validate_confirmation_phrase("i have backed up this database").valid is False
    assert validate_confirmation_phrase(REQUIRED_CONFIRMATION_PHRASE).valid is True
    assert validate_confirmation_phrase(f"  {REQUIRED_CONFIRMATION_PHRASE}  ").valid is True


def test_production_database_requires_stricter_gate(tmp_path):
    backup = tmp_path / "backup.db"
    backup.write_bytes(b"ok")
    decision = evaluate_migration_gate(
        db_path_or_url=DATABASE_URL,
        action=ACTION_UPGRADE_HEAD,
        is_populated=False,
        backup_path=backup,
        confirmation_value=REQUIRED_CONFIRMATION_PHRASE,
    )
    assert decision.production_database is True
    assert decision.requires_backup is True
    assert decision.requires_confirmation is True
    assert decision.allowed is True


def test_gate_not_wired_into_app():
    app_text = APP_PATH.read_text(encoding="utf-8")
    for token in (
        "schema_migration_gate",
        "evaluate_migration_gate",
        "MigrationGateDecision",
    ):
        assert token not in app_text


def test_gate_does_not_mutate_files_or_db(tmp_path):
    backup = tmp_path / "backup.db"
    backup.write_bytes(b"before")
    mtime_before = backup.stat().st_mtime
    size_before = backup.stat().st_size

    evaluate_migration_gate(
        db_path_or_url=TEST_DB_URL,
        action=ACTION_UPGRADE_HEAD,
        is_populated=True,
        require_backup=True,
        require_confirmation=True,
        backup_path=backup,
        confirmation_value=REQUIRED_CONFIRMATION_PHRASE,
    )

    assert backup.stat().st_size == size_before
    assert backup.stat().st_mtime == mtime_before


def test_gate_purity_by_source_contract():
    source = inspect.getsource(evaluate_migration_gate).lower()
    for token in (
        "subprocess",
        "alembic",
        "migrate_schema",
        "create_engine",
        "os.environ",
        "shutil",
        "vacuum",
    ):
        assert token not in source, f"gate must not reference {token!r}"
