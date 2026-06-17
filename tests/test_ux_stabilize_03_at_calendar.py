"""UX-STABILIZE-03 Phase 1 — Add Transaction calendar support."""

from __future__ import annotations

import datetime
import inspect
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

import app as erp
import models
from db import Base
from ui import date_input as date_ui

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as session:
        yield session


@pytest.fixture(autouse=True)
def clear_session():
    erp.st.session_state.clear()
    yield
    erp.st.session_state.clear()


# ── Shared helper contract ────────────────────────────────────────────────────


def test_render_preferred_date_input_accepts_show_calendar(monkeypatch):
    monkeypatch.setattr(date_ui.st, "text_input", lambda *a, **k: None)
    monkeypatch.setattr(date_ui.st, "date_input", lambda *a, **k: None)
    monkeypatch.setattr(
        date_ui.st,
        "expander",
        lambda *a, **k: MagicMock(__enter__=lambda s: s, __exit__=lambda *a: None),
    )
    monkeypatch.setattr(
        date_ui.st,
        "session_state",
        {"_user_date_format": "DD.MM.YYYY", "at_date_text": "05.06.2026"},
    )
    date_ui.render_preferred_date_input(
        "Date",
        "at_date_text",
        in_form=True,
        show_calendar=True,
        calendar_key="at_date_cal",
    )


def test_reconcile_calendar_wins_when_text_unchanged():
    prev = datetime.date(2026, 6, 1)
    picked = datetime.date(2026, 6, 15)
    state = {
        "_user_date_format": "DD.MM.YYYY",
        "at_date_text": "01.06.2026",
        "at_date_cal": picked,
        "at_date": prev,
    }
    erp.st.session_state.update(state)
    assert date_ui.reconcile_text_and_calendar(
        "at_date_text", "at_date_cal", canonical_key="at_date"
    ) == picked


def test_reconcile_typed_wins_when_calendar_unchanged():
    prev = datetime.date(2026, 6, 1)
    typed = datetime.date(2026, 6, 20)
    state = {
        "_user_date_format": "DD.MM.YYYY",
        "at_date_text": "20.06.2026",
        "at_date_cal": prev,
        "at_date": prev,
    }
    erp.st.session_state.update(state)
    assert date_ui.reconcile_text_and_calendar(
        "at_date_text", "at_date_cal", canonical_key="at_date"
    ) == typed


# ── Desktop resolve path ──────────────────────────────────────────────────────


def test_at_resolve_entry_date_calendar_updates_at_date(monkeypatch):
    prev = datetime.date(2026, 6, 1)
    picked = datetime.date(2026, 6, 15)
    state = {
        "_user_date_format": "DD.MM.YYYY",
        "at_date_text": "01.06.2026",
        "at_date_cal": picked,
        "at_date": prev,
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    resolved = erp._at_resolve_entry_date()
    assert resolved == picked
    assert state["at_date"] == picked


def test_at_resolve_backdated_wins_over_stale_today_text(monkeypatch):
    past = datetime.date(2026, 3, 15)
    today = datetime.date.today()
    today_text = erp._format_at_display_date(today)
    state = {
        "_user_date_format": "DD.MM.YYYY",
        "at_date": past,
        "at_date_follows_today": False,
        "at_date_text": today_text,
        "at_date_cal": today,
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._at_resolve_entry_date() == past


def test_at_resolve_entry_date_typed_date_still_works(monkeypatch):
    state = {
        "_user_date_format": "DD.MM.YYYY",
        "at_date_text": "20.06.2026",
        "at_date_cal": datetime.date(2026, 6, 1),
        "at_date": datetime.date(2026, 6, 1),
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    resolved = erp._at_resolve_entry_date()
    assert resolved == datetime.date(2026, 6, 20)
    assert state["at_date"] == datetime.date(2026, 6, 20)


def test_post_save_retains_at_date(monkeypatch):
    pinned = datetime.date(2026, 6, 10)
    state = {
        "at_date": pinned,
        "at_date_text": "10.06.2026",
        "at_amount_display": "100",
        "at_notes_field": "note",
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_clear_post_save_transient_fields()
    assert state["at_date"] == pinned
    assert "at_amount_display" not in state


@pytest.mark.parametrize(
    "txn_type,extra",
    [
        ("Sale", {}),
        ("Expense", {"at_expense_mode": "worker", "at_worker_id": 1}),
        ("Purchase", {}),
    ],
)
def test_gather_submit_uses_same_at_date(monkeypatch, db, txn_type, extra):
    co = models.Company(
        name="Cal Co",
        slug="cal_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    if txn_type == "Purchase":
        db.add(
            models.TransactionCategory(
                transaction_type="Purchase",
                name="Supplies",
                company_id=co.id,
                is_active=True,
            )
        )
    db.commit()
    pinned = datetime.date(2026, 6, 12)
    state = {
        "active_company_id": co.id,
        "_user_date_format": "DD.MM.YYYY",
        "at_date": pinned,
        "at_submit_resolved_date": pinned,
        "at_pm": "Cash",
        "at_amount_display": "50",
        **extra,
    }
    if txn_type == "Purchase":
        state["at_cat"] = "Supplies"
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "_coerce_at_payment_method", lambda *a, **k: None)
    monkeypatch.setattr(erp, "_mob_at_sync_select_widgets", lambda: None)
    ctx = erp._at_gather_submit_fields(
        db, txn_type, "TRY", [], [], []
    )
    assert ctx["date"] == pinned


def test_mobile_custom_path_has_calendar():
    src = inspect.getsource(erp._mob_at_render_date_picker_sheet)
    assert "show_calendar=True" in src
    assert "mob_at_date_custom_cal" in src
    assert "reconcile_text_and_calendar" in src


def test_calendar_logic_has_no_db_or_postgres_coupling():
    """Calendar support is UI-only — no schema/accounting/PostgreSQL changes."""
    date_src = (ROOT / "ui" / "date_input.py").read_text(encoding="utf-8")
    for banned in ("sqlalchemy", "postgresql", "create_engine", "fiscalperiod"):
        assert banned not in date_src.lower()
    assert "def reconcile_text_and_calendar" in date_src
    desktop = inspect.getsource(erp._at_render_desktop_date_field)
    assert "show_calendar=True" in desktop
    assert "SessionLocal" not in desktop
