"""POSTGRES cutover schema stamp — unit + optional PG integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_cutover_schema_module_exports():
    src = (ROOT / "services" / "postgres_cutover_schema.py").read_text(encoding="utf-8")
    assert "ensure_pg_stamped_at_head" in src
    assert "verify_pg_schema_matches_head" in src


@pytest.mark.optional_postgres
def test_ensure_stamp_on_populated_pg_without_alembic_table():
    import os

    pg_url = os.environ.get("ERP_TEST_POSTGRES_URL")
    if not pg_url:
        pytest.skip("ERP_TEST_POSTGRES_URL not set")

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from services.pg_sqlite_data_migration import table_row_counts
    from services.postgres_cutover_schema import ensure_pg_stamped_at_head, inspect_pg_alembic_state

    engine = create_engine(pg_url, pool_pre_ping=True)
    try:
        state = inspect_pg_alembic_state(engine)
        if state.companies_count == 0:
            pytest.skip("PostgreSQL test DB empty — run cutover script first")

        Session = sessionmaker(bind=engine)
        with Session() as session:
            counts_before = table_row_counts(session)

        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))

        stamp = ensure_pg_stamped_at_head(pg_url, allow_execute=True)
        assert stamp.success

        state_after = inspect_pg_alembic_state(engine)
        assert state_after.current_revision == "0002"

        with Session() as session:
            counts_after = table_row_counts(session)
        assert counts_before == counts_after
    finally:
        engine.dispose()
