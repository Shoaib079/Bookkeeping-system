"""POSTING-SERVICE-01 PS-P6-0a — yec_block_message helper characterization.

Pure helper proof only. No call-site rewiring; inline guards unchanged in app.py.
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
import services.posting as posting

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
PERIOD_START = datetime.date(2025, 1, 1)
PERIOD_END = datetime.date(2025, 1, 31)
OPEN_DATE = datetime.date(2026, 3, 1)

POST_MSG = (
    f"Year {FISCAL_YEAR} is closed. Cannot post movements dated in that year."
)
MOVEMENT_VOID_MSG = (
    f"Year {FISCAL_YEAR} is closed. Void the year-end close before "
    "voiding movements inside it."
)
ALLOCATION_VOID_MSG = (
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
            name="P6-0a Co",
            slug="p6_0a_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        yield s, co.id


def _count(session, model):
    return session.query(func.count()).select_from(model).scalar()


def _insert_closed_yec(session, company_id, *, is_void=False):
    yec = models.YearEndClose(
        fiscal_year=FISCAL_YEAR,
        start_date=YEC_START,
        end_date=YEC_END,
        status="voided" if is_void else "closed",
        closed_at=datetime.datetime.now(),
        period_count=12,
        allocation_count=12,
        net_income_snapshot=0.0,
        re_balance_at_close=0.0,
        is_void=is_void,
        created_at=datetime.datetime.now(),
        company_id=company_id,
    )
    session.add(yec)
    session.commit()
    return yec


def _snapshot_counts(session):
    return {
        "yec": _count(session, models.YearEndClose),
        "je": _count(session, models.JournalEntry),
        "mv": _count(session, models.PartnerMovement),
        "btxn": _count(session, models.BankTransaction),
        "bank": _count(session, models.BankAccount),
    }


class TestYecBlockMessagePostMode:
    def test_returns_exact_post_message_when_date_in_closed_year(self, session):
        db, cid = session
        _insert_closed_yec(db, cid)
        before = _snapshot_counts(db)

        msg = posting.yec_block_message(
            db, MOVEMENT_DATE, mode="post", company_id=cid
        )

        assert msg == POST_MSG
        assert _snapshot_counts(db) == before

    def test_returns_none_when_no_yec(self, session):
        db, cid = session
        assert posting.yec_block_message(
            db, MOVEMENT_DATE, mode="post", company_id=cid
        ) is None

    def test_returns_none_when_date_outside_closed_year(self, session):
        db, cid = session
        _insert_closed_yec(db, cid)
        assert posting.yec_block_message(
            db, OPEN_DATE, mode="post", company_id=cid
        ) is None

    def test_returns_none_for_void_yec(self, session):
        db, cid = session
        _insert_closed_yec(db, cid, is_void=True)
        assert posting.yec_block_message(
            db, MOVEMENT_DATE, mode="post", company_id=cid
        ) is None

    def test_company_scoped(self, session):
        db, cid = session
        _insert_closed_yec(db, cid)
        other_co = models.Company(
            name="Other Co",
            slug="other_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        db.add(other_co)
        db.commit()
        assert posting.yec_block_message(
            db, MOVEMENT_DATE, mode="post", company_id=other_co.id
        ) is None


class TestYecBlockMessageMovementVoidMode:
    def test_returns_exact_movement_void_message(self, session):
        db, cid = session
        _insert_closed_yec(db, cid)

        msg = posting.yec_block_message(
            db, MOVEMENT_DATE, mode="movement_void", company_id=cid
        )

        assert msg == MOVEMENT_VOID_MSG

    def test_returns_none_when_not_blocked(self, session):
        db, cid = session
        _insert_closed_yec(db, cid)
        assert posting.yec_block_message(
            db, OPEN_DATE, mode="movement_void", company_id=cid
        ) is None


class TestYecBlockMessageAllocationVoidMode:
    def test_returns_exact_allocation_void_message_for_period_span(self, session):
        db, cid = session
        _insert_closed_yec(db, cid)

        msg = posting.yec_block_message(
            db,
            PERIOD_START,
            mode="allocation_void",
            company_id=cid,
            period_end_date=PERIOD_END,
        )

        assert msg == ALLOCATION_VOID_MSG

    def test_returns_none_without_period_end_date(self, session):
        db, cid = session
        _insert_closed_yec(db, cid)
        assert posting.yec_block_message(
            db, PERIOD_START, mode="allocation_void", company_id=cid
        ) is None

    def test_span_query_differs_from_point_on_partial_overlap(self, session):
        """Period straddling YEC end is not blocked by allocation span check."""
        db, cid = session
        _insert_closed_yec(db, cid)
        span_start = datetime.date(2025, 12, 1)
        span_end = datetime.date(2026, 1, 31)

        assert posting.yec_block_message(
            db,
            span_start,
            mode="allocation_void",
            company_id=cid,
            period_end_date=span_end,
        ) is None
        assert posting.yec_block_message(
            db, span_start, mode="post", company_id=cid
        ) is not None


class TestYecBlockMessageNoSideEffects:
    def test_helper_is_read_only(self, session):
        db, cid = session
        _insert_closed_yec(db, cid)
        before = _snapshot_counts(db)

        for mode in ("post", "movement_void"):
            posting.yec_block_message(
                db, MOVEMENT_DATE, mode=mode, company_id=cid
            )
        posting.yec_block_message(
            db,
            PERIOD_START,
            mode="allocation_void",
            company_id=cid,
            period_end_date=PERIOD_END,
        )
        posting.yec_block_message(
            db, OPEN_DATE, mode="post", company_id=cid
        )

        assert _snapshot_counts(db) == before


class TestYecBlockMessageInlineParity:
    """Helper messages match inline guard strings from PS-P6-0a-CHAR."""

    def test_post_mode_matches_post_partner_movement_guard(self, session):
        db, cid = session
        _insert_closed_yec(db, cid)
        helper_msg = posting.yec_block_message(
            db, MOVEMENT_DATE, mode="post", company_id=cid
        )
        _, inline_err = app.post_partner_movement(
            db,
            partner_id=999,
            movement_type="Drawing",
            amount=100.0,
            date=MOVEMENT_DATE,
            bank_account_id=1,
        )
        assert helper_msg == inline_err

    def test_movement_void_mode_matches_void_partner_movement_guard(self, session):
        db, cid = session
        movement = models.PartnerMovement(
            partner_id=1,
            movement_type="Drawing",
            amount=200.0,
            date=MOVEMENT_DATE,
            is_void=False,
            created_at=datetime.datetime.now(),
            company_id=cid,
        )
        db.add(movement)
        db.commit()
        _insert_closed_yec(db, cid)

        helper_msg = posting.yec_block_message(
            db, movement.date, mode="movement_void", company_id=cid
        )
        inline_err = app.void_partner_movement(db, movement.id, 1, "parity pin")
        assert helper_msg == inline_err

    def test_allocation_void_mode_matches_void_profit_allocation_guard(self, session):
        db, cid = session
        period = models.FiscalPeriod(
            name="Jan 2025",
            start_date=PERIOD_START,
            end_date=PERIOD_END,
            is_closed=True,
            closed_at=datetime.date.today(),
            company_id=cid,
        )
        db.add(period)
        db.flush()
        alloc = models.PartnerProfitAllocation(
            fiscal_period_id=period.id,
            allocated_at=datetime.datetime.now(),
            total_net_income=1000.0,
            is_void=False,
            created_at=datetime.datetime.now(),
            company_id=cid,
        )
        db.add(alloc)
        db.commit()
        _insert_closed_yec(db, cid)

        helper_msg = posting.yec_block_message(
            db,
            PERIOD_START,
            mode="allocation_void",
            company_id=cid,
            period_end_date=PERIOD_END,
        )
        inline_err = app.void_profit_allocation(db, alloc.id, 1, "parity pin")
        assert helper_msg == inline_err
