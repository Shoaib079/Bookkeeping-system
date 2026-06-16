"""P3.8-F — contract tests for diagnostics-only startup decision wiring."""

from __future__ import annotations

import inspect
import logging
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from db import Base
from services.schema_startup import (
    ACTION_FAIL_CLOSED,
    ACTION_REQUIRE_STAMP,
    ACTION_RUN_MIGRATE_SCHEMA,
    ACTION_VERIFY_ONLY,
    ALEMBIC_AUTHORITATIVE_ENV_VAR,
    build_schema_startup_decision,
    log_schema_startup_decision_diagnostics,
)
from services.schema_version import ALEMBIC_VERSION_TABLE, STATUS_UNSTAMPED

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"
DOC_PATH = ROOT / "docs" / "P3_8_F_STARTUP_DECISION_DIAGNOSTICS.md"
MODULE_PATH = ROOT / "services" / "schema_startup.py"


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


@pytest.fixture
def memory_engine() -> Engine:
    import models  # noqa: F401

    engine = _make_memory_engine()
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_doc_covers_required_topics():
    text_doc = DOC_PATH.read_text(encoding="utf-8").lower()
    for topic in (
        "diagnostics only",
        "no action execution",
        "no startup blocking",
        "migrate_schema",
        "authoritative",
        "p3.8-g",
        "decision",
    ):
        assert topic in text_doc, f"Doc missing topic: {topic!r}"


def test_migrate_schema_still_runs_before_diagnostics_when_flag_off():
    wiring_src = inspect.getsource(
        __import__(
            "services.schema_startup_wiring",
            fromlist=["run_schema_startup_in_session"],
        ).run_schema_startup_in_session
    )
    assert wiring_src.index("migrate_schema_fn(session)") < wiring_src.index("log_fn(session)")


def test_flag_off_path_uses_dispatcher_in_app():
    app_text = APP_PATH.read_text(encoding="utf-8")
    assert "_run_schema_startup(_boot_session)" in app_text
    assert "migrate_schema(_boot_session)" not in app_text.replace(
        "migrate_schema_fn=migrate_schema", ""
    )


def test_flag_off_logs_run_migrate_schema_decision(memory_engine, caplog):
    caplog.set_level(logging.INFO)
    log_schema_startup_decision_diagnostics(
        memory_engine,
        environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "0"},
        logger=logging.getLogger("test.schema"),
    )
    decision_lines = [r.message for r in caplog.records if "decision action=" in r.message]
    assert decision_lines
    assert f"decision action={ACTION_RUN_MIGRATE_SCHEMA}" in decision_lines[0]


def test_flag_on_at_head_logs_verify_only(memory_engine, caplog):
    _create_alembic_version_table(memory_engine)
    _stamp(memory_engine, "0001")
    caplog.set_level(logging.INFO)
    log_schema_startup_decision_diagnostics(
        memory_engine,
        environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
        is_new_db=False,
        logger=logging.getLogger("test.schema"),
    )
    decision_lines = [r.message for r in caplog.records if "decision action=" in r.message]
    assert f"decision action={ACTION_VERIFY_ONLY}" in decision_lines[0]


def test_flag_on_unstamped_logs_require_stamp_startup_still_allowed(memory_engine, caplog):
    caplog.set_level(logging.INFO)
    bundle = log_schema_startup_decision_diagnostics(
        memory_engine,
        environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
        is_new_db=False,
        logger=logging.getLogger("test.schema"),
    )
    assert bundle["decision"].action == ACTION_REQUIRE_STAMP
    assert bundle["would_block_startup"] is True
    decision_lines = [r.message for r in caplog.records if "decision action=" in r.message]
    assert "not enforced" in decision_lines[0]


def test_flag_on_ahead_of_code_logs_fail_closed_startup_still_allowed(memory_engine, caplog):
    _create_alembic_version_table(memory_engine)
    _stamp(memory_engine, "0002")
    caplog.set_level(logging.INFO)
    bundle = log_schema_startup_decision_diagnostics(
        memory_engine,
        environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
        is_new_db=False,
        logger=logging.getLogger("test.schema"),
    )
    assert bundle["decision"].action == ACTION_FAIL_CLOSED
    assert bundle["would_block_startup"] is True
    decision_lines = [r.message for r in caplog.records if "decision action=" in r.message]
    assert f"decision action={ACTION_FAIL_CLOSED}" in decision_lines[0]
    assert "not enforced" in decision_lines[0]


def test_build_decision_does_not_mutate_db(memory_engine):
    with memory_engine.connect() as conn:
        before = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' "
                f"AND name='{ALEMBIC_VERSION_TABLE}'"
            )
        ).fetchone()
    build_schema_startup_decision(
        memory_engine, environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "0"}
    )
    with memory_engine.connect() as conn:
        after = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' "
                f"AND name='{ALEMBIC_VERSION_TABLE}'"
            )
        ).fetchone()
    assert before == after


def _table_exists(engine: Engine) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' "
                f"AND name='{ALEMBIC_VERSION_TABLE}'"
            )
        ).fetchone()
        return row is not None


def test_no_alembic_upgrade_or_stamp_execution_path():
    app_text = APP_PATH.read_text(encoding="utf-8").lower()
    assert "alembic upgrade" not in app_text
    assert "alembic stamp" not in app_text
    assert "alembic.command" not in app_text

    log_src = inspect.getsource(log_schema_startup_decision_diagnostics).lower()
    assert "alembic.command" not in log_src
    assert "op.upgrade" not in log_src
    assert "migrate_schema(" not in log_src


def test_app_branches_through_dispatcher_not_inline_decision():
    app_text = APP_PATH.read_text(encoding="utf-8")
    assert "_run_schema_startup(_boot_session)" in app_text
    assert "decide_schema_startup_action" not in app_text
    assert "build_schema_startup_decision" not in app_text
    assert "run_upgrade_head(" not in app_text


def test_decision_action_not_executed(memory_engine):
    """Decision bundle is computed only; no migration hooks run."""
    bundle = build_schema_startup_decision(
        memory_engine,
        environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
        is_new_db=False,
    )
    assert bundle["diagnostic"]["read_only"] is True
    assert bundle["decision"].action == ACTION_REQUIRE_STAMP
