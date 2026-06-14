"""P3.8-E — contract tests for pure schema startup decision function."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from services.schema_startup import (
    ACTION_ALEMBIC_UPGRADE_HEAD,
    ACTION_FAIL_CLOSED,
    ACTION_REQUIRE_STAMP,
    ACTION_RUN_MIGRATE_SCHEMA,
    ACTION_VERIFY_ONLY,
    SchemaStartupDecision,
    decide_schema_startup_action,
)
from services.schema_version import (
    STATUS_AHEAD_OF_CODE,
    STATUS_AT_HEAD,
    STATUS_BEHIND_HEAD,
    STATUS_UNKNOWN,
    STATUS_UNSTAMPED,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_8_E_STARTUP_DECISION_FUNCTION.md"
APP_PATH = ROOT / "app.py"


def _decide(**overrides) -> SchemaStartupDecision:
    base = {
        "flag_authoritative": False,
        "schema_status": STATUS_UNSTAMPED,
        "is_new_db": False,
        "dialect": "sqlite",
        "backup_available": False,
        "confirmation_given": False,
        "db_revision": None,
        "head_revision": "0001",
    }
    base.update(overrides)
    return decide_schema_startup_action(**base)


@pytest.mark.parametrize(
    "schema_status",
    [
        STATUS_UNSTAMPED,
        STATUS_AT_HEAD,
        STATUS_BEHIND_HEAD,
        STATUS_AHEAD_OF_CODE,
        STATUS_UNKNOWN,
        "unstamped_legacy",
    ],
)
def test_flag_off_always_run_migrate_schema(schema_status):
    decision = _decide(flag_authoritative=False, schema_status=schema_status)
    assert decision.action == ACTION_RUN_MIGRATE_SCHEMA
    assert decision.blocks_startup is False
    assert decision.requires_backup is False
    assert decision.requires_confirmation is False
    assert "migrate_schema" in decision.message.lower()


def test_flag_off_sqlite_run_migrate_schema():
    decision = _decide(flag_authoritative=False, dialect="sqlite", schema_status=STATUS_AT_HEAD)
    assert decision.action == ACTION_RUN_MIGRATE_SCHEMA


def test_flag_on_new_db_alembic_upgrade_head():
    decision = _decide(flag_authoritative=True, is_new_db=True, schema_status=STATUS_UNSTAMPED)
    assert decision.action == ACTION_ALEMBIC_UPGRADE_HEAD
    assert decision.blocks_startup is False
    assert decision.requires_backup is False
    assert decision.requires_confirmation is False
    assert "upgrade head" in decision.message.lower()
    assert "0001" in decision.message


def test_flag_on_at_head_verify_only():
    decision = _decide(
        flag_authoritative=True,
        schema_status=STATUS_AT_HEAD,
        db_revision="0001",
    )
    assert decision.action == ACTION_VERIFY_ONLY
    assert decision.blocks_startup is False
    assert "head" in decision.message.lower()
    assert "0001" in decision.message


@pytest.mark.parametrize("status", [STATUS_UNSTAMPED, "unstamped_legacy"])
def test_flag_on_unstamped_require_stamp_blocks_without_preconditions(status):
    decision = _decide(flag_authoritative=True, schema_status=status)
    assert decision.action == ACTION_REQUIRE_STAMP
    assert decision.blocks_startup is True
    assert decision.requires_backup is True
    assert decision.requires_confirmation is True
    assert "stamp" in decision.message.lower()


def test_flag_on_unstamped_require_stamp_unblocks_with_preconditions():
    decision = _decide(
        flag_authoritative=True,
        schema_status=STATUS_UNSTAMPED,
        backup_available=True,
        confirmation_given=True,
    )
    assert decision.action == ACTION_REQUIRE_STAMP
    assert decision.blocks_startup is False


def test_flag_on_behind_head_upgrade_blocks_without_preconditions():
    decision = _decide(
        flag_authoritative=True,
        schema_status=STATUS_BEHIND_HEAD,
        db_revision="0001",
        head_revision="0002",
    )
    assert decision.action == ACTION_ALEMBIC_UPGRADE_HEAD
    assert decision.blocks_startup is True
    assert decision.requires_backup is True
    assert decision.requires_confirmation is True
    assert "behind" in decision.message.lower()


def test_flag_on_behind_head_upgrade_unblocks_with_preconditions():
    decision = _decide(
        flag_authoritative=True,
        schema_status=STATUS_BEHIND_HEAD,
        db_revision="0001",
        head_revision="0002",
        backup_available=True,
        confirmation_given=True,
    )
    assert decision.action == ACTION_ALEMBIC_UPGRADE_HEAD
    assert decision.blocks_startup is False


def test_flag_on_ahead_of_code_fail_closed():
    decision = _decide(
        flag_authoritative=True,
        schema_status=STATUS_AHEAD_OF_CODE,
        db_revision="0002",
        head_revision="0001",
    )
    assert decision.action == ACTION_FAIL_CLOSED
    assert decision.blocks_startup is True
    assert "blocked" in decision.message.lower()


def test_flag_on_unknown_fail_closed():
    decision = _decide(flag_authoritative=True, schema_status=STATUS_UNKNOWN)
    assert decision.action == ACTION_FAIL_CLOSED
    assert decision.blocks_startup is True


def test_invalid_status_fail_closed():
    decision = _decide(flag_authoritative=True, schema_status="not_a_real_status")
    assert decision.action == ACTION_FAIL_CLOSED
    assert decision.blocks_startup is True


@pytest.mark.parametrize(
    "schema_status",
    [
        STATUS_UNSTAMPED,
        STATUS_AT_HEAD,
        STATUS_BEHIND_HEAD,
        STATUS_AHEAD_OF_CODE,
        STATUS_UNKNOWN,
    ],
)
def test_postgresql_never_run_migrate_schema_when_flag_on(schema_status):
    decision = _decide(
        flag_authoritative=True,
        dialect="postgresql",
        schema_status=schema_status,
    )
    assert decision.action != ACTION_RUN_MIGRATE_SCHEMA


def test_output_fields_populated():
    decision = _decide(
        flag_authoritative=True,
        schema_status=STATUS_AT_HEAD,
        db_revision="0001",
        dialect="sqlite",
    )
    assert decision.schema_status == STATUS_AT_HEAD
    assert decision.db_revision == "0001"
    assert decision.head_revision == "0001"
    assert decision.dialect == "sqlite"
    assert decision.flag_authoritative is True
    assert isinstance(decision.message, str) and decision.message


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_doc_covers_required_topics():
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for topic in (
        "pure decision",
        "not wired",
        "no migration execution",
        "p3.8-f",
        "migrate_schema",
        "run_migrate_schema",
        "verify_only",
        "alembic_upgrade_head",
        "require_stamp",
        "fail_closed",
    ):
        assert topic in text, f"Doc missing topic: {topic!r}"


def test_decision_function_purity_by_source_contract():
    source = inspect.getsource(decide_schema_startup_action).lower()
    banned = (
        "create_engine",
        "alembic.command",
        "detect_schema_version",
        "os.environ",
        "sessionlocal",
        "open(",
        "path(",
        "import migrate_schema",
        "from app import migrate_schema",
    )
    for token in banned:
        assert token not in source, f"decide_schema_startup_action must not reference {token!r}"


def test_not_wired_into_app_startup():
    app_text = APP_PATH.read_text(encoding="utf-8")
    assert "decide_schema_startup_action" not in app_text


def test_new_db_takes_priority_over_unstamped_status():
    decision = _decide(
        flag_authoritative=True,
        is_new_db=True,
        schema_status=STATUS_UNSTAMPED,
    )
    assert decision.action == ACTION_ALEMBIC_UPGRADE_HEAD
