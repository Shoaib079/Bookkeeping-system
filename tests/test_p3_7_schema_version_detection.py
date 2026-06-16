"""P3.7 — contract tests for read-only Alembic schema version detection."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from db import Base
from services.schema_version import (
    STATUS_AHEAD_OF_CODE,
    STATUS_AT_HEAD,
    STATUS_BEHIND_HEAD,
    STATUS_UNKNOWN,
    STATUS_UNSTAMPED,
    ALEMBIC_VERSION_TABLE,
    DEFAULT_VERSIONS_DIR,
    SchemaVersionInfo,
    detect_schema_version,
    detect_schema_version_from_session,
    discover_local_revisions,
    format_schema_version_summary,
    resolve_head_revision,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_7_SCHEMA_VERSION_DETECTION.md"


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


def _table_row_count(engine: Engine) -> int:
    with engine.connect() as conn:
        if not conn.dialect.has_table(conn, ALEMBIC_VERSION_TABLE):
            return 0
        return conn.execute(
            text(f"SELECT COUNT(*) FROM {ALEMBIC_VERSION_TABLE}")
        ).scalar_one()


@pytest.fixture
def memory_engine() -> Engine:
    import models  # noqa: F401

    engine = _make_memory_engine()
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


def test_doc_exists():
    assert DOC_PATH.exists(), f"Missing doc: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0


def test_doc_covers_required_topics():
    text_doc = DOC_PATH.read_text(encoding="utf-8").lower()
    for topic in (
        "read-only",
        "no upgrade",
        "no stamp",
        "migrate_schema",
        "authoritative",
        "unstamped",
        "at_head",
        "behind_head",
        "ahead_of_code",
        "unknown",
        "p3.8",
        "rollback",
    ):
        assert topic in text_doc, f"Doc missing topic: {topic!r}"


def test_local_head_detection_returns_0002():
    revisions = discover_local_revisions(DEFAULT_VERSIONS_DIR)
    assert "0001" in revisions
    assert "0002" in revisions
    assert revisions["0002"] == "0001"
    assert resolve_head_revision(revisions) == "0002"


def test_missing_alembic_version_table_is_unstamped(memory_engine):
    info = detect_schema_version(memory_engine)
    assert info.status == STATUS_UNSTAMPED
    assert info.alembic_version_table_exists is False
    assert info.db_revision is None
    assert info.head_revision == "0002"
    assert info.row_count == 0
    assert "unstamped" in info.message.lower() or "no alembic_version" in info.message.lower()


def test_empty_alembic_version_table_is_unstamped(memory_engine):
    _create_alembic_version_table(memory_engine)
    info = detect_schema_version(memory_engine)
    assert info.status == STATUS_UNSTAMPED
    assert info.alembic_version_table_exists is True
    assert info.row_count == 0


def test_alembic_version_0001_is_behind_head(memory_engine):
    _create_alembic_version_table(memory_engine)
    _stamp(memory_engine, "0001")
    info = detect_schema_version(memory_engine)
    assert info.status == STATUS_BEHIND_HEAD
    assert info.db_revision == "0001"
    assert info.head_revision == "0002"
    assert not info.is_at_head()


def test_alembic_version_0002_is_at_head(memory_engine):
    _create_alembic_version_table(memory_engine)
    _stamp(memory_engine, "0002")
    info = detect_schema_version(memory_engine)
    assert info.status == STATUS_AT_HEAD
    assert info.db_revision == "0002"
    assert info.head_revision == "0002"
    assert info.is_at_head()


def test_fake_older_revision_is_unknown(memory_engine):
    _create_alembic_version_table(memory_engine)
    _stamp(memory_engine, "0000")
    info = detect_schema_version(memory_engine)
    assert info.status == STATUS_UNKNOWN
    assert info.db_revision == "0000"


def test_fake_future_revision_is_ahead_of_code(memory_engine):
    _create_alembic_version_table(memory_engine)
    _stamp(memory_engine, "0003")
    info = detect_schema_version(memory_engine)
    assert info.status == STATUS_AHEAD_OF_CODE
    assert info.db_revision == "0003"


def test_behind_head_when_local_chain_has_later_revision(memory_engine, tmp_path):
    versions_dir = tmp_path / "versions"
    versions_dir.mkdir()
    (versions_dir / "0001_baseline.py").write_text(
        'revision = "0001"\ndown_revision = None\n',
        encoding="utf-8",
    )
    (versions_dir / "0002_followup.py").write_text(
        'revision = "0002"\ndown_revision = "0001"\n',
        encoding="utf-8",
    )
    _create_alembic_version_table(memory_engine)
    _stamp(memory_engine, "0001")
    info = detect_schema_version(memory_engine, versions_dir=versions_dir)
    assert info.status == STATUS_BEHIND_HEAD
    assert info.head_revision == "0002"
    assert info.db_revision == "0001"


def test_multiple_rows_is_unknown(memory_engine):
    _create_alembic_version_table(memory_engine)
    with memory_engine.begin() as conn:
        conn.execute(
            text(f"INSERT INTO {ALEMBIC_VERSION_TABLE} (version_num) VALUES ('0001')")
        )
        conn.execute(
            text(f"INSERT INTO {ALEMBIC_VERSION_TABLE} (version_num) VALUES ('0002')")
        )
    info = detect_schema_version(memory_engine)
    assert info.status == STATUS_UNKNOWN
    assert info.row_count == 2


def test_helper_does_not_mutate_db(memory_engine):
    before_tables = _table_row_count(memory_engine)
    detect_schema_version(memory_engine)
    assert _table_row_count(memory_engine) == before_tables

    _create_alembic_version_table(memory_engine)
    _stamp(memory_engine, "0001")
    before_rows = _table_row_count(memory_engine)
    detect_schema_version(memory_engine)
    assert _table_row_count(memory_engine) == before_rows


def test_detect_from_session_wrapper(memory_engine):
    _create_alembic_version_table(memory_engine)
    _stamp(memory_engine, "0002")
    Session = sessionmaker(bind=memory_engine)
    with Session() as session:
        info = detect_schema_version_from_session(session)
    assert info.status == STATUS_AT_HEAD


def test_format_schema_version_summary():
    info = SchemaVersionInfo(
        status=STATUS_AT_HEAD,
        alembic_version_table_exists=True,
        db_revision="0001",
        head_revision="0001",
        known_revisions=("0001",),
        row_count=1,
        message="ok",
    )
    summary = format_schema_version_summary(info)
    assert "at_head" in summary
    assert "'0001'" in summary
