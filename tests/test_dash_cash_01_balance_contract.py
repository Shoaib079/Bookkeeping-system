"""DASH-CASH-01-S1 — GL liquid position read helper contract tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services import read_balances as rb
from services import read_reports as rr

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

_CASH_CODES = frozenset({"1000", "1001", "1002", "1003"})
_BANK_CODES = frozenset({"1010", "1011", "1012", "1013"})


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


def _account(db, company_id, code, name, acct_type, *, currency=None):
    a = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        currency=currency,
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
    lines,
    *,
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
    for account_id, debit, credit in lines:
        db.add(
            models.JournalEntryLine(
                journal_entry_id=je.id,
                account_id=account_id,
                debit=debit,
                credit=credit,
                company_id=company_id,
            )
        )
    db.flush()
    return je


def _bs_liquid_totals(stmt):
    cash = sum(
        ln.amount for ln in stmt.asset_lines if ln.code in _CASH_CODES
    )
    bank = sum(
        ln.amount for ln in stmt.asset_lines if ln.code in _BANK_CODES
    )
    return round(cash, 2), round(bank, 2)


@pytest.fixture()
def liquid_seed(db):
    co_a = _company(db, "Alpha", "alpha")
    co_b = _company(db, "Beta", "beta")

    cash_try = _account(db, co_a.id, "1000", "Cash", "Asset", currency="TRY")
    cash_usd = _account(db, co_a.id, "1001", "Cash USD", "Asset", currency="USD")
    bank_try = _account(db, co_a.id, "1010", "Bank", "Asset", currency="TRY")
    bank_usd = _account(db, co_a.id, "1011", "Bank USD", "Asset", currency="USD")
    clearing = _account(db, co_a.id, "1150", "Card Sales Clearing", "Asset")
    cc_payable = _account(db, co_a.id, "2110", "Credit Card Payable", "Liability")
    income = _account(db, co_a.id, "4000", "Sales", "Income")

    cash_b = _account(db, co_b.id, "1000", "Cash", "Asset", currency="TRY")
    income_b = _account(db, co_b.id, "4000", "Sales B", "Income")

    _journal_entry(
        db,
        co_a.id,
        [(cash_try.id, 300.0, 0.0), (income.id, 0.0, 300.0)],
        date=datetime.date(2026, 1, 10),
    )
    _journal_entry(
        db,
        co_a.id,
        [(cash_usd.id, 150.0, 0.0), (income.id, 0.0, 150.0)],
        date=datetime.date(2026, 1, 12),
    )
    _journal_entry(
        db,
        co_a.id,
        [(bank_try.id, 500.0, 0.0), (income.id, 0.0, 500.0)],
        date=datetime.date(2026, 2, 1),
    )
    _journal_entry(
        db,
        co_a.id,
        [(bank_usd.id, 75.0, 0.0), (income.id, 0.0, 75.0)],
        date=datetime.date(2026, 2, 3),
    )
    _journal_entry(
        db,
        co_a.id,
        [(clearing.id, 999.0, 0.0), (income.id, 0.0, 999.0)],
        date=datetime.date(2026, 2, 5),
    )
    _journal_entry(
        db,
        co_a.id,
        [(cc_payable.id, 0.0, 888.0), (income.id, 888.0, 0.0)],
        date=datetime.date(2026, 2, 6),
    )
    _journal_entry(
        db,
        co_a.id,
        [(cash_try.id, 100.0, 0.0), (income.id, 0.0, 100.0)],
        date=datetime.date(2026, 3, 15),
    )
    _journal_entry(
        db,
        co_b.id,
        [(cash_b.id, 9000.0, 0.0), (income_b.id, 0.0, 9000.0)],
        date=datetime.date(2026, 1, 20),
    )

    db.commit()
    return co_a, co_b


class TestComputeLiquidPosition:
    def test_company_scoped(self, db, liquid_seed):
        co_a, co_b = liquid_seed
        as_of = datetime.date(2026, 2, 28)

        pos_a = rb.compute_liquid_position(db, company_id=co_a.id, as_of=as_of)
        pos_b = rb.compute_liquid_position(db, company_id=co_b.id, as_of=as_of)

        assert pos_a.cash_by_currency["TRY"] == pytest.approx(300.0)
        assert pos_b.cash_by_currency["TRY"] == pytest.approx(9000.0)
        assert "USD" not in pos_b.cash_by_currency
        assert "USD" not in pos_b.bank_by_currency

    def test_as_of_date_excludes_future_entries(self, db, liquid_seed):
        co_a, _co_b = liquid_seed

        feb = rb.compute_liquid_position(
            db, company_id=co_a.id, as_of=datetime.date(2026, 2, 28),
        )
        mar = rb.compute_liquid_position(
            db, company_id=co_a.id, as_of=datetime.date(2026, 3, 31),
        )

        assert feb.cash_by_currency["TRY"] == pytest.approx(300.0)
        assert mar.cash_by_currency["TRY"] == pytest.approx(400.0)
        assert feb.bank_by_currency["TRY"] == pytest.approx(500.0)
        assert mar.bank_by_currency["TRY"] == pytest.approx(500.0)

    def test_excludes_clearing_and_credit_card_payable(self, db, liquid_seed):
        co_a, _co_b = liquid_seed
        pos = rb.compute_liquid_position(
            db, company_id=co_a.id, as_of=datetime.date(2026, 2, 28),
        )

        assert sum(pos.cash_by_currency.values()) == pytest.approx(450.0)
        assert sum(pos.bank_by_currency.values()) == pytest.approx(575.0)
        assert pos.total_by_currency["TRY"] == pytest.approx(800.0)
        assert pos.total_by_currency["USD"] == pytest.approx(225.0)

    def test_split_by_currency(self, db, liquid_seed):
        co_a, _co_b = liquid_seed
        pos = rb.compute_liquid_position(
            db, company_id=co_a.id, as_of=datetime.date(2026, 2, 28),
        )

        assert pos.cash_by_currency == {"TRY": 300.0, "USD": 150.0}
        assert pos.bank_by_currency == {"TRY": 500.0, "USD": 75.0}
        assert pos.total_by_currency == {"TRY": 800.0, "USD": 225.0}

    def test_parity_with_balance_sheet_asset_lines(self, db, liquid_seed):
        co_a, _co_b = liquid_seed
        as_of = datetime.date(2026, 2, 28)

        pos = rb.compute_liquid_position(db, company_id=co_a.id, as_of=as_of)
        stmt = rr.compute_balance_sheet(db, company_id=co_a.id, as_of=as_of)
        bs_cash, bs_bank = _bs_liquid_totals(stmt)

        assert sum(pos.cash_by_currency.values()) == pytest.approx(bs_cash)
        assert sum(pos.bank_by_currency.values()) == pytest.approx(bs_bank)
        assert sum(pos.total_by_currency.values()) == pytest.approx(bs_cash + bs_bank)

    def test_returns_liquid_position_dataclass(self, db, liquid_seed):
        co_a, _co_b = liquid_seed
        pos = rb.compute_liquid_position(
            db, company_id=co_a.id, as_of=datetime.date(2026, 2, 28),
        )

        assert isinstance(pos, rb.LiquidPosition)
        assert pos.as_of == datetime.date(2026, 2, 28)
        assert hasattr(pos, "cash_by_currency")
        assert hasattr(pos, "bank_by_currency")
        assert hasattr(pos, "total_by_currency")
