"""MD-05-IMPL-4 — helpers for Alembic 0002 migration smoke (test-only).

Never connects to production ``erp_data.db``. Uses ``DATABASE_URL`` env override
for ephemeral SQLite file DBs or optional ``ERP_TEST_POSTGRES_URL``.
"""

from __future__ import annotations

import datetime
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import models
from money_numeric_columns import NUMERIC_19_2, NUMERIC_19_4, NUMERIC_19_8
from p3_schema_equivalence_utils import extract_sqlite_schema_summary
from registry.coa_seed import seed_chart_of_accounts_for_company
from services.banking_balance import apply_account_balance_delta, sync_bank_account_balances
from services.money import money_to_float
from services.read_reports import compute_profit_loss

ROOT = Path(__file__).resolve().parents[1]
COMPANY_ID = 1
POST_DATE = datetime.date(2025, 6, 15)
PERIOD_START = datetime.date(2025, 6, 1)
PERIOD_END = datetime.date(2025, 6, 30)
GOLDEN_AMOUNT = 100.01


@dataclass(frozen=True)
class MoneySnapshot:
    total_debit: float
    total_credit: float
    cash_balance: float
    bank_stored: float
    pl_net: float


def require_alembic_cli() -> str:
    alembic_bin = shutil.which("alembic")
    if not alembic_bin:
        pytest.skip("alembic CLI not on PATH")
    return alembic_bin


def run_alembic_upgrade(database_url: str, revision: str) -> None:
    alembic_bin = require_alembic_cli()
    env = {**os.environ, "DATABASE_URL": database_url}
    result = subprocess.run(
        [alembic_bin, "upgrade", revision],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def make_sqlite_file_engine(db_path: Path) -> Engine:
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


def session_for_url(database_url: str) -> Session:
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
    )
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def seed_smoke_tenant(session: Session) -> None:
    """Minimal populated tenant at Alembic 0001 for migration smoke."""
    from services import posting

    session.add(
        models.Company(
            name="MD-05 Smoke Co",
            slug="md05_smoke",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
    )
    session.flush()
    seed_chart_of_accounts_for_company(session, COMPANY_ID)
    bank = models.BankAccount(
        name="Main Bank",
        currency="TRY",
        balance=0.0,
        company_id=COMPANY_ID,
        is_active=True,
    )
    session.add(bank)
    session.flush()
    sale = models.Sale(
        date=POST_DATE,
        invoice_number="SMOKE-001",
        customer_name="Walk-in",
        sale_type="Cash",
        amount=GOLDEN_AMOUNT,
        paid_amount=GOLDEN_AMOUNT,
        balance=0.0,
        status="Paid",
        company_id=COMPANY_ID,
        is_void=False,
    )
    session.add(sale)
    session.flush()
    posting.post_cash_sale(
        session,
        sale.id,
        GOLDEN_AMOUNT,
        POST_DATE,
        currency="TRY",
        company_id=COMPANY_ID,
    )
    btxn = models.BankTransaction(
        account_id=bank.id,
        date=POST_DATE,
        amount=50.0,
        type="deposit",
        description="Smoke deposit",
        company_id=COMPANY_ID,
    )
    session.add(btxn)
    apply_account_balance_delta(bank, "deposit", 50.0)
    session.commit()


def capture_money_snapshot(session: Session) -> MoneySnapshot:
    from services import posting
    from services.read_balances import calculate_account_balance

    lines = session.query(models.JournalEntryLine).order_by(models.JournalEntryLine.id).all()
    total_debit = sum(money_to_float(ln.debit) for ln in lines)
    total_credit = sum(money_to_float(ln.credit) for ln in lines)
    cash = posting.get_account_by_name(session, "Cash", currency="TRY", company_id=COMPANY_ID)
    bank = session.query(models.BankAccount).filter_by(company_id=COMPANY_ID).one()
    pl = compute_profit_loss(
        session,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        company_id=COMPANY_ID,
    )
    return MoneySnapshot(
        total_debit=total_debit,
        total_credit=total_credit,
        cash_balance=calculate_account_balance(session, cash, company_id=COMPANY_ID),
        bank_stored=money_to_float(bank.balance),
        pl_net=pl.net,
    )


def schema_integrity_fingerprint(summary: dict[str, Any]) -> dict[str, Any]:
    """Indexes/FKs/tables that must survive SQLite batch rebuild."""
    fk_items: list[tuple[str, str, str, str]] = []
    for table, rows in sorted(summary["foreign_keys"].items()):
        for row in rows:
            fk_items.append(
                (table, row["from_column"], row["to_table"], row["to_column"])
            )
    return {
        "tables": list(summary["tables"]),
        "indexes": sorted(summary["indexes"].keys()),
        "foreign_keys": sorted(fk_items),
    }


def sqlite_column_type(engine: Engine, table: str, column: str) -> str:
    with engine.connect() as conn:
        rows = conn.execute(text(f'PRAGMA table_info("{table}")')).fetchall()
    for row in rows:
        if row[1] == column:
            return str(row[2]).upper()
    raise KeyError(f"{table}.{column}")


def assert_sqlite_numeric_affinity(engine: Engine) -> None:
    for table, column in sorted(NUMERIC_19_2 | NUMERIC_19_4 | NUMERIC_19_8):
        type_name = sqlite_column_type(engine, table, column)
        assert "NUM" in type_name or "DEC" in type_name, (
            f"{table}.{column} expected Numeric affinity after 0002, got {type_name!r}"
        )


def resync_caches(session: Session) -> None:
    import app as erp_app

    erp_app.sync_account_balances(session)
    sync_bank_account_balances(session)


def pg_numeric_column_scale(engine: Engine, table: str, column: str) -> tuple[int, int]:
    from sqlalchemy import inspect

    insp = inspect(engine)
    for col in insp.get_columns(table):
        if col["name"] == column:
            col_type = col["type"]
            precision = getattr(col_type, "precision", None)
            scale = getattr(col_type, "scale", None)
            return int(precision or 0), int(scale or 0)
    raise KeyError(f"{table}.{column}")


from postgres_utils import drop_all_pg_objects
