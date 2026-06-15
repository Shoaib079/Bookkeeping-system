"""P3.8-A — contract tests for read-only schema startup diagnostics."""

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
    get_schema_startup_diagnostic,
    log_schema_startup_decision_diagnostics,
    startup_message_for_status,
)
from services.schema_version import (
    STATUS_AHEAD_OF_CODE,
    STATUS_AT_HEAD,
    STATUS_BEHIND_HEAD,
    STATUS_UNKNOWN,
    STATUS_UNSTAMPED,
    ALEMBIC_VERSION_TABLE,
)

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"
DOC_PATH = ROOT / "docs" / "P3_8_SCHEMA_STARTUP_DIAGNOSTICS.md"


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


def _table_exists(engine: Engine) -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' "
                f"AND name='{ALEMBIC_VERSION_TABLE}'"
            )
        ).fetchone()
        return row is not None


@pytest.fixture
def memory_engine() -> Engine:
    import models  # noqa: F401

    engine = _make_memory_engine()
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.mark.parametrize(
    ("status", "head", "expected_fragment"),
    [
        (STATUS_AT_HEAD, "0001", "stamped at Alembic head 0001"),
        (STATUS_UNSTAMPED, "0001", "not Alembic-stamped"),
        (STATUS_BEHIND_HEAD, "0002", "behind Alembic head"),
        (STATUS_AHEAD_OF_CODE, "0001", "newer than this code"),
        (STATUS_UNKNOWN, "0001", "could not be determined safely"),
    ],
)
def test_startup_messages_for_all_statuses(status, head, expected_fragment):
    message = startup_message_for_status(status, head_revision=head)
    assert expected_fragment in message


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_doc_covers_required_topics():
    text_doc = DOC_PATH.read_text(encoding="utf-8").lower()
    for topic in (
        "read-only",
        "diagnostic",
        "no startup blocking",
        "no upgrade",
        "no stamp",
        "migrate_schema",
        "authoritative",
        "p3.8-b",
    ):
        assert topic in text_doc, f"Doc missing topic: {topic!r}"


def test_unstamped_diagnostic(memory_engine):
    diag = get_schema_startup_diagnostic(memory_engine)
    assert diag["status"] == STATUS_UNSTAMPED
    assert diag["read_only"] is True
    assert diag["blocks_startup"] is False
    assert "migrate_schema remains active" in diag["message"]


def test_at_head_diagnostic(memory_engine):
    _create_alembic_version_table(memory_engine)
    _stamp(memory_engine, "0001")
    diag = get_schema_startup_diagnostic(memory_engine)
    assert diag["status"] == STATUS_AT_HEAD
    assert diag["db_revision"] == "0001"
    assert diag["head_revision"] == "0001"
    assert "stamped at Alembic head 0001" in diag["message"]


def test_ahead_of_code_diagnostic(memory_engine):
    _create_alembic_version_table(memory_engine)
    _stamp(memory_engine, "0002")
    diag = get_schema_startup_diagnostic(memory_engine)
    assert diag["status"] == STATUS_AHEAD_OF_CODE
    assert "newer than this code" in diag["message"]


def test_helper_does_not_mutate_db(memory_engine):
    exists_before = _table_exists(memory_engine)
    get_schema_startup_diagnostic(memory_engine)
    log_schema_startup_decision_diagnostics(memory_engine, logger=logging.getLogger("test"))
    assert _table_exists(memory_engine) == exists_before


def test_log_schema_startup_diagnostic_emits_info(caplog, memory_engine):
    caplog.set_level(logging.INFO)
    log_schema_startup_decision_diagnostics(memory_engine, logger=logging.getLogger("test.schema"))
    assert any("migrate_schema remains active" in r.message for r in caplog.records)


def test_migrate_schema_still_called_at_startup():
    main_src = inspect.getsource(
        __import__("app", fromlist=["main"]).main
    )
    assert "_run_schema_startup(_boot_session)" in main_src
    wiring_src = inspect.getsource(
        __import__(
            "services.schema_startup_wiring",
            fromlist=["run_schema_startup_in_session"],
        ).run_schema_startup_in_session
    )
    assert "migrate_schema_fn(session)" in wiring_src


def test_startup_has_no_alembic_upgrade_or_stamp():
    app_text = APP_PATH.read_text(encoding="utf-8").lower()
    assert "alembic upgrade" not in app_text
    assert "alembic stamp" not in app_text
    assert "op.upgrade" not in app_text
    assert "context.run_migrations" not in app_text

    startup_text = (ROOT / "services" / "schema_startup.py").read_text(encoding="utf-8")
    assert "alembic.command" not in startup_text
    assert "op.upgrade" not in startup_text
    assert "run_migrations" not in startup_text

    runtime_src = (
        inspect.getsource(get_schema_startup_diagnostic)
        + inspect.getsource(log_schema_startup_decision_diagnostics)
        + inspect.getsource(__import__("app", fromlist=["main"])._log_schema_startup_diagnostic)
    ).lower()
    assert "alembic upgrade" not in runtime_src
    assert "alembic stamp" not in runtime_src


def test_detect_from_session_wrapper(memory_engine):
    _create_alembic_version_table(memory_engine)
    _stamp(memory_engine, "0001")
    Session = sessionmaker(bind=memory_engine)
    with Session() as session:
        diag = get_schema_startup_diagnostic(session)
    assert diag["status"] == STATUS_AT_HEAD
