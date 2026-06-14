"""FASTAPI-P0.5a — posting result DTO contract tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event, func
from sqlalchemy.orm import sessionmaker

import app as erp_app
from db import Base
import models
from services import posting

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    _seed_dev_auth_user()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        co = models.Company(
            name="DTO Co",
            slug="dto_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        yield s, co.id


def _accounts(db, company_id):
    cash = models.ChartOfAccounts(
        account_code="1000",
        account_name="Cash",
        account_type="Asset",
        balance=0.0,
        is_active=True,
        company_id=company_id,
    )
    income = models.ChartOfAccounts(
        account_code="4000",
        account_name="Sales Revenue",
        account_type="Income",
        balance=0.0,
        is_active=True,
        company_id=company_id,
    )
    db.add_all([cash, income])
    db.commit()
    return cash, income


def _counts(db):
    return (
        db.query(func.count()).select_from(models.JournalEntry).scalar(),
        db.query(func.count()).select_from(models.BankTransaction).scalar(),
    )


class TestPostingResult:
    def test_mirrors_journal_entry(self, db):
        session, cid = db
        cash, income = _accounts(session, cid)
        entry = posting.create_journal_entry(
            session,
            datetime.date(2026, 6, 1),
            "Cash Sale (ID: 1)",
            "CashSale",
            1,
            [(cash.id, 100.0, 0), (income.id, 0, 100.0)],
            currency="TRY",
            company_id=cid,
        )
        assert isinstance(entry, models.JournalEntry)
        dto = posting.posting_result_from_entry(session, entry, currency="TRY")
        assert dto.je_id == entry.id
        assert dto.reference_type == "CashSale"
        assert dto.reference_id == 1
        assert dto.entry_date == datetime.date(2026, 6, 1)
        assert dto.company_id == cid
        assert dto.currency == "TRY"
        assert len(dto.lines) == 2
        assert dto.lines[0].account_id == cash.id
        assert dto.lines[0].debit == 100.0
        assert dto.lines[0].credit == 0.0
        assert dto.lines[1].account_id == income.id
        assert dto.lines[1].debit == 0.0
        assert dto.lines[1].credit == 100.0

    def test_to_dict_stable(self, db):
        session, cid = db
        cash, income = _accounts(session, cid)
        entry = posting.create_journal_entry(
            session,
            datetime.date(2026, 6, 2),
            "Test",
            "Sale",
            9,
            [(cash.id, 50.0, 0), (income.id, 0, 50.0)],
            company_id=cid,
        )
        dto = posting.posting_result_from_entry(session, entry)
        d1 = dto.to_dict()
        d2 = dto.to_dict()
        assert d1 == d2
        assert d1["je_id"] == entry.id
        assert d1["lines"] == [
            {
                "account_id": cash.id,
                "debit": 50.0,
                "credit": 0.0,
                "currency": None,
                "amount_native": None,
            },
            {
                "account_id": income.id,
                "debit": 0.0,
                "credit": 50.0,
                "currency": None,
                "amount_native": None,
            },
        ]

    def test_legacy_create_journal_entry_still_returns_orm(self, db):
        session, cid = db
        cash, income = _accounts(session, cid)
        entry = posting.create_journal_entry(
            session,
            datetime.date(2026, 6, 3),
            "Legacy",
            "Expense",
            2,
            [(cash.id, 10.0, 0), (income.id, 0, 10.0)],
            company_id=cid,
        )
        assert isinstance(entry, models.JournalEntry)
        assert session.get(models.JournalEntry, entry.id) is not None

    def test_dto_helpers_create_no_extra_jes(self, db):
        session, cid = db
        cash, income = _accounts(session, cid)
        je_before, bt_before = _counts(session)
        entry = posting.create_journal_entry(
            session,
            datetime.date(2026, 6, 4),
            "No extra",
            "Sale",
            3,
            [(cash.id, 25.0, 0), (income.id, 0, 25.0)],
            company_id=cid,
        )
        posting.posting_result_from_entry(session, entry)
        je_after, bt_after = _counts(session)
        assert je_after == je_before + 1
        assert bt_after == bt_before


class TestPeriodCloseResult:
    def test_from_close_fiscal_period(self, db):
        session, cid = db
        re_acct = models.ChartOfAccounts(
            account_code="3100",
            account_name="Retained Earnings",
            account_type="Equity",
            balance=0.0,
            is_active=True,
            company_id=cid,
        )
        inc = models.ChartOfAccounts(
            account_code="4000",
            account_name="Revenue",
            account_type="Income",
            balance=0.0,
            is_active=True,
            company_id=cid,
        )
        cash = models.ChartOfAccounts(
            account_code="1000",
            account_name="Cash",
            account_type="Asset",
            balance=0.0,
            is_active=True,
            company_id=cid,
        )
        session.add_all([re_acct, inc, cash])
        session.flush()
        period = models.FiscalPeriod(
            name="Jun 2026",
            start_date=datetime.date(2026, 6, 1),
            end_date=datetime.date(2026, 6, 30),
            is_closed=False,
        )
        session.add(period)
        session.commit()
        posting.create_journal_entry(
            session,
            datetime.date(2026, 6, 15),
            "Sale",
            "Sale",
            1,
            [(cash.id, 500.0, 0), (inc.id, 0, 500.0)],
            company_id=cid,
        )
        je = posting.close_fiscal_period(session, period.id, company_id=cid)
        assert isinstance(je, models.JournalEntry)
        session.refresh(period)
        dto = posting.period_close_result_from_je(je, period, net_income=500.0)
        assert dto.je_id == je.id
        assert dto.period_id == period.id
        assert dto.closing_je_id == period.closing_je_id
        assert dto.net_income == 500.0
        assert dto.to_dict()["closing_je_id"] == je.id


class TestAllocationAndYearEndResults:
    def test_allocation_result_from_post(self, db):
        session, cid = db
        re_acct = models.ChartOfAccounts(
            account_code="3100",
            account_name="Retained Earnings",
            account_type="Equity",
            balance=0.0,
            is_active=True,
            company_id=cid,
        )
        cur = models.ChartOfAccounts(
            account_code="3601",
            account_name="Partner Current",
            account_type="Equity",
            balance=0.0,
            is_active=True,
            company_id=cid,
        )
        session.add_all([re_acct, cur])
        session.flush()
        partner = models.Partner(
            name="Pat",
            profit_share_pct=100.0,
            current_account_id=cur.id,
            is_active=True,
            created_at=datetime.datetime.now(),
            company_id=cid,
        )
        session.add(partner)
        session.flush()
        period = models.FiscalPeriod(
            name="Q1",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 3, 31),
            is_closed=True,
            closed_at=datetime.date.today(),
        )
        session.add(period)
        session.flush()
        posting.create_journal_entry(
            session,
            datetime.date(2026, 3, 31),
            f"Period Close: {period.name}",
            "PeriodClose",
            period.id,
            [(re_acct.id, 0, 200.0), (cur.id, 200.0, 0)],
            company_id=cid,
        )
        period.closing_je_id = (
            session.query(models.JournalEntry)
            .filter_by(reference_type="PeriodClose", reference_id=period.id)
            .one()
            .id
        )
        session.commit()
        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, allocated_by_id=1, company_id=cid
        )
        assert err == ""
        legacy = (alloc_id, err)
        dto = posting.allocation_result_from_post(session, alloc_id, err)
        assert dto.allocation_id == alloc_id
        assert dto.error == ""
        assert dto.je_id is not None
        assert len(dto.per_partner) == 1
        assert legacy[0] == dto.allocation_id
        assert legacy[1] == dto.error

    def test_year_end_close_result_from_tuple(self):
        dto = posting.year_end_close_result_from_tuple(
            42,
            [("re_residual", "RE balance")],
            "",
        )
        assert dto.yec_id == 42
        assert dto.warnings == (("re_residual", "RE balance"),)
        assert dto.error == ""
        assert dto.to_dict() == {
            "yec_id": 42,
            "warnings": [["re_residual", "RE balance"]],
            "error": "",
        }


class TestVoidAndPaymentResults:
    def test_void_result_from_expense_void(self, db):
        session, cid = db
        exp_acct = models.ChartOfAccounts(
            account_code="5000",
            account_name="Office Expense",
            account_type="Expense",
            balance=0.0,
            is_active=True,
            company_id=cid,
        )
        cash = models.ChartOfAccounts(
            account_code="1000",
            account_name="Cash",
            account_type="Asset",
            balance=0.0,
            is_active=True,
            company_id=cid,
        )
        session.add_all([exp_acct, cash])
        session.flush()
        expense = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="General",
            category="Office",
            description="DTO test expense",
            amount=75.0,
            payment_method="Cash",
            is_void=False,
            company_id=cid,
        )
        session.add(expense)
        session.flush()
        posting.create_journal_entry(
            session,
            expense.date,
            "Expense",
            "Expense",
            expense.id,
            [(exp_acct.id, 75.0, 0), (cash.id, 0, 75.0)],
            company_id=cid,
        )
        session.commit()
        voided = posting.void_expense(session, expense.id, "test void", company_id=cid)
        assert voided is True
        dto = posting.void_result_from_expense_void(
            session, expense.id, voided, void_reason="test void", company_id=cid
        )
        assert dto.voided is True
        assert len(dto.reversal_je_ids) >= 1
        assert posting.void_result_from_bool(False).voided is False

    def test_payment_result_from_receivable_post(self, db):
        session, cid = db
        ar = models.ChartOfAccounts(
            account_code="1200",
            account_name="Accounts Receivable",
            account_type="Asset",
            balance=0.0,
            is_active=True,
            company_id=cid,
        )
        cash = models.ChartOfAccounts(
            account_code="1100",
            account_name="Cash",
            account_type="Asset",
            balance=0.0,
            is_active=True,
            company_id=cid,
        )
        session.add_all([ar, cash])
        session.flush()
        sale = models.Sale(
            invoice_number="INV-1",
            customer_name="Acme",
            sale_type="Credit",
            date=datetime.date.today(),
            amount=100.0,
            paid_amount=0.0,
            balance=100.0,
            status="Open",
            company_id=cid,
        )
        session.add(sale)
        session.commit()
        err = posting.post_receivable_payment(
            session, sale.id, 40.0, datetime.date.today(), company_id=cid
        )
        assert err is None
        session.refresh(sale)
        dto = posting.payment_result_from_receivable_post(
            session, sale.id, applied_amount=40.0
        )
        assert dto.error == ""
        assert dto.je_id is not None
        assert dto.applied_amount == 40.0
        assert dto.sale_balance_after == sale.balance
