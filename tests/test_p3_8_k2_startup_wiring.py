"""P3.8-K2 — contract tests for flag-gated startup wiring."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from db import Base
from services.alembic_runner import AlembicCommandResult
from services.schema_startup import (
    ACTION_ALEMBIC_UPGRADE_HEAD,
    ACTION_FAIL_CLOSED,
    ACTION_REQUIRE_STAMP,
    ALEMBIC_AUTHORITATIVE_ENV_VAR,
)
from services.schema_startup_wiring import (
    SchemaStartupError,
    prepare_schema_startup_authoritative,
    reset_schema_startup_plan,
    run_schema_startup_in_session,
)
from services.schema_version import ALEMBIC_VERSION_TABLE

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_8_K2_STARTUP_WIRING.md"
APP_PATH = ROOT / "app.py"

FLAG_OFF = {ALEMBIC_AUTHORITATIVE_ENV_VAR: "0"}


def _make_memory_engine() -> Engine:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
        if engine.dialect.name != "sqlite":
            return
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


def _create_alembic_version_table(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE TABLE {ALEMBIC_VERSION_TABLE} "
                "(version_num VARCHAR(32) NOT NULL)"
            )
        )


def _stamp(engine: Engine, revision: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(f"INSERT INTO {ALEMBIC_VERSION_TABLE} (version_num) VALUES (:rev)"),
            {"rev": revision},
        )


@pytest.fixture(autouse=True)
def _clear_startup_plan():
    reset_schema_startup_plan()
    yield
    reset_schema_startup_plan()


@pytest.fixture
def populated_db(tmp_path):
    import models  # noqa: F401

    db_path = tmp_path / "populated.db"
    database_url = f"sqlite:///{db_path}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield database_url, engine
    engine.dispose()


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_doc_covers_required_topics():
    text_doc = DOC_PATH.read_text(encoding="utf-8").lower()
    for topic in (
        "flag off",
        "flag on",
        "migrate_schema",
        "rollback",
        "blocked",
        "p3.8-k2",
    ):
        assert topic in text_doc, f"Doc missing topic: {topic!r}"


def test_flag_off_calls_migrate_schema_then_diagnostic_same_order():
    migrate_calls: list[str] = []
    log_calls: list[str] = []
    order: list[str] = []

    def migrate_schema(session) -> None:
        migrate_calls.append("migrate")
        order.append("migrate")

    def log_diag(session) -> None:
        log_calls.append("log")
        order.append("log")

    engine = _make_memory_engine()
    SessionLocal = sessionmaker(bind=engine)
    try:
        prepare_schema_startup_authoritative(
            database_url=str(engine.url),
            environ=FLAG_OFF,
        )
        with SessionLocal() as session:
            run_schema_startup_in_session(
                session,
                migrate_schema_fn=migrate_schema,
                log_diagnostics_fn=log_diag,
                environ=FLAG_OFF,
            )
    finally:
        engine.dispose()

    assert migrate_calls == ["migrate"]
    assert log_calls == ["log"]
    assert order == ["migrate", "log"]


def test_flag_off_does_not_call_alembic_runner():
    runner = MagicMock()
    engine = _make_memory_engine()
    try:
        prepare_schema_startup_authoritative(
            database_url=str(engine.url),
            environ=FLAG_OFF,
            run_upgrade_head_fn=runner,
        )
    finally:
        engine.dispose()
    runner.assert_not_called()


def test_flag_on_at_head_skips_migrate_schema(populated_db):
    database_url, engine = populated_db
    _create_alembic_version_table(engine)
    _stamp(engine, "0001")

    migrate_called = False

    def migrate_schema(session) -> None:
        nonlocal migrate_called
        migrate_called = True

    prepare_schema_startup_authoritative(
        database_url=database_url,
        environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
        run_upgrade_head_fn=MagicMock(),
    )
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        run_schema_startup_in_session(
            session,
            migrate_schema_fn=migrate_schema,
            log_diagnostics_fn=lambda _s: None,
            environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
        )

    assert migrate_called is False


def test_flag_on_at_head_continues_startup(populated_db):
    database_url, _engine = populated_db
    _create_alembic_version_table(_engine)
    _stamp(_engine, "0001")

    plan = prepare_schema_startup_authoritative(
        database_url=database_url,
        environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
        run_upgrade_head_fn=MagicMock(),
    )
    assert plan.schema_step_succeeded is True
    assert plan.skip_migrate_schema is True


def test_flag_on_new_empty_uses_runner_via_gate(tmp_path):
    db_path = tmp_path / "erp_data.db"
    database_url = f"sqlite:///{db_path}"
    runner = MagicMock(
        return_value=AlembicCommandResult(
            command="upgrade",
            target="head",
            success=True,
            message="ok",
            dry_run=False,
            executed=True,
            argv=("python", "-m", "alembic", "upgrade", "head"),
        )
    )

    plan = prepare_schema_startup_authoritative(
        database_url=database_url,
        environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
        run_upgrade_head_fn=runner,
    )
    assert plan.skip_migrate_schema is True
    runner.assert_called_once()
    _args, kwargs = runner.call_args
    assert kwargs["allow_execute"] is True
    assert kwargs["allow_production"] is True


def test_new_empty_runner_failure_blocks_startup(tmp_path):
    db_path = tmp_path / "fresh.db"
    database_url = f"sqlite:///{db_path}"
    runner = MagicMock(
        return_value=AlembicCommandResult(
            command="upgrade",
            target="head",
            success=False,
            message="upgrade failed",
            dry_run=False,
            executed=True,
            argv=("python", "-m", "alembic", "upgrade", "head"),
        )
    )

    with pytest.raises(SchemaStartupError) as excinfo:
        prepare_schema_startup_authoritative(
            database_url=database_url,
            environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
            run_upgrade_head_fn=runner,
        )
    assert excinfo.value.action == ACTION_ALEMBIC_UPGRADE_HEAD


def test_unstamped_legacy_blocks_and_does_not_call_migrate_schema(populated_db):
    database_url, _engine = populated_db
    migrate_called = False

    def migrate_schema(session) -> None:
        nonlocal migrate_called
        migrate_called = True

    with pytest.raises(SchemaStartupError) as excinfo:
        prepare_schema_startup_authoritative(
            database_url=database_url,
            environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
            run_upgrade_head_fn=MagicMock(),
        )
    assert excinfo.value.action == ACTION_REQUIRE_STAMP
    assert migrate_called is False


def test_ahead_blocks_and_does_not_call_migrate_schema(populated_db):
    database_url, engine = populated_db
    _create_alembic_version_table(engine)
    _stamp(engine, "0002")
    migrate_called = False

    def migrate_schema(session) -> None:
        nonlocal migrate_called
        migrate_called = True

    with pytest.raises(SchemaStartupError) as excinfo:
        prepare_schema_startup_authoritative(
            database_url=database_url,
            environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
            run_upgrade_head_fn=MagicMock(),
        )
    assert excinfo.value.action == ACTION_FAIL_CLOSED
    assert migrate_called is False


def test_unknown_blocks_and_does_not_call_migrate_schema(populated_db):
    database_url, engine = populated_db
    _create_alembic_version_table(engine)
    _stamp(engine, "not-a-real-revision")
    with pytest.raises(SchemaStartupError) as excinfo:
        prepare_schema_startup_authoritative(
            database_url=database_url,
            environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
            run_upgrade_head_fn=MagicMock(),
        )
    assert excinfo.value.action == ACTION_FAIL_CLOSED


def test_seeds_only_after_successful_schema_step(tmp_path):
    import models  # noqa: F401

    ok_path = tmp_path / "at_head.db"
    ok_url = f"sqlite:///{ok_path}"
    ok_engine = create_engine(
        ok_url,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(ok_engine)
    _create_alembic_version_table(ok_engine)
    _stamp(ok_engine, "0001")
    ok_engine.dispose()

    plan = prepare_schema_startup_authoritative(
        database_url=ok_url,
        environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
        run_upgrade_head_fn=MagicMock(),
    )
    assert plan.schema_step_succeeded is True

    reset_schema_startup_plan()
    legacy_path = tmp_path / "legacy.db"
    legacy_url = f"sqlite:///{legacy_path}"
    legacy_engine = create_engine(
        legacy_url,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(legacy_engine)
    legacy_engine.dispose()

    with pytest.raises(SchemaStartupError):
        prepare_schema_startup_authoritative(
            database_url=legacy_url,
            environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
            run_upgrade_head_fn=MagicMock(),
        )


def test_no_raw_alembic_commands_in_app():
    app_text = APP_PATH.read_text(encoding="utf-8").lower()
    assert "alembic upgrade" not in app_text
    assert "alembic stamp" not in app_text
    assert "alembic.command" not in app_text
    assert "subprocess.run" not in app_text
    assert "import subprocess" not in app_text


def test_app_uses_dispatcher_not_inline_branching():
    app_text = APP_PATH.read_text(encoding="utf-8")
    assert "_run_schema_startup(_boot_session)" in app_text
    assert "prepare_schema_startup_authoritative()" in app_text
    assert "decide_schema_startup_action" not in app_text
    assert "run_upgrade_head(" not in app_text


def test_production_runner_not_authorized_when_gate_blocks(tmp_path):
    db_path = tmp_path / "erp_data.db"
    database_url = f"sqlite:///{db_path}"
    runner = MagicMock()

    import services.schema_startup_wiring as wiring

    original_evaluate = wiring.evaluate_migration_gate

    def blocked_gate(**kwargs):
        from services.schema_migration_gate import MigrationGateDecision

        return MigrationGateDecision(
            allowed=False,
            message="blocked for test",
            requires_backup=True,
            requires_confirmation=True,
            backup_valid=False,
            confirmation_valid=False,
            action="upgrade_head",
            is_populated=False,
            production_database=True,
        )

    wiring.evaluate_migration_gate = blocked_gate
    try:
        with pytest.raises(SchemaStartupError):
            prepare_schema_startup_authoritative(
                database_url=database_url,
                environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
                run_upgrade_head_fn=runner,
            )
    finally:
        wiring.evaluate_migration_gate = original_evaluate

    runner.assert_not_called()


def test_main_calls_prepare_before_boot_session():
    main_src = inspect.getsource(__import__("app", fromlist=["main"]).main)
    assert main_src.index("prepare_schema_startup_authoritative()") < main_src.index(
        "with get_session() as _boot_session:"
    )


def test_wiring_uses_safe_runner_not_raw_subprocess():
    source = inspect.getsource(prepare_schema_startup_authoritative).lower()
    assert "run_upgrade_head" in source
    assert "subprocess.run" not in source
    assert "import subprocess" not in source
