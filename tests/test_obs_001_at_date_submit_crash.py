"""OBS-001 — Add Transaction submit must not mutate ``at_date`` after widget creation."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

import app as erp
import models
from db import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PAST = datetime.date(2026, 3, 15)
TODAY = datetime.date.today()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as session:
        yield session


@pytest.fixture(autouse=True)
def clear_session():
    erp.st.session_state = {}
    yield
    erp.st.session_state = {}


class _WidgetBoundSessionState(dict):
    """Reject writes to ``at_date`` once the date widget is considered live."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._at_date_widget_live = False

    def mark_at_date_widget_live(self) -> None:
        self._at_date_widget_live = True

    def __setitem__(self, key, value):
        if key == "at_date" and self._at_date_widget_live:
            raise RuntimeError(
                "st.session_state.at_date cannot be modified after widget instantiation"
            )
        super().__setitem__(key, value)


def test_resolve_submit_date_does_not_mutate_at_date_when_cache_present():
    """Pinned submit date is returned without writing back to widget key."""
    widget_date = TODAY
    erp.st.session_state["at_date"] = widget_date
    erp.st.session_state["at_submit_resolved_date"] = PAST

    resolved = erp._at_resolve_submit_date()

    assert resolved == PAST
    assert erp.st.session_state["at_date"] is widget_date
    assert "at_submit_resolved_date" not in erp.st.session_state


def test_resolve_submit_date_does_not_mutate_at_date_on_fallback():
    """Fallback reads widget SSOT without assigning ``at_date``."""
    erp.st.session_state["at_date"] = PAST

    resolved = erp._at_resolve_submit_date()

    assert resolved == PAST
    assert erp.st.session_state["at_date"] is PAST


def test_resolve_submit_date_never_assigns_at_date_after_widget_bound():
    """Regression for StreamlitAPIException on submit after ``key=at_date`` widget."""
    state = _WidgetBoundSessionState(
        {"at_date": TODAY, "at_submit_resolved_date": PAST}
    )
    state.mark_at_date_widget_live()
    erp.st.session_state = state

    assert erp._at_resolve_submit_date() == PAST
    assert state["at_date"] is TODAY


def test_gather_submit_uses_pinned_date_without_clobbering_widget_value(db):
    """Submit path posts pinned date while ``at_date`` retention key stays unchanged."""
    co = models.Company(
        name="OBS Co",
        slug="obs_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()

    widget_date = TODAY
    erp.st.session_state.update(
        {
            "active_company_id": co.id,
            "at_date": widget_date,
            "at_submit_resolved_date": PAST,
            "at_pm": "Cash",
            "at_expense_mode": "worker",
            "at_worker_id": 1,
        }
    )

    ctx = erp._at_gather_submit_fields(db, "Expense", "TRY", [], [], [])

    assert ctx["date"] == PAST
    assert erp.st.session_state["at_date"] is widget_date
