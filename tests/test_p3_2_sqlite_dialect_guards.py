"""P3.2-B — SQLite dialect guards on db.py connect listener.

Verifies PRAGMA foreign_keys=ON remains enabled for SQLite and is skipped for
other dialects. No PostgreSQL engine switch or runtime behavior change.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

import db


class _SpyCursor:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, sql: str) -> None:
        self.executed.append(sql)

    def close(self) -> None:
        pass


class _SpyDbapiConnection:
    def __init__(self) -> None:
        self.cursor_obj = _SpyCursor()

    def cursor(self) -> _SpyCursor:
        return self.cursor_obj


def test_db_module_imports_cleanly():
    """db.py import/reload exposes Base, engine, and SessionLocal."""
    reloaded = importlib.reload(db)
    assert reloaded.Base is not None
    assert reloaded.engine is not None
    assert reloaded.SessionLocal is not None
    assert reloaded.engine.dialect.name == "sqlite"


def test_sqlite_connect_listener_enables_foreign_keys():
    """Production SQLite engine still turns on PRAGMA foreign_keys after connect."""
    assert db.engine.dialect.name == "sqlite"
    with db.engine.connect() as conn:
        fk_enabled = conn.exec_driver_sql("PRAGMA foreign_keys").scalar()
    assert fk_enabled == 1


def test_in_memory_sqlite_listener_enables_foreign_keys():
    """Fresh SQLite engine with the same listener pattern preserves FK enforcement."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def _listener(dbapi_connection, connection_record):
        db._set_sqlite_pragma(dbapi_connection, connection_record)

    with test_engine.connect() as conn:
        fk_enabled = conn.exec_driver_sql("PRAGMA foreign_keys").scalar()
    assert fk_enabled == 1


def test_non_sqlite_dialect_skips_pragma(monkeypatch):
    """When the bound engine dialect is not sqlite, PRAGMA must not run."""
    monkeypatch.setattr(db.engine.dialect, "name", "postgresql")
    spy = _SpyDbapiConnection()

    db._set_sqlite_pragma(spy, SimpleNamespace())

    assert spy.cursor_obj.executed == []


@pytest.mark.parametrize("dialect_name", ("postgresql", "mysql", "mssql"))
def test_non_sqlite_dialects_skip_pragma(monkeypatch, dialect_name: str):
    monkeypatch.setattr(db.engine.dialect, "name", dialect_name)
    spy = _SpyDbapiConnection()

    db._set_sqlite_pragma(spy, SimpleNamespace())

    assert spy.cursor_obj.executed == []


def test_sqlite_dialect_executes_pragma_via_listener(monkeypatch):
    """Direct listener call on sqlite dialect issues PRAGMA foreign_keys = ON."""
    monkeypatch.setattr(db.engine.dialect, "name", "sqlite")
    spy = _SpyDbapiConnection()

    db._set_sqlite_pragma(spy, SimpleNamespace())

    assert spy.cursor_obj.executed == ["PRAGMA foreign_keys = ON"]


def test_db_source_contains_dialect_guard():
    """Contract: db.py gates PRAGMA on engine dialect name sqlite."""
    text_source = Path(db.__file__).read_text(encoding="utf-8")
    assert 'engine.dialect.name != "sqlite"' in text_source
    assert "PRAGMA foreign_keys = ON" in text_source
