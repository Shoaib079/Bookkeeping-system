"""Regression: TXH must not crash on backdated expenses (UnboundLocalError on `s`)."""
from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

_TXH_ALL = "All"


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
            name="Test Co",
            slug="test_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        yield s


def _fetch(
    session,
    *,
    start_date: datetime.date,
    end_date: datetime.date,
    type_filter: str = _TXH_ALL,
    user_lkp: dict | None = None,
):
    return app._txh_fetch_filtered_rows(
        session,
        start_date=start_date,
        end_date=end_date,
        keyword="",
        type_filter=type_filter,
        method_filter=_TXH_ALL,
        cat_filter=_TXH_ALL,
        subcat_filter=_TXH_ALL,
        show_voided=False,
        currency="TRY",
        cat_names_lkp={},
        subcat_names_lkp={},
        user_lkp=user_lkp or {},
        txh_all=_TXH_ALL,
    )


def _add_expense(session, *, expense_date: datetime.date, created_by_id: int | None):
    rec = models.ExpenseRecord(
        date=expense_date,
        expense_type="Operating",
        category="Supplies",
        description="Backdated expense",
        amount=50.0,
        payment_method="Cash",
        created_by_id=created_by_id,
    )
    session.add(rec)
    session.commit()
    return rec


class TestBackdatedExpenseCreatedBy:
    def test_last_month_expense_no_sales_no_crash(self, session):
        """Reproduces crash: Expense-only path when Sale loop never binds `s`."""
        today = datetime.date.today()
        last_month_end = today.replace(day=1) - datetime.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        _add_expense(session, expense_date=last_month_end, created_by_id=1)

        rows = _fetch(
            session,
            start_date=last_month_start,
            end_date=last_month_end,
            type_filter="Expense",
        )
        assert len(rows) == 1
        assert rows[0][0]["Created By"] == "—"

    def test_last_month_created_by_resolves(self, session):
        today = datetime.date.today()
        last_month_end = today.replace(day=1) - datetime.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        user = models.User(
            username="owner1",
            display_name="Alex Owner",
            password_hash="x",
            role="owner",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        session.add(user)
        session.flush()
        _add_expense(session, expense_date=last_month_end, created_by_id=user.id)

        rows = _fetch(
            session,
            start_date=last_month_start,
            end_date=last_month_end,
            type_filter=_TXH_ALL,
            user_lkp={user.id: user.display_name},
        )
        expense_rows = [r for r in rows if r[1] == "ExpenseRecord"]
        assert len(expense_rows) == 1
        assert expense_rows[0][0]["Created By"] == "Alex Owner"

    def test_missing_created_by_shows_dash(self, session):
        today = datetime.date.today()
        month_start = today.replace(day=1)
        _add_expense(session, expense_date=month_start, created_by_id=None)

        rows = _fetch(
            session,
            start_date=month_start,
            end_date=today,
            type_filter="Expense",
            user_lkp={99: "Someone"},
        )
        assert rows[0][0]["Created By"] == "—"

    def test_custom_range_includes_backdated_row(self, session):
        today = datetime.date.today()
        custom_from = today - datetime.timedelta(days=45)
        custom_to = today - datetime.timedelta(days=30)
        _add_expense(session, expense_date=custom_from + datetime.timedelta(days=5), created_by_id=None)

        rows = _fetch(session, start_date=custom_from, end_date=custom_to)
        assert any(r[1] == "ExpenseRecord" for r in rows)

    def test_current_month_all_types_no_crash(self, session):
        today = datetime.date.today()
        month_start = today.replace(day=1)
        _add_expense(session, expense_date=today, created_by_id=None)

        rows = _fetch(session, start_date=month_start, end_date=today)
        assert any(r[1] == "ExpenseRecord" for r in rows)
