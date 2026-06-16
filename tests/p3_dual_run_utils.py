"""P3.2-D — SQLite / PostgreSQL dual-run parity harness (test-only).

Runs the same business flow on isolated SQLite (always) and optional PostgreSQL
(when ``ERP_TEST_POSTGRES_URL`` is set), then compares normalized persisted-state
summaries. Never uses ``db.engine`` or production ``erp_data.db``.
"""

from __future__ import annotations

import datetime
import sys
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator
from unittest.mock import MagicMock

from sqlalchemy import create_engine, event, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from services.money import line_money

import models
from db import Base
from postgres_utils import (
    create_test_postgres_engine,
    create_test_schema,
    drop_test_schema,
    get_test_postgres_url,
    validate_test_postgres_url,
)
from registry.coa_seed import seed_chart_of_accounts_for_company
from tests.helpers.commit_parity import (
    DEFAULT_TABLES,
    EXPENSE_TABLES,
    MOVEMENT_TABLES,
    PURCHASE_PAYABLE_TABLES,
    RECEIVABLE_PAYMENT_TABLES,
)

POST_DATE = datetime.date(2026, 9, 1)
DUE_DATE = datetime.date(2026, 10, 1)
AMOUNT = 150.0
CURRENCY = "TRY"

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

FlowFn = Callable[[Session, "ParitySeed"], None]

_MODELS_WITH_OPTIONAL_COMPANY_ID: tuple[type, ...] = (
    models.JournalEntry,
    models.JournalEntryLine,
    models.Sale,
    models.ExpenseRecord,
    models.Purchase,
    models.Payable,
    models.Partner,
    models.PartnerMovement,
    models.Worker,
    models.WorkerMovement,
    models.BankTransaction,
    models.BankAccount,
    models.AuditLog,
    models.Vendor,
)


@dataclass(frozen=True)
class ParitySeed:
    company_id: int
    bank_account_id: int


@dataclass(frozen=True)
class ParityFlowSpec:
    name: str
    runner: FlowFn
    tables: tuple[type, ...]


def make_sqlite_memory_engine() -> Engine:
    """In-memory SQLite engine with FK enforcement (mirrors db.py guard)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
        if engine.dialect.name != "sqlite":
            return
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


def _register_metadata() -> None:
    import models as _models  # noqa: F401


def seed_parity_tenant(session: Session) -> ParitySeed:
    """Seed company, standard COA, and a main bank account."""
    company = models.Company(
        name="Dual-Run Parity Co",
        slug="dual_run_parity_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    session.add(company)
    session.flush()
    seed_chart_of_accounts_for_company(session, company.id)
    bank = models.BankAccount(
        name="Main Bank",
        currency=CURRENCY,
        company_id=company.id,
        is_active=True,
        balance=10_000.0,
        kind="bank",
    )
    session.add(bank)
    session.flush()
    return ParitySeed(company_id=company.id, bank_account_id=bank.id)


def _free_account_code(session: Session, company_id: int, prefix: str) -> str:
    for n in range(1, 100):
        code = f"{prefix}{n:02d}"
        exists = (
            session.query(models.ChartOfAccounts)
            .filter_by(company_id=company_id, account_code=code)
            .first()
        )
        if not exists:
            return code
    raise RuntimeError(f"No free account code for prefix {prefix}")


def seed_partner_for_parity(session: Session, company_id: int, name: str = "Alice") -> int:
    cap_code = _free_account_code(session, company_id, "35")
    cur_code = _free_account_code(session, company_id, "36")
    adv_code = _free_account_code(session, company_id, "15")
    cap_acct = models.ChartOfAccounts(
        account_code=cap_code,
        account_name=f"{name} Capital",
        account_type="Equity",
        balance=0.0,
        is_active=True,
        company_id=company_id,
    )
    cur_acct = models.ChartOfAccounts(
        account_code=cur_code,
        account_name=f"{name} Current Account",
        account_type="Equity",
        balance=0.0,
        is_active=True,
        company_id=company_id,
    )
    adv_acct = models.ChartOfAccounts(
        account_code=adv_code,
        account_name=f"{name} Advances",
        account_type="Asset",
        balance=0.0,
        is_active=True,
        company_id=company_id,
    )
    session.add_all([cap_acct, cur_acct, adv_acct])
    session.flush()
    partner = models.Partner(
        name=name,
        profit_share_pct=100.0,
        capital_account_id=cap_acct.id,
        current_account_id=cur_acct.id,
        advance_account_id=adv_acct.id,
        is_active=True,
        created_at=datetime.datetime.now(),
        company_id=company_id,
    )
    session.add(partner)
    session.flush()
    return partner.id


def seed_worker_for_parity(session: Session, company_id: int, name: str = "Bob") -> int:
    worker = models.Worker(
        name=name,
        role="Staff",
        is_active=True,
        created_at=datetime.datetime.now(),
        company_id=company_id,
    )
    session.add(worker)
    session.flush()
    return worker.id


def seed_vendor_for_parity(session: Session, company_id: int, name: str = "Acme") -> int:
    vendor = models.Vendor(
        name=name,
        is_active=True,
        company_id=company_id,
    )
    session.add(vendor)
    session.flush()
    return vendor.id


def table_row_counts(session: Session, tables: tuple[type, ...]) -> dict[str, int]:
    return {
        table.__tablename__: session.query(func.count()).select_from(table).scalar() or 0
        for table in tables
    }


def journal_metrics(session: Session) -> dict[str, Any]:
    entries = session.query(models.JournalEntry).all()
    lines = session.query(models.JournalEntryLine).all()
    ref_counts: dict[str, int] = {}
    for entry in entries:
        key = entry.reference_type or ""
        ref_counts[key] = ref_counts.get(key, 0) + 1
    debit_total = round(sum(line_money(line.debit) for line in lines), 2)
    credit_total = round(sum(line_money(line.credit) for line in lines), 2)
    return {
        "journal_entry_count": len(entries),
        "journal_line_count": len(lines),
        "debit_total": debit_total,
        "credit_total": credit_total,
        "balanced": abs(debit_total - credit_total) < 0.02,
        "reference_type_counts": dict(sorted(ref_counts.items())),
    }


def company_id_null_counts(session: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in _MODELS_WITH_OPTIONAL_COMPANY_ID:
        if hasattr(model, "company_id"):
            nulls = (
                session.query(func.count())
                .select_from(model)
                .filter(model.company_id.is_(None))
                .scalar()
                or 0
            )
            counts[model.__tablename__] = nulls
    return dict(sorted(counts.items()))


def void_counts(session: Session) -> dict[str, int]:
    return {
        "sales": session.query(models.Sale).filter(models.Sale.is_void.is_(True)).count(),
        "expenses": session.query(models.ExpenseRecord)
        .filter(models.ExpenseRecord.is_void.is_(True))
        .count(),
        "purchases": session.query(models.Purchase)
        .filter(models.Purchase.is_void.is_(True))
        .count(),
        "payables": session.query(models.Payable)
        .filter(models.Payable.is_void.is_(True))
        .count(),
        "partner_movements": session.query(models.PartnerMovement)
        .filter(models.PartnerMovement.is_void.is_(True))
        .count(),
        "worker_movements": session.query(models.WorkerMovement)
        .filter(models.WorkerMovement.is_void.is_(True))
        .count(),
    }


def normalized_parity_summary(
    session: Session,
    *,
    tables: tuple[type, ...],
) -> dict[str, Any]:
    """Engine-neutral persisted-state fingerprint for dual-run comparison."""
    return {
        "counts": table_row_counts(session, tables),
        "journal": journal_metrics(session),
        "audit_count": session.query(func.count())
        .select_from(models.AuditLog)
        .scalar()
        or 0,
        "void_counts": void_counts(session),
        "company_id_null_counts": company_id_null_counts(session),
    }


def assert_parity_summaries_equal(left: dict[str, Any], right: dict[str, Any]) -> None:
    assert left == right


@contextmanager
def isolated_sqlite_session() -> Iterator[Session]:
    _register_metadata()
    engine = make_sqlite_memory_engine()
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@contextmanager
def isolated_postgres_session(url: str) -> Iterator[Session]:
    _register_metadata()
    safe_url = validate_test_postgres_url(url)
    engine = create_test_postgres_engine(safe_url)
    create_test_schema(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        drop_test_schema(engine)
        engine.dispose()


def run_parity_flow_sqlite(flow: FlowFn, *, tables: tuple[type, ...]) -> dict[str, Any]:
    with isolated_sqlite_session() as session:
        seed = seed_parity_tenant(session)
        session.commit()
        flow(session, seed)
        session.commit()
        return normalized_parity_summary(session, tables=tables)


def run_parity_flow_postgres(
    flow: FlowFn,
    *,
    tables: tuple[type, ...],
    url: str | None = None,
) -> dict[str, Any]:
    configured = url or get_test_postgres_url()
    if not configured:
        raise RuntimeError("PostgreSQL URL not configured")
    with isolated_postgres_session(configured) as session:
        seed = seed_parity_tenant(session)
        session.commit()
        flow(session, seed)
        session.commit()
        return normalized_parity_summary(session, tables=tables)


def dual_engine_parity(
    flow: FlowFn,
    *,
    tables: tuple[type, ...],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Run flow on SQLite; on PostgreSQL when configured, assert summaries match."""
    sqlite_summary = run_parity_flow_sqlite(flow, tables=tables)
    pg_url = get_test_postgres_url()
    if pg_url is None:
        return sqlite_summary, None
    postgres_summary = run_parity_flow_postgres(flow, tables=tables, url=pg_url)
    assert_parity_summaries_equal(sqlite_summary, postgres_summary)
    return sqlite_summary, postgres_summary


# ── Golden parity flows ───────────────────────────────────────────────────────


def _posting():
    import app  # noqa: F401 — initialise module graph before services.posting

    from services import posting as posting_svc

    return posting_svc


def flow_cash_sale(session: Session, seed: ParitySeed) -> None:
    sale = models.Sale(
        date=POST_DATE,
        invoice_number="DR-CASH-001",
        customer_name="Walk-in",
        description="dual-run cash sale",
        amount=AMOUNT,
        sale_type="Cash",
        paid_amount=AMOUNT,
        balance=0.0,
        due_date=POST_DATE,
        status="Paid",
        company_id=seed.company_id,
    )
    posting_svc = _posting()
    session.add(sale)
    session.flush()
    posting_svc.post_cash_sale(
        session,
        sale.id,
        AMOUNT,
        POST_DATE,
        company_id=seed.company_id,
    )


def flow_expense(session: Session, seed: ParitySeed) -> None:
    posting_svc = _posting()
    record = models.ExpenseRecord(
        date=POST_DATE,
        expense_type="Office",
        category="Office",
        description="dual-run expense",
        amount=AMOUNT,
        payment_method="Cash",
        gross_salary=AMOUNT,
        deductions=0.0,
        net_salary=AMOUNT,
        currency=CURRENCY,
        fx_rate=1.0,
        native_amount=AMOUNT,
        company_id=seed.company_id,
    )
    session.add(record)
    session.flush()
    posting_svc.post_expense(
        session,
        record.id,
        AMOUNT,
        POST_DATE,
        "Office",
        "Cash",
        company_id=seed.company_id,
    )


def flow_credit_purchase_payable(session: Session, seed: ParitySeed) -> None:
    posting_svc = _posting()
    vendor_id = seed_vendor_for_parity(session, seed.company_id)
    purchase = models.Purchase(
        date=POST_DATE,
        vendor_id=vendor_id,
        amount=AMOUNT,
        purchase_type="Credit",
        gl_debit="Inventory",
        description="dual-run credit purchase",
        company_id=seed.company_id,
    )
    session.add(purchase)
    session.flush()
    posting_svc.post_purchase(
        session,
        purchase.id,
        AMOUNT,
        POST_DATE,
        purchase_type="Credit",
        gl_debit="Inventory",
        currency=CURRENCY,
        company_id=seed.company_id,
    )
    payable = models.Payable(
        date=POST_DATE,
        vendor_id=vendor_id,
        amount=AMOUNT,
        due_date=DUE_DATE,
        paid=False,
        description=f"From Purchase #{purchase.id}",
        expense_category="Inventory",
        purchase_id=purchase.id,
        company_id=seed.company_id,
    )
    session.add(payable)


def flow_receivable_payment(session: Session, seed: ParitySeed) -> None:
    posting_svc = _posting()
    sale = models.Sale(
        date=POST_DATE,
        invoice_number="DR-CR-001",
        customer_name="Credit Customer",
        description="dual-run credit sale",
        amount=AMOUNT,
        sale_type="Credit",
        paid_amount=0.0,
        balance=AMOUNT,
        due_date=DUE_DATE,
        status="Open",
        company_id=seed.company_id,
    )
    session.add(sale)
    session.flush()
    posting_svc.post_credit_sale(
        session,
        sale.id,
        AMOUNT,
        POST_DATE,
        company_id=seed.company_id,
    )
    err = posting_svc.post_receivable_payment(
        session,
        sale.id,
        AMOUNT,
        POST_DATE,
        payment_method="Cash",
        company_id=seed.company_id,
    )
    if err:
        raise AssertionError(err)


def flow_partner_capital_contribution(session: Session, seed: ParitySeed) -> None:
    posting_svc = _posting()
    partner_id = seed_partner_for_parity(session, seed.company_id)
    movement_id, err = posting_svc.post_partner_movement(
        session,
        partner_id,
        "CapitalContribution",
        AMOUNT,
        POST_DATE,
        bank_account_id=seed.bank_account_id,
        company_id=seed.company_id,
    )
    if err:
        raise AssertionError(err)
    assert movement_id is not None


def flow_worker_advance(session: Session, seed: ParitySeed) -> None:
    posting_svc = _posting()
    worker_id = seed_worker_for_parity(session, seed.company_id)
    movement_id, err = posting_svc.post_worker_movement(
        session,
        worker_id,
        "Advance",
        POST_DATE,
        bank_account_id=seed.bank_account_id,
        amount=AMOUNT,
        company_id=seed.company_id,
    )
    if err:
        raise AssertionError(err)
    assert movement_id is not None


PARITY_FLOWS: tuple[ParityFlowSpec, ...] = (
    ParityFlowSpec("cash_sale", flow_cash_sale, DEFAULT_TABLES),
    ParityFlowSpec("expense", flow_expense, EXPENSE_TABLES),
    ParityFlowSpec(
        "credit_purchase_payable",
        flow_credit_purchase_payable,
        PURCHASE_PAYABLE_TABLES,
    ),
    ParityFlowSpec(
        "receivable_payment",
        flow_receivable_payment,
        RECEIVABLE_PAYMENT_TABLES,
    ),
    ParityFlowSpec(
        "partner_capital_contribution",
        flow_partner_capital_contribution,
        MOVEMENT_TABLES,
    ),
    ParityFlowSpec("worker_advance", flow_worker_advance, MOVEMENT_TABLES),
)
