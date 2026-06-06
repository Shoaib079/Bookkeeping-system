"""Tests for Phase 14C-A — Company-aware accounting helpers.

Verification checklist:
 1.  cq() returns only rows for active_company_id
 2.  cq() raises RuntimeError when no company context is set
 3.  current_company_required() returns the id when set
 4.  current_company_required() raises RuntimeError when absent
 5.  get_account_by_name scopes to active company when context is set
 6.  get_account_by_name returns None for account belonging to other company
 7.  get_account_by_name ignores company filter when no context (startup path)
 8.  calculate_account_balance_for_period scopes JEs to active company
 9.  calculate_account_balance_for_period ignores other company's JEs
10.  calculate_account_balance scopes to active company
11.  calculate_account_balance ignores other company's JEs
12.  before_flush stamps company_id on new objects when context is set
13.  before_flush does NOT stamp when no context (startup path)
"""

import sys
import datetime
from unittest.mock import MagicMock

# ── Streamlit mock — real dict for session_state ─────────────────────────────
if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock
else:
    _st_mock = sys.modules["streamlit"]
    if not isinstance(getattr(_st_mock, "session_state", None), dict):
        _st_mock.session_state = {}

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app

app.DEVELOPMENT_MODE = False


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def db():
    """Fresh in-memory SQLite per test — NOT tied to SessionLocal."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


# ─── Seed helpers ─────────────────────────────────────────────────────────────

def _company(db, name="Acme", slug="co1"):
    c = models.Company(
        name=name, slug=slug, is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(c)
    db.flush()
    return c


def _account(db, company_id, code="1000", name="Cash", acct_type="Asset"):
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


def _fiscal_period(db, company_id, name="Jan 2026",
                   start=datetime.date(2026, 1, 1),
                   end=datetime.date(2026, 1, 31)):
    fp = models.FiscalPeriod(
        name=name, start_date=start, end_date=end,
        is_closed=False, company_id=company_id,
    )
    db.add(fp)
    db.flush()
    return fp


def _journal_entry(db, company_id, account_id, debit=100.0, credit=0.0,
                   date=datetime.date(2026, 1, 15)):
    je = models.JournalEntry(
        entry_date=date,
        description="Test JE",
        reference_type="Sale",
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


def _set_company(company_id):
    sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _clear_company():
    sys.modules["streamlit"].session_state.pop("active_company_id", None)


# ─── 3–4. current_company_required() ─────────────────────────────────────────

class TestCurrentCompanyRequired:
    def test_returns_id_when_set(self):
        _set_company(42)
        assert app.current_company_required() == 42

    def test_raises_when_absent(self):
        with pytest.raises(RuntimeError, match="no active_company_id"):
            app.current_company_required()


# ─── 1–2. cq() ───────────────────────────────────────────────────────────────

class TestCq:
    def test_returns_only_active_company_rows(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")
        _fiscal_period(db, co_a.id, "Alpha-Jan")
        _fiscal_period(db, co_b.id, "Beta-Jan")

        _set_company(co_a.id)
        results = app.cq(db, models.FiscalPeriod).all()
        assert len(results) == 1
        assert results[0].name == "Alpha-Jan"

    def test_other_company_row_not_visible(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")
        _fiscal_period(db, co_a.id, "Alpha-Jan")
        _fiscal_period(db, co_b.id, "Beta-Jan")

        _set_company(co_b.id)
        results = app.cq(db, models.FiscalPeriod).all()
        names = [r.name for r in results]
        assert "Alpha-Jan" not in names
        assert "Beta-Jan" in names

    def test_raises_without_company_context(self, db):
        with pytest.raises(RuntimeError):
            app.cq(db, models.Sale).all()


# ─── 5–7. get_account_by_name ─────────────────────────────────────────────────

class TestGetAccountByName:
    def test_scoped_to_active_company(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")
        acct_a = _account(db, co_a.id, "1000", "Cash")
        _account(db, co_b.id, "1000", "Cash")  # same name, different company

        _set_company(co_a.id)
        result = app.get_account_by_name(db, "Cash")
        assert result is not None
        assert result.company_id == co_a.id

    def test_returns_none_for_other_company_account(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")
        _account(db, co_b.id, "1000", "Cash")  # only in co_b

        _set_company(co_a.id)
        result = app.get_account_by_name(db, "Cash")
        assert result is None

    def test_no_filter_when_no_context(self, db):
        co_a = _company(db, "Alpha", "alpha")
        _account(db, co_a.id, "1000", "Cash")

        _clear_company()  # startup path
        result = app.get_account_by_name(db, "Cash")
        assert result is not None  # visible without company context


# ─── 8–9. calculate_account_balance_for_period ───────────────────────────────

class TestCalculateAccountBalanceForPeriod:
    def test_returns_only_active_company_je_amounts(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")
        acct_a = _account(db, co_a.id, "1000", "Cash")
        acct_b = _account(db, co_b.id, "1000", "Cash")

        _journal_entry(db, co_a.id, acct_a.id, debit=300.0)
        _journal_entry(db, co_b.id, acct_b.id, debit=500.0)

        _set_company(co_a.id)
        bal = app.calculate_account_balance_for_period(
            db, acct_a,
            datetime.date(2026, 1, 1), datetime.date(2026, 1, 31),
        )
        assert bal == pytest.approx(300.0)

    def test_ignores_other_company_je(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")
        acct_a = _account(db, co_a.id, "1000", "Cash")
        acct_b = _account(db, co_b.id, "1000", "Cash")

        _journal_entry(db, co_b.id, acct_b.id, debit=999.0)

        _set_company(co_a.id)
        bal = app.calculate_account_balance_for_period(
            db, acct_a,
            datetime.date(2026, 1, 1), datetime.date(2026, 1, 31),
        )
        assert bal == pytest.approx(0.0)

    def test_no_filter_when_no_context(self, db):
        co_a = _company(db, "Alpha", "alpha")
        acct_a = _account(db, co_a.id, "1000", "Cash")
        _journal_entry(db, co_a.id, acct_a.id, debit=200.0)

        _clear_company()
        bal = app.calculate_account_balance_for_period(
            db, acct_a,
            datetime.date(2026, 1, 1), datetime.date(2026, 1, 31),
        )
        assert bal == pytest.approx(200.0)


# ─── 10–11. calculate_account_balance ────────────────────────────────────────

class TestCalculateAccountBalance:
    def test_scoped_to_active_company(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")
        acct_a = _account(db, co_a.id, "1000", "Cash")
        acct_b = _account(db, co_b.id, "1000", "Cash")

        _journal_entry(db, co_a.id, acct_a.id, debit=400.0)
        _journal_entry(db, co_b.id, acct_b.id, debit=600.0)

        _set_company(co_a.id)
        bal = app.calculate_account_balance(db, acct_a)
        assert bal == pytest.approx(400.0)

    def test_ignores_other_company_je(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")
        acct_a = _account(db, co_a.id, "1000", "Cash")
        acct_b = _account(db, co_b.id, "1000", "Cash")

        _journal_entry(db, co_b.id, acct_b.id, debit=777.0)

        _set_company(co_a.id)
        bal = app.calculate_account_balance(db, acct_a)
        assert bal == pytest.approx(0.0)

    def test_no_filter_when_no_context(self, db):
        co_a = _company(db, "Alpha", "alpha")
        acct_a = _account(db, co_a.id, "1000", "Cash")
        _journal_entry(db, co_a.id, acct_a.id, debit=150.0)

        _clear_company()
        bal = app.calculate_account_balance(db, acct_a)
        assert bal == pytest.approx(150.0)


# ─── 12–13. before_flush company_id stamping ─────────────────────────────────
# before_flush is registered on SessionLocal, not on the per-test Session,
# so we test the stamping logic directly: _stamp_company_id_on_new_objects
# is a module-level function we can call with a mock session.

class TestBeforeFlushStamp:
    def test_stamps_company_id_when_context_set(self):
        _set_company(7)
        sale = models.Sale()
        sale.company_id = None

        class _FakeSession:
            new = [sale]

        app._stamp_company_id_on_new_objects(_FakeSession(), None, None)
        assert sale.company_id == 7

    def test_does_not_stamp_when_no_context(self):
        _clear_company()
        sale = models.Sale()
        sale.company_id = None

        class _FakeSession:
            new = [sale]

        app._stamp_company_id_on_new_objects(_FakeSession(), None, None)
        assert sale.company_id is None

    def test_does_not_overwrite_existing_company_id(self):
        _set_company(7)
        cu = models.CompanyUser()
        cu.company_id = 3  # explicitly set by caller

        class _FakeSession:
            new = [cu]

        app._stamp_company_id_on_new_objects(_FakeSession(), None, None)
        assert cu.company_id == 3  # untouched

    def test_skips_global_models_without_company_id(self):
        _set_company(7)
        user = models.User()
        # User has no company_id column — hasattr check must not raise

        class _FakeSession:
            new = [user]

        app._stamp_company_id_on_new_objects(_FakeSession(), None, None)
        assert not hasattr(user, "company_id")
