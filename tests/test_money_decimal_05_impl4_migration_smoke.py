"""MD-05-IMPL-4 — SQLite populated smoke + optional PG migration test + report parity.

Upgrades a **seeded copy** SQLite database 0001→0002 (never production ``erp_data.db``),
verifies constraint preservation, money snapshot parity, posting after migration, and
optional PostgreSQL NUMERIC column exactness when ``ERP_TEST_POSTGRES_URL`` is set.
"""

from __future__ import annotations

import sys
import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import models
from money_numeric_columns import FLOAT_REMAIN, NUMERIC_19_2, NUMERIC_19_4, NUMERIC_19_8
from postgres_utils import create_test_postgres_engine, get_test_postgres_url, require_test_postgres_url
from services.money import money_to_float, persist_money, quantize_money
from p3_schema_equivalence_utils import extract_sqlite_schema_summary

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

import app  # noqa: F401 — bootstrap import graph before services.posting

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

from services import posting
from services.read_balances import calculate_account_balance
from tests.md05_migration_smoke_utils import (
    COMPANY_ID,
    GOLDEN_AMOUNT,
    POST_DATE,
    ROOT,
    assert_sqlite_numeric_affinity,
    capture_money_snapshot,
    drop_all_pg_objects,
    make_sqlite_file_engine,
    pg_numeric_column_scale,
    resync_caches,
    run_alembic_upgrade,
    schema_integrity_fingerprint,
    seed_smoke_tenant,
    session_for_url,
    sqlite_column_type,
)

DOC_PATH = ROOT / "docs" / "MONEY_DECIMAL_05_IMPL_4.md"
PRODUCTION_DB = ROOT / "erp_data.db"


class TestImpl4DocContract:
    def test_impl4_doc_exists(self):
        assert DOC_PATH.exists()
        assert DOC_PATH.stat().st_size > 0

    def test_impl4_doc_covers_scope(self):
        text_doc = DOC_PATH.read_text(encoding="utf-8").lower()
        for topic in (
            "sqlite",
            "0002",
            "erp_test_postgres_url",
            "golden",
            "production",
        ):
            assert topic in text_doc, f"missing topic: {topic!r}"

    def test_harness_never_targets_production_db(self):
        src = Path(__file__).read_text(encoding="utf-8")
        assert "erp_data.db" in src
        assert str(PRODUCTION_DB) not in src or "never" in src.lower() or "PRODUCTION_DB" in src


class TestSqlitePopulatedMigrationSmoke:
    def test_upgrade_0001_to_0002_preserves_integrity_and_money(self, tmp_path):
        db_path = tmp_path / "md05_impl4_seeded.db"
        database_url = f"sqlite:///{db_path.as_posix()}"

        run_alembic_upgrade(database_url, "0001")
        with session_for_url(database_url) as session:
            seed_smoke_tenant(session)
            before = capture_money_snapshot(session)

        engine = make_sqlite_file_engine(db_path)
        try:
            schema_before = schema_integrity_fingerprint(
                extract_sqlite_schema_summary(engine)
            )
        finally:
            engine.dispose()

        run_alembic_upgrade(database_url, "0002")

        engine = make_sqlite_file_engine(db_path)
        try:
            with engine.connect() as conn:
                rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert rev == "0002"

            schema_after = schema_integrity_fingerprint(
                extract_sqlite_schema_summary(engine)
            )
            assert schema_after["tables"] == schema_before["tables"]
            before_idx = set(schema_before["indexes"])
            after_idx = set(schema_after["indexes"])
            assert before_idx == after_idx, sorted(before_idx ^ after_idx)
            assert schema_after["foreign_keys"] == schema_before["foreign_keys"]

            assert_sqlite_numeric_affinity(engine)

            for table, column in sorted(FLOAT_REMAIN):
                assert sqlite_column_type(engine, table, column) == "FLOAT"
        finally:
            engine.dispose()

        with session_for_url(database_url) as session:
            after = capture_money_snapshot(session)
            assert after.total_debit == pytest.approx(before.total_debit)
            assert after.total_credit == pytest.approx(before.total_credit)
            assert after.cash_balance == pytest.approx(before.cash_balance)
            assert after.bank_stored == pytest.approx(before.bank_stored)
            assert after.pl_net == pytest.approx(before.pl_net)

            resync_caches(session)

            sale2 = models.Sale(
                date=POST_DATE,
                invoice_number="SMOKE-002",
                customer_name="Walk-in",
                sale_type="Cash",
                amount=10.0,
                paid_amount=10.0,
                balance=0.0,
                status="Paid",
                company_id=COMPANY_ID,
                is_void=False,
            )
            session.add(sale2)
            session.flush()
            posting.post_cash_sale(
                session,
                sale2.id,
                10.0,
                POST_DATE,
                currency="TRY",
                company_id=COMPANY_ID,
            )
            session.commit()

            final = capture_money_snapshot(session)
            assert final.pl_net == pytest.approx(before.pl_net + 10.0)

    def test_golden_amount_posting_after_0002(self, tmp_path):
        db_path = tmp_path / "md05_impl4_golden.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic_upgrade(database_url, "0001")
        with session_for_url(database_url) as session:
            seed_smoke_tenant(session)
        run_alembic_upgrade(database_url, "0002")

        with session_for_url(database_url) as session:
            cash = posting.get_account_by_name(
                session, "Cash", currency="TRY", company_id=COMPANY_ID
            )
            assert money_to_float(
                calculate_account_balance(session, cash, company_id=COMPANY_ID)
            ) == pytest.approx(GOLDEN_AMOUNT)

    def test_ugly_double_sale_amount_readable_after_0002(self, tmp_path):
        db_path = tmp_path / "md05_impl4_ugly.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic_upgrade(database_url, "0001")
        with session_for_url(database_url) as session:
            session.add(
                models.Company(
                    name="Ugly Co",
                    slug="ugly_co",
                    is_active=True,
                    created_at=datetime.datetime.now(),
                )
            )
            session.commit()
        run_alembic_upgrade(database_url, "0002")

        with session_for_url(database_url) as session:
            sale = models.Sale(
                date=POST_DATE,
                invoice_number="UGLY-001",
                customer_name="Walk-in",
                sale_type="Cash",
                amount=100.0100000001,
                paid_amount=0.0,
                balance=100.0100000001,
                status="Open",
                company_id=COMPANY_ID,
                is_void=False,
            )
            session.add(sale)
            session.commit()
            session.refresh(sale)
            assert money_to_float(sale.amount) == 100.01
            assert isinstance(sale.amount, Decimal)
            assert persist_money(sale.amount) == quantize_money("100.01")


@pytest.mark.optional_postgres
class TestPostgresAlembic0002Smoke:
    def test_pg_upgrade_head_numeric_columns(self):
        if get_test_postgres_url() is None:
            pytest.skip("ERP_TEST_POSTGRES_URL not set")
        url = require_test_postgres_url()
        engine = create_test_postgres_engine(url)
        try:
            drop_all_pg_objects(engine)
        finally:
            engine.dispose()

        run_alembic_upgrade(url, "head")

        engine = create_test_postgres_engine(url)
        try:
            with engine.connect() as conn:
                rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            assert rev == "0002"

            prec, scale = pg_numeric_column_scale(engine, "journal_entry_lines", "debit")
            assert prec == 19 and scale == 2

            prec, scale = pg_numeric_column_scale(engine, "journal_entry_lines", "amount_native")
            assert prec == 19 and scale == 4

            prec, scale = pg_numeric_column_scale(engine, "sales", "fx_rate")
            assert prec == 19 and scale == 8

            prec, scale = pg_numeric_column_scale(engine, "ingredients", "cost_per_base_unit")
            assert prec == 19 and scale == 4
        finally:
            engine.dispose()

    def test_pg_numeric_exactness_round_trip(self):
        if get_test_postgres_url() is None:
            pytest.skip("ERP_TEST_POSTGRES_URL not set")
        url = require_test_postgres_url()
        engine = create_test_postgres_engine(url)
        try:
            drop_all_pg_objects(engine)
        finally:
            engine.dispose()

        run_alembic_upgrade(url, "head")

        engine = create_test_postgres_engine(url)
        Session = sessionmaker(bind=engine)
        try:
            with Session() as session:
                session.add(
                    models.Company(
                        name="PG Numeric Co",
                        slug="pg_numeric",
                        is_active=True,
                        created_at=datetime.datetime.now(),
                    )
                )
                session.flush()
                session.execute(
                    text(
                        "INSERT INTO chart_of_accounts "
                        "(account_code, account_name, account_type, balance, is_active, company_id) "
                        "VALUES ('9999', 'Probe', 'Asset', 0, true, 1)"
                    )
                )
                session.execute(
                    text(
                        "INSERT INTO journal_entries "
                        "(entry_date, description, reference_type, company_id) "
                        "VALUES ('2025-01-01', 'probe', 'Probe', 1)"
                    )
                )
                je_id = session.execute(text("SELECT id FROM journal_entries LIMIT 1")).scalar_one()
                acct_id = session.execute(
                    text("SELECT id FROM chart_of_accounts WHERE account_code = '9999'")
                ).scalar_one()
                session.execute(
                    text(
                        "INSERT INTO journal_entry_lines "
                        "(journal_entry_id, account_id, debit, credit, company_id) "
                        "VALUES (:je, :acct, 0.1::numeric + 0.2::numeric, 0, 1)"
                    ),
                    {"je": je_id, "acct": acct_id},
                )
                session.commit()
                debit = session.execute(
                    text("SELECT debit FROM journal_entry_lines LIMIT 1")
                ).scalar_one()
                assert debit == Decimal("0.30")
        finally:
            engine.dispose()
