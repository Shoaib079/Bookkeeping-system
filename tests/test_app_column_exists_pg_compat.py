"""Regression: app._column_exists dialect-safe inspection (PG cutover startup)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock(session_state={})

import app  # noqa: E402
import models  # noqa: F401 — register metadata
from db import Base


@pytest.fixture()
def sqlite_session():
    from sqlalchemy import create_engine, event

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class TestColumnExistsSqlite:
    def test_existing_column(self, sqlite_session):
        assert app._column_exists(sqlite_session, "companies", "slug") is True

    def test_missing_column(self, sqlite_session):
        assert app._column_exists(sqlite_session, "companies", "not_a_column") is False

    def test_missing_table(self, sqlite_session):
        assert app._column_exists(sqlite_session, "not_a_table", "company_id") is False


class TestColumnExistsSourceContract:
    def test_column_exists_does_not_use_pragma(self):
        src = app._column_exists.__doc__ or ""
        import inspect

        body = inspect.getsource(app._column_exists)
        assert "PRAGMA" not in body
        assert "inspect" in body


class TestRepairOrphanCompanyIds:
    def test_repair_does_not_call_pragma(self):
        import inspect

        body = inspect.getsource(app._backfill_null_company_ids)
        assert "PRAGMA" not in body

    def test_repair_runs_on_sqlite_without_error(self, sqlite_session):
        import datetime

        company = models.Company(
            name="Test Co",
            slug="company_1",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        sqlite_session.add(company)
        sqlite_session.commit()
        app._repair_orphan_company_ids(sqlite_session)


@pytest.mark.optional_postgres
class TestColumnExistsPostgres:
    def test_existing_and_missing_columns(self):
        from postgres_utils import get_test_postgres_url, require_test_postgres_url
        from sqlalchemy import create_engine

        if get_test_postgres_url() is None:
            pytest.skip("ERP_TEST_POSTGRES_URL not set")

        url = require_test_postgres_url()
        engine = create_engine(url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        try:
            assert app._column_exists(session, "journal_entries", "company_id") is True
            assert app._column_exists(session, "journal_entries", "not_a_column") is False
        finally:
            session.close()
            engine.dispose()

    def test_repair_orphan_company_ids_on_postgres(self):
        from postgres_utils import get_test_postgres_url, require_test_postgres_url
        from sqlalchemy import create_engine

        if get_test_postgres_url() is None:
            pytest.skip("ERP_TEST_POSTGRES_URL not set")

        url = require_test_postgres_url()
        engine = create_engine(url, pool_pre_ping=True)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        try:
            app._repair_orphan_company_ids(session)
        finally:
            session.close()
            engine.dispose()
