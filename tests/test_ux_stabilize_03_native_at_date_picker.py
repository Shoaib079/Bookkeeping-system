"""UX-STABILIZE-03 — Add Transaction native st.date_input (one field only)."""

from __future__ import annotations

import datetime
import inspect
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

import app as erp
import models
from db import Base
from registry.date_utils import streamlit_date_input_format

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clear_session():
    erp.st.session_state.clear()
    yield
    erp.st.session_state.clear()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as session:
        yield session


def test_no_calendar_hybrid_symbols_in_codebase():
    for rel in ("app.py", "ui/date_input.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        for banned in (
            "show_calendar",
            "calendar_key",
            "calendar_label",
            "reconcile_text_and_calendar",
            "at_date_cal",
            "mob_at_date_custom_cal",
        ):
            assert banned not in text, f"{banned} found in {rel}"


def test_streamlit_format_mapping():
    assert streamlit_date_input_format("DD.MM.YYYY") == "DD.MM.YYYY"
    assert streamlit_date_input_format("DD/MM/YYYY") == "DD/MM/YYYY"
    assert streamlit_date_input_format("YYYY-MM-DD") == "YYYY-MM-DD"


def test_desktop_at_uses_one_native_date_input():
    src = inspect.getsource(erp._at_render_desktop_date_field)
    assert src.count("st.date_input") == 1
    assert 'key="at_date"' in src
    assert "render_preferred_date_input" not in src


def test_post_save_retains_at_date(monkeypatch):
    pinned = datetime.date(2026, 6, 10)
    state = {
        "at_date": pinned,
        "at_amount_display": "100",
        "at_notes_field": "note",
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_clear_post_save_transient_fields()
    assert state["at_date"] == pinned
    assert "at_amount_display" not in state


@pytest.mark.parametrize("txn_type", ["Sale", "Expense", "Purchase"])
def test_gather_submit_uses_same_at_date(monkeypatch, db, txn_type):
    co = models.Company(
        name="Native Co",
        slug="native_co",
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
        "at_date": pinned,
        "at_submit_resolved_date": pinned,
        "at_pm": "Cash",
        "at_amount_display": "50",
    }
    if txn_type == "Expense":
        state["at_expense_mode"] = "worker"
        state["at_worker_id"] = 1
    if txn_type == "Purchase":
        state["at_cat"] = "Supplies"
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "_coerce_at_payment_method", lambda *a, **k: None)
    monkeypatch.setattr(erp, "_mob_at_sync_select_widgets", lambda: None)
    ctx = erp._at_gather_submit_fields(db, txn_type, "TRY", [], [], [])
    assert ctx["date"] == pinned


def test_mobile_custom_uses_native_date_input():
    src = inspect.getsource(erp._mob_at_render_date_picker_sheet)
    assert "st.date_input" in src
    assert "mob_at_date_custom_pick" in src
    assert "render_preferred_date_input" not in src
