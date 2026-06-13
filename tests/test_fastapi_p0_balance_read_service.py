"""FASTAPI-P0.2-A — balance read service contract tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app as erp_app
from db import Base
import models
from services import read_balances as rb

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

_ACCOUNT_TYPES = ("Asset", "Liability", "Equity", "Income", "Expense")


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


def _company(db, name="Acme", slug="co1"):
    c = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(c)
    db.flush()
    return c


def _account(db, company_id, code, name, acct_type):
    a = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        is_active=True,
        balance=0.0,
        company_id=company_id,
    )
    db.add(a)
    db.flush()
    return a


def _journal_entry(
    db,
    company_id,
    account_id,
    *,
    debit=0.0,
    credit=0.0,
    date=datetime.date(2026, 1, 15),
    reference_type="Sale",
):
    je = models.JournalEntry(
        entry_date=date,
        description="Test JE",
        reference_type=reference_type,
        reference_id=1,
        company_id=company_id,
    )
    db.add(je)
    db.flush()
    jel = models.JournalEntryLine(
        journal_entry_id=je.id,
        account_id=account_id,
        debit=debit,
        credit=credit,
        company_id=company_id,
    )
    db.add(jel)
    db.flush()
    return je, jel


def _set_company(company_id: int | None):
    if company_id is None:
        sys.modules["streamlit"].session_state.pop("active_company_id", None)
    else:
        sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _counts(db):
    return (
        db.query(models.JournalEntry).count(),
        db.query(models.BankTransaction).count(),
    )


@pytest.fixture()
def seeded_balances(db):
    co_a = _company(db, "Alpha", "alpha")
    co_b = _company(db, "Beta", "beta")
    accounts = {}
    for idx, acct_type in enumerate(_ACCOUNT_TYPES, start=1):
        accounts[acct_type] = _account(
            db,
            co_a.id,
            f"{1000 + idx}",
            f"{acct_type} Acct",
            acct_type,
        )
    cash_b = _account(db, co_b.id, "1000", "Cash B", "Asset")

    _journal_entry(db, co_a.id, accounts["Asset"].id, debit=100.0, credit=0.0)
    _journal_entry(db, co_a.id, accounts["Liability"].id, debit=0.0, credit=40.0)
    _journal_entry(db, co_a.id, accounts["Equity"].id, debit=0.0, credit=25.0)
    _journal_entry(db, co_a.id, accounts["Income"].id, debit=0.0, credit=80.0)
    _journal_entry(db, co_a.id, accounts["Expense"].id, debit=30.0, credit=0.0)

    _journal_entry(
        db,
        co_a.id,
        accounts["Asset"].id,
        debit=50.0,
        credit=0.0,
        date=datetime.date(2026, 2, 10),
    )
    _journal_entry(
        db,
        co_a.id,
        accounts["Asset"].id,
        debit=20.0,
        credit=0.0,
        date=datetime.date(2025, 12, 31),
        reference_type="PeriodClose",
    )
    _journal_entry(db, co_b.id, cash_b.id, debit=999.0, credit=0.0)

    db.commit()
    return co_a, co_b, accounts, cash_b


class TestServiceMatchesAppShim:
    @pytest.mark.parametrize("acct_type", _ACCOUNT_TYPES)
    def test_all_time_balance_matches_app(self, db, seeded_balances, acct_type):
        co_a, _co_b, accounts, _cash_b = seeded_balances
        _set_company(co_a.id)
        acct = accounts[acct_type]

        app_bal = erp_app.calculate_account_balance(db, acct)
        svc_bal = rb.calculate_account_balance(db, acct, company_id=co_a.id)
        assert svc_bal == pytest.approx(app_bal)

    @pytest.mark.parametrize("acct_type", _ACCOUNT_TYPES)
    def test_period_balance_matches_app(self, db, seeded_balances, acct_type):
        co_a, _co_b, accounts, _cash_b = seeded_balances
        _set_company(co_a.id)
        acct = accounts[acct_type]
        start = datetime.date(2026, 1, 1)
        end = datetime.date(2026, 1, 31)

        app_bal = erp_app.calculate_account_balance_for_period(
            db, acct, start, end,
        )
        svc_bal = rb.calculate_account_balance_for_period(
            db, acct, start, end, company_id=co_a.id,
        )
        assert svc_bal == pytest.approx(app_bal)


class TestSignConventions:
    def test_asset_expense_debit_minus_credit(self, db, seeded_balances):
        co_a, _co_b, accounts, _cash_b = seeded_balances
        assert rb.calculate_account_balance(
            db, accounts["Asset"], company_id=co_a.id,
        ) == pytest.approx(170.0)
        assert rb.calculate_account_balance(
            db, accounts["Expense"], company_id=co_a.id,
        ) == pytest.approx(30.0)

    def test_liability_equity_income_credit_minus_debit(self, db, seeded_balances):
        co_a, _co_b, accounts, _cash_b = seeded_balances
        assert rb.calculate_account_balance(
            db, accounts["Liability"], company_id=co_a.id,
        ) == pytest.approx(40.0)
        assert rb.calculate_account_balance(
            db, accounts["Equity"], company_id=co_a.id,
        ) == pytest.approx(25.0)
        assert rb.calculate_account_balance(
            db, accounts["Income"], company_id=co_a.id,
        ) == pytest.approx(80.0)


class TestPeriodFiltering:
    def test_includes_only_dates_in_range(self, db, seeded_balances):
        co_a, _co_b, accounts, _cash_b = seeded_balances
        jan_bal = rb.calculate_account_balance_for_period(
            db,
            accounts["Asset"],
            datetime.date(2026, 1, 1),
            datetime.date(2026, 1, 31),
            company_id=co_a.id,
        )
        feb_bal = rb.calculate_account_balance_for_period(
            db,
            accounts["Asset"],
            datetime.date(2026, 2, 1),
            datetime.date(2026, 2, 28),
            company_id=co_a.id,
        )
        assert jan_bal == pytest.approx(100.0)
        assert feb_bal == pytest.approx(50.0)


class TestExcludeRefs:
    def test_excludes_reference_types(self, db, seeded_balances):
        co_a, _co_b, accounts, _cash_b = seeded_balances
        _set_company(co_a.id)
        start = datetime.date(2025, 12, 1)
        end = datetime.date(2026, 2, 28)

        without = rb.calculate_account_balance_for_period(
            db, accounts["Asset"], start, end, company_id=co_a.id,
        )
        with_excl = rb.calculate_account_balance_for_period(
            db,
            accounts["Asset"],
            start,
            end,
            exclude_refs=["PeriodClose"],
            company_id=co_a.id,
        )
        app_with_excl = erp_app.calculate_account_balance_for_period(
            db,
            accounts["Asset"],
            start,
            end,
            exclude_refs=["PeriodClose"],
        )

        assert without == pytest.approx(170.0)
        assert with_excl == pytest.approx(app_with_excl)
        assert with_excl == pytest.approx(150.0)


class TestCompanyIsolation:
    def test_explicit_company_id_ignores_other_company(self, db, seeded_balances):
        co_a, co_b, accounts, cash_b = seeded_balances
        bal_a = rb.calculate_account_balance(
            db, accounts["Asset"], company_id=co_a.id,
        )
        bal_b = rb.calculate_account_balance(
            db, cash_b, company_id=co_b.id,
        )
        cross = rb.calculate_account_balance(
            db, accounts["Asset"], company_id=co_b.id,
        )
        assert bal_a == pytest.approx(170.0)
        assert bal_b == pytest.approx(999.0)
        assert cross == pytest.approx(0.0)

    def test_none_company_id_matches_startup_path(self, db, seeded_balances):
        co_a, _co_b, accounts, _cash_b = seeded_balances
        _set_company(None)
        app_bal = erp_app.calculate_account_balance(db, accounts["Asset"])
        svc_bal = rb.calculate_account_balance(db, accounts["Asset"], company_id=None)
        assert svc_bal == pytest.approx(app_bal)


class TestReadOnly:
    def test_balance_reads_create_no_rows(self, db, seeded_balances):
        co_a, _co_b, accounts, _cash_b = seeded_balances
        je_before, bt_before = _counts(db)

        rb.calculate_account_balance(db, accounts["Asset"], company_id=co_a.id)
        rb.calculate_account_balance_for_period(
            db,
            accounts["Asset"],
            datetime.date(2026, 1, 1),
            datetime.date(2026, 1, 31),
            exclude_refs=["PeriodClose"],
            company_id=co_a.id,
        )

        je_after, bt_after = _counts(db)
        assert je_after == je_before
        assert bt_after == bt_before
