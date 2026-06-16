"""P2-HARDEN-01-H01 — company_id stamping matrix for FastAPI P2 write services.

Characterization tests that exercise each write service family through direct
service calls (route-equivalent) using a bare SessionLocal-style session with
**no** Streamlit ``before_flush`` hook and **no** ``active_company_id`` ambient.

See ``docs/P2_HARDEN_01_COMPANY_STAMP_AUDIT.md`` §5–6 (H-01).
"""

from __future__ import annotations

import datetime
import sys
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import models
from db import Base
from reconciliation.company_card import post_credit_card_bill_payment
from registry.categories_seed import seed_default_categories_for_company
from registry.coa_seed import ensure_accounts_for_company, seed_chart_of_accounts_for_company
from registry.service import set_setting
from services import commit_modes
from services import posting
from services import write_banking
from services import write_closing
from services import write_expenses
from services import write_partner_worker
from services import write_purchases
from services import write_receivable_payments
from services import write_reconciliation
from services import write_sales
from services import write_voids

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

POST_DATE = datetime.date(2026, 6, 5)
AMOUNT = 100.0
CURRENCY = "TRY"
PAST_YEAR = datetime.date.today().year - 1
P_START = datetime.date(PAST_YEAR, 1, 1)
P_END = datetime.date(PAST_YEAR, 1, 31)
MID = datetime.date(PAST_YEAR, 1, 15)

# ORM types that must carry explicit company_id on every row created by a write.
STAMP_MODELS: tuple[type, ...] = (
    models.Sale,
    models.ExpenseRecord,
    models.Purchase,
    models.Payable,
    models.BankTransaction,
    models.PartnerMovement,
    models.WorkerMovement,
    models.PartnerProfitAllocation,
    models.JournalEntry,
    models.JournalEntryLine,
    models.AuditLog,
)


@pytest.fixture(autouse=True)
def _reset_commit_modes():
    commit_modes.reset_commit_modes_for_tests()
    yield
    commit_modes.reset_commit_modes_for_tests()


@pytest.fixture()
def api_session_factory():
    """API-style session factory — intentionally no before_flush stamp hook."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db(api_session_factory):
    with api_session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
def _no_streamlit_ambient():
    """Fixtures must not rely on active_company_id / session_state stamping."""
    st = sys.modules.get("streamlit")
    if st is not None:
        st.session_state.clear()
    yield
    if st is not None:
        assert "active_company_id" not in st.session_state


@pytest.fixture()
def env(db: Session) -> dict[str, Any]:
    """Two-company seed with explicit ORM company_id — no Streamlit ambient."""
    owner = models.User(
        username="owner_h01",
        display_name="Owner H01",
        password_hash="hash",
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_a = models.Company(
        name="Co A H01",
        slug="co_a_h01",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_b = models.Company(
        name="Co B H01",
        slug="co_b_h01",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add_all([owner, co_a, co_b])
    db.flush()

    for cid in (co_a.id, co_b.id):
        seed_chart_of_accounts_for_company(db, cid)
        seed_default_categories_for_company(db, cid)
        ensure_accounts_for_company(db, cid)

    set_setting(db, "banking.bank_charges_enabled", True, company_id=co_a.id)
    set_setting(db, "banking.company_card_enabled", True, company_id=co_a.id)

    bank_a = models.BankAccount(
        name="Bank A",
        currency=CURRENCY,
        company_id=co_a.id,
        is_active=True,
        balance=10_000.0,
        kind="bank",
    )
    bank_b = models.BankAccount(
        name="Bank B",
        currency=CURRENCY,
        company_id=co_b.id,
        is_active=True,
        balance=10_000.0,
        kind="bank",
    )
    cc_a = models.BankAccount(
        name="CC A",
        currency=CURRENCY,
        company_id=co_a.id,
        is_active=True,
        balance=500.0,
        kind="credit_card",
    )
    vendor = models.Vendor(name="Vendor H01", company_id=co_a.id, is_active=True)
    db.add_all([bank_a, bank_b, cc_a, vendor])
    db.flush()

    office_cat = (
        db.query(models.TransactionCategory)
        .filter_by(company_id=co_a.id, transaction_type="Expense", name="Office")
        .one()
    )
    inv_cat = (
        db.query(models.TransactionCategory)
        .filter_by(company_id=co_a.id, transaction_type="Purchase", name="Inventory")
        .one()
    )
    stock_sub = (
        db.query(models.TransactionSubcategory)
        .filter_by(category_id=inv_cat.id, name="General Stock")
        .one()
    )
    db.commit()

    return {
        "company_id": co_a.id,
        "other_company_id": co_b.id,
        "user_id": owner.id,
        "bank_a_id": bank_a.id,
        "bank_b_id": bank_b.id,
        "cc_a_id": cc_a.id,
        "vendor_id": vendor.id,
        "expense_category_id": office_cat.id,
        "purchase_category_id": inv_cat.id,
        "purchase_subcategory_id": stock_sub.id,
    }


# ── Snapshot / assertion helpers ─────────────────────────────────────────────


def _ids(session: Session, model: type) -> set[int]:
    return {row.id for row in session.query(model).all()}


def _snapshot_baseline(session: Session) -> dict[str, set[int]]:
    return {model.__tablename__: _ids(session, model) for model in STAMP_MODELS}


def _delta_rows(session: Session, baseline: dict[str, set[int]], model: type) -> list:
    before = baseline[model.__tablename__]
    return [row for row in session.query(model).all() if row.id not in before]


def _assert_matrix(
    session: Session,
    baseline: dict[str, set[int]],
    company_id: int,
    other_company_id: int,
) -> None:
    """Every ORM row created by the write must carry explicit company_id == header company."""
    for model in STAMP_MODELS:
        for row in _delta_rows(session, baseline, model):
            cid = getattr(row, "company_id", None)
            assert cid is not None, f"{model.__name__}#{row.id} has NULL company_id"
            assert cid == company_id, (
                f"{model.__name__}#{row.id} company_id={cid} "
                f"expected {company_id} (other={other_company_id})"
            )


# ── ORM seed helpers (no Streamlit / no before_flush) ───────────────────────


def _seed_partner_orm(db: Session, company_id: int, *, name: str = "Alice") -> int:
    cap = models.ChartOfAccounts(
        account_code=f"351{company_id}",
        account_name=f"{name} Capital",
        account_type="Equity",
        balance=0.0,
        is_active=True,
        company_id=company_id,
    )
    cur = models.ChartOfAccounts(
        account_code=f"361{company_id}",
        account_name=f"{name} Current",
        account_type="Equity",
        balance=0.0,
        is_active=True,
        company_id=company_id,
    )
    adv = models.ChartOfAccounts(
        account_code=f"151{company_id}",
        account_name=f"{name} Advances",
        account_type="Asset",
        balance=0.0,
        is_active=True,
        company_id=company_id,
    )
    db.add_all([cap, cur, adv])
    db.flush()
    partner = models.Partner(
        name=name,
        profit_share_pct=100.0,
        capital_account_id=cap.id,
        current_account_id=cur.id,
        advance_account_id=adv.id,
        is_active=True,
        company_id=company_id,
        created_at=datetime.datetime.now(),
    )
    db.add(partner)
    db.commit()
    return partner.id


def _seed_worker_orm(db: Session, company_id: int, *, name: str = "Bob") -> int:
    worker = models.Worker(
        name=name,
        is_active=True,
        company_id=company_id,
        created_at=datetime.datetime.now(),
    )
    db.add(worker)
    db.commit()
    return worker.id


def _stmt_row(
    db: Session,
    *,
    company_id: int,
    bank_account_id: int,
    credit: bool = True,
    amount: float = AMOUNT,
    description: str = "H01 stmt row",
) -> models.BankStatementRow:
    imp = models.BankStatementImport(
        company_id=company_id,
        bank_account_id=bank_account_id,
        file_name="h01.csv",
        file_hash="h01-hash",
        file_size=10,
        file_path="/tmp/h01.csv",
        status="staging",
        import_date=POST_DATE,
        row_count=1,
        valid_count=1,
        flagged_count=0,
        error_count=0,
        currency=CURRENCY,
        created_at=datetime.datetime.now(),
    )
    db.add(imp)
    db.flush()
    row = models.BankStatementRow(
        bank_statement_import_id=imp.id,
        status="staging",
        import_row_index=1,
        date=POST_DATE,
        description=description,
        debit_amount=None if credit else amount,
        credit_amount=amount if credit else None,
        amount=amount,
        currency=CURRENCY,
        original_amount=amount,
        parsed_successfully=True,
        created_at=datetime.datetime.now(),
    )
    db.add(row)
    db.commit()
    return row


def _acct_id(db: Session, company_id: int, name: str) -> int:
    acct = posting.get_account_by_name(db, name, company_id=company_id)
    assert acct is not None, f"Account {name!r} missing for company {company_id}"
    return acct.id


def _open_period(
    db: Session,
    company_id: int,
    *,
    revenue: float = 1000.0,
    expense: float = 600.0,
) -> models.FiscalPeriod:
    period = models.FiscalPeriod(
        name=f"Jan {PAST_YEAR}",
        start_date=P_START,
        end_date=P_END,
        is_closed=False,
        company_id=company_id,
    )
    db.add(period)
    db.flush()
    cash_id = _acct_id(db, company_id, "Cash")
    inc_id = _acct_id(db, company_id, "Sales Revenue")
    exp_id = _acct_id(db, company_id, "Rent Expense")
    if revenue:
        posting.create_journal_entry(
            db,
            MID,
            "H01 revenue pin",
            "Sale",
            None,
            [(cash_id, revenue, 0.0), (inc_id, 0.0, revenue)],
            company_id=company_id,
        )
    if expense:
        posting.create_journal_entry(
            db,
            MID,
            "H01 expense pin",
            "Expense",
            None,
            [(exp_id, expense, 0.0), (cash_id, 0.0, expense)],
            company_id=company_id,
        )
    db.commit()
    return period


# ── Write-family invokers (direct service calls, route-equivalent) ───────────


def _invoke_sales(db: Session, env: dict[str, Any]) -> None:
    write_sales.create_and_post_sale(
        db,
        company_id=env["company_id"],
        user_id=env["user_id"],
        performed_by="h01",
        entry_date=POST_DATE,
        amount=AMOUNT,
        currency=CURRENCY,
        payment_method="Cash",
        notes="h01 sales",
    )


def _invoke_expenses(db: Session, env: dict[str, Any]) -> None:
    write_expenses.create_and_post_expense(
        db,
        company_id=env["company_id"],
        user_id=env["user_id"],
        performed_by="h01",
        entry_date=POST_DATE,
        amount=AMOUNT,
        currency=CURRENCY,
        payment_method="Cash",
        category_id=env["expense_category_id"],
        notes="h01 expense",
    )


def _invoke_purchases(db: Session, env: dict[str, Any]) -> None:
    write_purchases.create_and_post_purchase(
        db,
        company_id=env["company_id"],
        user_id=env["user_id"],
        performed_by="h01",
        entry_date=POST_DATE,
        amount=AMOUNT,
        currency=CURRENCY,
        payment_method="Cash",
        vendor_id=env["vendor_id"],
        category_id=env["purchase_category_id"],
        subcategory_id=env["purchase_subcategory_id"],
        notes="h01 purchase",
    )


def _invoke_receivable_payments(db: Session, env: dict[str, Any]) -> None:
    sale = write_sales.create_and_post_sale(
        db,
        company_id=env["company_id"],
        user_id=env["user_id"],
        performed_by="h01",
        entry_date=POST_DATE,
        amount=AMOUNT,
        currency=CURRENCY,
        payment_method="Credit",
        customer_name="Credit Customer H01",
        notes="h01 credit sale",
    )
    write_receivable_payments.record_receivable_payment(
        db,
        company_id=env["company_id"],
        performed_by="h01",
        entry_date=POST_DATE,
        amount=50.0,
        currency=CURRENCY,
        payment_method="Cash",
        sale_id=sale.sale_id,
        notes="h01 receivable payment",
    )


def _invoke_voids(db: Session, env: dict[str, Any]) -> None:
    sale = write_sales.create_and_post_sale(
        db,
        company_id=env["company_id"],
        user_id=env["user_id"],
        performed_by="h01",
        entry_date=POST_DATE,
        amount=AMOUNT,
        currency=CURRENCY,
        payment_method="Cash",
        notes="h01 void target",
    )
    write_voids.void_record(
        db,
        company_id=env["company_id"],
        performed_by="h01",
        target_type="Sale",
        target_id=sale.sale_id,
        reason="h01 void test",
    )


def _invoke_partner_movements(db: Session, env: dict[str, Any]) -> None:
    partner_id = _seed_partner_orm(db, env["company_id"])
    write_partner_worker.post_partner_movement_record(
        db,
        company_id=env["company_id"],
        performed_by="h01",
        created_by_id=env["user_id"],
        partner_id=partner_id,
        movement_type="CapitalContribution",
        amount=AMOUNT,
        entry_date=POST_DATE,
        bank_account_id=env["bank_a_id"],
        notes="h01 partner movement",
    )


def _invoke_worker_payments(db: Session, env: dict[str, Any]) -> None:
    worker_id = _seed_worker_orm(db, env["company_id"])
    write_partner_worker.post_worker_payment_record(
        db,
        company_id=env["company_id"],
        performed_by="h01",
        created_by_id=env["user_id"],
        worker_id=worker_id,
        movement_type="Advance",
        entry_date=POST_DATE,
        bank_account_id=env["bank_a_id"],
        amount=AMOUNT,
        notes="h01 worker payment",
    )


def _invoke_bank_transactions(db: Session, env: dict[str, Any]) -> None:
    dest = models.BankAccount(
        name="Dest Bank H01",
        currency=CURRENCY,
        company_id=env["company_id"],
        is_active=True,
        balance=0.0,
        kind="bank",
    )
    db.add(dest)
    db.commit()
    write_banking.create_manual_bank_transaction(
        db,
        company_id=env["company_id"],
        performed_by="h01",
        entry_date=POST_DATE,
        amount=AMOUNT,
        transaction_type="transfer",
        bank_account_id=env["bank_a_id"],
        destination_bank_account_id=dest.id,
        notes="h01 transfer",
    )


def _invoke_recon_match(db: Session, env: dict[str, Any]) -> None:
    row = _stmt_row(
        db,
        company_id=env["company_id"],
        bank_account_id=env["bank_a_id"],
    )
    write_reconciliation.match_statement_row(
        db,
        company_id=env["company_id"],
        user_id=env["user_id"],
        performed_by="h01",
        statement_row_id=row.id,
        match_type="generic_deposit",
        credit_account_name="Sales Revenue",
    )


def _invoke_recon_unmatch(db: Session, env: dict[str, Any]) -> None:
    row = _stmt_row(
        db,
        company_id=env["company_id"],
        bank_account_id=env["bank_a_id"],
        credit=False,
        amount=250.0,
        description="KK ODEME H01",
    )
    post_credit_card_bill_payment(
        db,
        row_id=row.id,
        company_id=env["company_id"],
        credit_card_account_id=env["cc_a_id"],
        user_id=env["user_id"],
    )
    write_reconciliation.unmatch_statement_row(
        db,
        company_id=env["company_id"],
        performed_by="h01",
        statement_row_id=row.id,
        reason="h01 unmatch",
    )


def _invoke_closing(db: Session, env: dict[str, Any]) -> None:
    _seed_partner_orm(db, env["company_id"], name="Closing Partner")
    period = _open_period(db, env["company_id"])
    write_closing.close_period(
        db,
        company_id=env["company_id"],
        performed_by="h01",
        period_id=period.id,
    )
    write_closing.allocate(
        db,
        company_id=env["company_id"],
        performed_by="h01",
        allocated_by_id=env["user_id"],
        period_id=period.id,
        notes="h01 allocation",
    )


WRITE_FAMILY_INVOKERS: dict[str, Callable[[Session, dict[str, Any]], None]] = {
    "sales": _invoke_sales,
    "expenses": _invoke_expenses,
    "purchases": _invoke_purchases,
    "receivable_payments": _invoke_receivable_payments,
    "voids": _invoke_voids,
    "partner_movements": _invoke_partner_movements,
    "worker_payments": _invoke_worker_payments,
    "bank_transactions": _invoke_bank_transactions,
    "recon_match": _invoke_recon_match,
    "recon_unmatch": _invoke_recon_unmatch,
    "closing": _invoke_closing,
}


# ── Contract tests ───────────────────────────────────────────────────────────


class TestApiSessionContract:
    def test_session_factory_has_no_before_flush_hook(self, api_session_factory):
        """Ambient active_company_id must not auto-stamp rows — real API has no hook."""
        st = sys.modules["streamlit"]
        st.session_state["active_company_id"] = 99_999
        try:
            with api_session_factory() as session:
                sale = models.Sale(
                    date=POST_DATE,
                    invoice_number="H01-HOOK-PROBE",
                    customer_name="Probe",
                    description="",
                    amount=1.0,
                    sale_type="Cash",
                    paid_amount=1.0,
                    balance=0.0,
                    due_date=POST_DATE,
                    status="Paid",
                    company_id=None,
                )
                session.add(sale)
                session.flush()
                assert sale.company_id is None, (
                    "before_flush hook stamped company_id from ambient session_state"
                )
        finally:
            st.session_state.pop("active_company_id", None)

    def test_ambient_company_id_absent_during_fixture(self):
        st = sys.modules.get("streamlit")
        assert st is not None
        assert "active_company_id" not in st.session_state


# ── Company stamp matrix ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "family",
    list(WRITE_FAMILY_INVOKERS.keys()),
    ids=list(WRITE_FAMILY_INVOKERS.keys()),
)
def test_write_family_stamps_company_id_without_streamlit_hook(
    db: Session, env: dict[str, Any], family: str
):
    baseline = _snapshot_baseline(db)
    WRITE_FAMILY_INVOKERS[family](db, env)
    _assert_matrix(db, baseline, env["company_id"], env["other_company_id"])


class TestCrossCompanyIsolation:
    def test_other_company_rows_unchanged_after_sales_write(
        self, db: Session, env: dict[str, Any]
    ):
        co_b = env["other_company_id"]
        before_b_jes = {
            row.id
            for row in db.query(models.JournalEntry).filter_by(company_id=co_b).all()
        }
        before_b_btx = {
            row.id
            for row in db.query(models.BankTransaction).filter_by(company_id=co_b).all()
        }
        _invoke_sales(db, env)
        new_b_jes = [
            row
            for row in db.query(models.JournalEntry).filter_by(company_id=co_b).all()
            if row.id not in before_b_jes
        ]
        new_b_btx = [
            row
            for row in db.query(models.BankTransaction).filter_by(company_id=co_b).all()
            if row.id not in before_b_btx
        ]
        assert not new_b_jes
        assert not new_b_btx

    def test_wrong_company_partner_rejected_without_co_b_mutation(
        self, db: Session, env: dict[str, Any]
    ):
        other_partner = _seed_partner_orm(db, env["other_company_id"], name="Other Co")
        before = _snapshot_baseline(db)
        with pytest.raises(ValueError, match="Partner not found"):
            write_partner_worker.post_partner_movement_record(
                db,
                company_id=env["company_id"],
                performed_by="h01",
                created_by_id=env["user_id"],
                partner_id=other_partner,
                movement_type="CapitalContribution",
                amount=AMOUNT,
                entry_date=POST_DATE,
                bank_account_id=env["bank_a_id"],
            )
        for model in STAMP_MODELS:
            assert _delta_rows(db, before, model) == []
