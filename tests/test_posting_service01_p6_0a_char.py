"""POSTING-SERVICE-01 PS-P6-0a-CHAR — TD-POSTING-05 inline YEC guard characterization.

Pins the five duplicate inline YearEndClose guards before PS-P6-0b
centralization. No production changes.
"""
from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event, func
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app
import services.posting as posting_service

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

FISCAL_YEAR = "2025"
YEC_START = datetime.date(2025, 1, 1)
YEC_END = datetime.date(2025, 12, 31)
MOVEMENT_DATE = datetime.date(2025, 6, 15)
VOID_REASON = "PS-P6-0a-CHAR void pin"

POST_MOVEMENT_MSG = (
    f"Year {FISCAL_YEAR} is closed. Cannot post movements dated in that year."
)
VOID_MOVEMENT_MSG = (
    f"Year {FISCAL_YEAR} is closed. Void the year-end close before "
    "voiding movements inside it."
)
VOID_ALLOCATION_MSG = (
    f"Year {FISCAL_YEAR} is closed. Void the year-end close before "
    "voiding allocations inside it."
)


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(app._DEV_USER)
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
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        co = models.Company(
            name="P6-0a Char Co",
            slug="p6_0a_char_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        yield s, co.id


def _count(session, model):
    return session.query(func.count()).select_from(model).scalar()


def _make_coa(session, code, name, acct_type, *, currency=None):
    acct = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        balance=0.0,
        is_active=True,
        currency=currency,
    )
    session.add(acct)
    session.flush()
    return acct


def _insert_closed_yec(session, company_id):
    yec = models.YearEndClose(
        fiscal_year=FISCAL_YEAR,
        start_date=YEC_START,
        end_date=YEC_END,
        status="closed",
        closed_at=datetime.datetime.now(),
        period_count=12,
        allocation_count=12,
        net_income_snapshot=0.0,
        re_balance_at_close=0.0,
        is_void=False,
        created_at=datetime.datetime.now(),
        company_id=company_id,
    )
    session.add(yec)
    session.commit()
    return yec


def _seed_partner(session, company_id):
    cap = _make_coa(session, "3501", "Partner Capital", "Equity")
    cur = _make_coa(session, "3601", "Partner Current", "Equity")
    adv = _make_coa(session, "1501", "Partner Advances", "Asset")
    _make_coa(session, "1100", "Cash", "Asset", currency="TRY")
    partner = models.Partner(
        name="Alice",
        profit_share_pct=100.0,
        capital_account_id=cap.id,
        current_account_id=cur.id,
        advance_account_id=adv.id,
        is_active=True,
        created_at=datetime.datetime.now(),
        company_id=company_id,
    )
    session.add(partner)
    bank = models.BankAccount(
        name="Cash",
        currency="TRY",
        balance=10000.0,
        is_active=True,
        kind="bank",
        company_id=company_id,
    )
    session.add(bank)
    session.commit()
    return partner.id, bank.id, bank.balance


def _seed_worker(session, company_id):
    _make_coa(session, "1100", "Bank", "Asset", currency="TRY")
    _make_coa(session, "1250", "Employee Advances", "Asset")
    _make_coa(session, "5100", "Salary Expense", "Expense")
    worker_id, err = app.create_worker(session, "Ahmet", role="Sales")
    assert err == ""
    bank = models.BankAccount(
        name="Main TRY",
        currency="TRY",
        balance=50000.0,
        is_active=True,
        company_id=company_id,
    )
    session.add(bank)
    session.commit()
    return worker_id, bank.id, bank.balance


def _post_partner_movement_open_year(session, partner_id, bank_id, movement_date):
    mid, err = app.post_partner_movement(
        session,
        partner_id=partner_id,
        movement_type="Drawing",
        amount=500.0,
        date=movement_date,
        bank_account_id=bank_id,
        created_by_id=1,
    )
    assert err == "", f"pre-YEC post failed: {err}"
    assert mid is not None
    return mid


def _post_worker_movement_open_year(session, worker_id, bank_id, movement_date):
    mid, err = app.post_worker_movement(
        session,
        worker_id,
        "Advance",
        movement_date,
        bank_account_id=bank_id,
        amount=1000.0,
        created_by_id=1,
    )
    assert err == "", f"pre-YEC post failed: {err}"
    assert mid is not None
    return mid


def _make_allocation_in_closed_year_span(session, company_id, partner_id, cur_acct_id):
    re_acct = _make_coa(session, "3100", "Retained Earnings", "Equity")
    period = models.FiscalPeriod(
        name="Jan 2025",
        start_date=datetime.date(2025, 1, 1),
        end_date=datetime.date(2025, 1, 31),
        is_closed=False,
        company_id=company_id,
    )
    session.add(period)
    session.flush()
    alloc = models.PartnerProfitAllocation(
        fiscal_period_id=period.id,
        allocated_at=datetime.datetime.now(),
        allocated_by_id=1,
        total_net_income=1000.0,
        is_void=False,
        created_at=datetime.datetime.now(),
        company_id=company_id,
    )
    session.add(alloc)
    session.flush()
    je = app.create_journal_entry(
        session,
        datetime.date.today(),
        f"Profit Allocation for period {period.id}",
        "ProfitAllocation",
        alloc.id,
        [(re_acct.id, 1000.0, 0), (cur_acct_id, 0, 1000.0)],
    )
    alloc.journal_entry_id = je.id
    period.is_closed = True
    period.closed_at = datetime.date.today()
    session.commit()
    return alloc.id


class TestPostPartnerMovementYecGuard:
    def test_blocks_with_exact_message_and_no_side_effects(self, session):
        db, cid = session
        partner_id, bank_id, bank_balance = _seed_partner(db, cid)
        _insert_closed_yec(db, cid)

        n_mv = _count(db, models.PartnerMovement)
        n_btxn = _count(db, models.BankTransaction)
        n_je = _count(db, models.JournalEntry)

        mid, err = app.post_partner_movement(
            db,
            partner_id=partner_id,
            movement_type="Drawing",
            amount=500.0,
            date=MOVEMENT_DATE,
            bank_account_id=bank_id,
            created_by_id=1,
        )

        assert mid is None
        assert err == POST_MOVEMENT_MSG
        assert _count(db, models.PartnerMovement) == n_mv
        assert _count(db, models.BankTransaction) == n_btxn
        assert _count(db, models.JournalEntry) == n_je
        assert db.get(models.BankAccount, bank_id).balance == bank_balance


class TestVoidPartnerMovementYecGuard:
    def test_blocks_with_exact_message_and_no_side_effects(self, session):
        db, cid = session
        partner_id, bank_id, bank_balance = _seed_partner(db, cid)
        mid = _post_partner_movement_open_year(db, partner_id, bank_id, MOVEMENT_DATE)
        movement = db.get(models.PartnerMovement, mid)
        btxn_id = movement.bank_transaction_id
        bank_balance = db.get(models.BankAccount, bank_id).balance
        n_je = _count(db, models.JournalEntry)

        _insert_closed_yec(db, cid)

        err = app.void_partner_movement(db, mid, 1, VOID_REASON)

        assert err == VOID_MOVEMENT_MSG
        db.refresh(movement)
        assert movement.is_void is False
        assert _count(db, models.JournalEntry) == n_je
        btxn = db.get(models.BankTransaction, btxn_id)
        assert btxn is not None
        assert btxn.is_void is False
        assert db.get(models.BankAccount, bank_id).balance == bank_balance


class TestPostWorkerMovementYecGuard:
    def test_blocks_with_exact_message_and_no_side_effects(self, session):
        db, cid = session
        worker_id, bank_id, bank_balance = _seed_worker(db, cid)
        _insert_closed_yec(db, cid)

        n_mv = _count(db, models.WorkerMovement)
        n_btxn = _count(db, models.BankTransaction)
        n_je = _count(db, models.JournalEntry)

        mid, err = app.post_worker_movement(
            db,
            worker_id,
            "Advance",
            MOVEMENT_DATE,
            bank_account_id=bank_id,
            amount=1000.0,
            created_by_id=1,
        )

        assert mid is None
        assert err == POST_MOVEMENT_MSG
        assert _count(db, models.WorkerMovement) == n_mv
        assert _count(db, models.BankTransaction) == n_btxn
        assert _count(db, models.JournalEntry) == n_je
        assert db.get(models.BankAccount, bank_id).balance == bank_balance


class TestVoidWorkerMovementYecGuard:
    def test_blocks_with_exact_message_and_no_side_effects(self, session):
        db, cid = session
        worker_id, bank_id, bank_balance = _seed_worker(db, cid)
        mid = _post_worker_movement_open_year(db, worker_id, bank_id, MOVEMENT_DATE)
        movement = db.get(models.WorkerMovement, mid)
        btxn_id = movement.bank_transaction_id
        bank_balance = db.get(models.BankAccount, bank_id).balance
        n_je = _count(db, models.JournalEntry)

        _insert_closed_yec(db, cid)

        err = app.void_worker_movement(db, mid, 1, VOID_REASON)

        assert err == VOID_MOVEMENT_MSG
        db.refresh(movement)
        assert movement.is_void is False
        assert _count(db, models.JournalEntry) == n_je
        btxn = db.get(models.BankTransaction, btxn_id)
        assert btxn is not None
        assert btxn.is_void is False
        assert db.get(models.BankAccount, bank_id).balance == bank_balance


class TestVoidProfitAllocationYecGuard:
    def test_blocks_with_exact_message_and_no_side_effects(self, session):
        db, cid = session
        partner_id, _, _ = _seed_partner(db, cid)
        cur_acct_id = db.get(models.Partner, partner_id).current_account_id
        alloc_id = _make_allocation_in_closed_year_span(db, cid, partner_id, cur_acct_id)
        allocation = db.get(models.PartnerProfitAllocation, alloc_id)
        n_je = _count(db, models.JournalEntry)

        _insert_closed_yec(db, cid)

        err = app.void_profit_allocation(db, alloc_id, 1, VOID_REASON)

        assert err == VOID_ALLOCATION_MSG
        db.refresh(allocation)
        assert allocation.is_void is False
        assert _count(db, models.JournalEntry) == n_je


class TestVoidInlineGuardOriginalDateNotReversalToday:
    """Reversal JEs use today; kernel guard checks today, not movement date."""

    def test_kernel_allows_today_while_inline_blocks_original_date_void(self, session):
        db, cid = session
        partner_id, bank_id, _ = _seed_partner(db, cid)
        mid = _post_partner_movement_open_year(db, partner_id, bank_id, MOVEMENT_DATE)
        movement = db.get(models.PartnerMovement, mid)
        original_je = db.get(models.JournalEntry, movement.journal_entry_id)
        n_je = _count(db, models.JournalEntry)

        _insert_closed_yec(db, cid)

        today = datetime.date.today()
        assert today > YEC_END, "fixture requires today outside closed 2025 year"
        assert YEC_START <= movement.date <= YEC_END

        assert app._entry_date_posting_blocked(db, today) is None

        err = app.void_partner_movement(db, mid, 1, VOID_REASON)
        assert err == VOID_MOVEMENT_MSG
        assert _count(db, models.JournalEntry) == n_je

        reversal = posting_service.create_reversing_journal_entry(
            db, original_je, "PS-P6-0a-CHAR kernel path pin", company_id=cid
        )
        assert reversal is not None
        assert reversal.entry_date == today
        assert _count(db, models.JournalEntry) == n_je + 1
