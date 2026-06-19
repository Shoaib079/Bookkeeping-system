"""OBS-004 — centralized Add Transaction date ownership acceptance tests."""

from __future__ import annotations

import datetime
import inspect
import re
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
    sys.modules["streamlit"].session_state = {}

import app as erp
import models
from db import Base
from registry.categories_seed import seed_default_categories_for_company
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import at_date_ownership as at_date

SELECTED = datetime.date(2026, 6, 10)
TODAY = datetime.date(2026, 6, 19)


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

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        erp._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as session:
        yield session


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


def _extract_at_entry_form_block() -> str:
    src = inspect.getsource(erp.render_add_transaction)
    marker = 'with st.form("at_entry_form", clear_on_submit=False):'
    start = src.index(marker)
    # Form body ends at submission handler comment (same indent level as `with st.form`).
    end = src.index("# ── SUBMISSION HANDLER", start)
    return src[start:end]


def _setup_company(db):
    co = models.Company(
        name="OBS-004 Co",
        slug="obs_004_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    erp.st.session_state["active_company_id"] = co.id
    seed_chart_of_accounts_for_company(db, co.id)
    seed_default_categories_for_company(db, co.id)
    db.commit()
    return co


def _assert_record_and_je_dates(
    db,
    *,
    reference_type: str,
    reference_id: int,
    expected: datetime.date,
):
    if reference_type == "CashSale":
        record = db.get(models.Sale, reference_id)
        assert record is not None
        assert record.date == expected
    else:
        raise AssertionError(reference_type)
    je = (
        db.query(models.JournalEntry)
        .filter_by(reference_type=reference_type, reference_id=reference_id)
        .one()
    )
    assert je.entry_date == expected


# ── Criterion 1: no widget key mutation (OBS-001) ───────────────────────────


def test_resolve_submit_date_never_mutates_at_date():
    state = _WidgetBoundSessionState(
        {"at_date": TODAY, "at_submit_resolved_date": SELECTED}
    )
    state.mark_at_date_widget_live()
    erp.st.session_state = state
    assert erp._at_resolve_submit_date() == SELECTED
    assert state["at_date"] is TODAY


def test_capture_pins_without_mutating_widget_key_when_already_set():
    state = _WidgetBoundSessionState({"at_date": SELECTED, "at_date_follows_today": True})
    state.mark_at_date_widget_live()
    at_date.capture_submit_resolved_date(state, today=TODAY)
    assert state["at_submit_resolved_date"] == SELECTED
    assert state["at_date"] is SELECTED


# ── Criterion 2: no callbacks inside at_entry_form ──────────────────────────


def test_desktop_date_field_has_no_callbacks():
    src = inspect.getsource(erp._at_render_desktop_date_field)
    assert "on_change" not in src
    assert "on_click" not in src


def test_at_entry_form_has_no_widget_callbacks():
    block = _extract_at_entry_form_block()
    # st.form_submit_button is allowed; other widgets must not use callbacks.
    widget_lines = [
        ln
        for ln in block.splitlines()
        if re.search(r"\bst\.(date_input|selectbox|text_input|radio|checkbox|button)\b", ln)
    ]
    for ln in widget_lines:
        assert "on_change" not in ln, f"forbidden on_change in form: {ln.strip()}"
        assert "on_click" not in ln, f"forbidden on_click in form: {ln.strip()}"


# ── Criterion 3: DATE-01 must not overwrite historical picks ────────────────


def test_rollover_preserves_deep_backdate_with_stale_follow_flag():
    backdate = TODAY - datetime.timedelta(days=10)
    state = {"at_date": backdate, "at_date_follows_today": True}
    at_date.apply_follow_today_rollover(state, today=TODAY)
    assert state["at_date"] == backdate
    assert state["at_date_follows_today"] is False


def test_rollover_rolls_yesterday_only_when_follow_today():
    yesterday = TODAY - datetime.timedelta(days=1)
    state = {"at_date": yesterday, "at_date_follows_today": True}
    at_date.apply_follow_today_rollover(state, today=TODAY)
    assert state["at_date"] == TODAY


def test_explicit_yesterday_pinned_survives_rollover():
    yesterday = TODAY - datetime.timedelta(days=1)
    state = {"at_date": yesterday, "at_date_follows_today": False}
    at_date.apply_follow_today_rollover(state, today=TODAY)
    assert state["at_date"] == yesterday


def test_capture_clears_follow_flag_for_non_today_submit():
    state = {"at_date": SELECTED, "at_date_follows_today": True}
    at_date.capture_submit_resolved_date(state, today=TODAY)
    assert state["at_date_follows_today"] is False
    assert state["at_submit_resolved_date"] == SELECTED


# ── Criteria 4–5: selected date posts; JE matches ─────────────────────────


def test_desktop_submit_pipeline_posts_selected_date_and_je(monkeypatch, db):
    co = _setup_company(db)
    erp.st.session_state.update(
        {
            "at_date": SELECTED,
            "at_date_follows_today": True,
            "at_pm": "Cash",
            "at_amount_display": "55",
            "at_currency": "TRY",
            "at_notes_field": "",
            "at_cust": "Walk-in Customer",
        }
    )
    at_date.pre_render_date_sync(erp.st.session_state, today=TODAY)
    at_date.capture_submit_resolved_date(erp.st.session_state, today=TODAY)
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=[],
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )
    sale = (
        db.query(models.Sale)
        .filter_by(company_id=co.id, is_void=False)
        .order_by(models.Sale.id.desc())
        .first()
    )
    assert sale is not None
    _assert_record_and_je_dates(
        db, reference_type="CashSale", reference_id=sale.id, expected=SELECTED
    )


# ── Criterion 6: desktop/mobile parity (same SSOT module) ───────────────────


def test_mobile_set_date_choice_uses_ssot():
    src = inspect.getsource(erp._mob_at_set_date_choice)
    assert "_at_set_date_choice" in src


def test_mobile_rollover_delegates_to_ssot():
    src = inspect.getsource(erp._mob_at_apply_date_follow_today)
    assert "_at_apply_follow_today_rollover" in src


def test_pre_render_called_from_render_add_transaction():
    src = inspect.getsource(erp.render_add_transaction)
    assert "_at_pre_render_date_sync(st.session_state)" in src


def test_desktop_and_mobile_capture_same_pinned_date():
    state = {"at_date": SELECTED}
    at_date.capture_submit_resolved_date(state, today=TODAY)
    pinned = at_date.resolve_submit_date(dict(state), today=TODAY)
    assert pinned == SELECTED


def test_mobile_yesterday_choice_matches_desktop_capture_semantics():
    yesterday = TODAY - datetime.timedelta(days=1)
    state = {}
    at_date.set_date_choice(state, yesterday, follows_today=False)
    at_date.capture_submit_resolved_date(state, today=TODAY)
    assert at_date.resolve_submit_date(state, today=TODAY) == yesterday
    assert state["at_date_follows_today"] is False


# ── Criterion 7: regression guardrails ─────────────────────────────────────


def test_no_duplicate_rollover_logic_in_app():
    """Rollover body must live only in services/at_date_ownership.py."""
    src = inspect.getsource(erp._mob_at_apply_date_follow_today)
    assert "timedelta" not in src
    assert "_at_apply_follow_today_rollover" in src


def test_obs_001_resolve_path_unchanged():
    assert "resolve_submit_date" in inspect.getsource(erp._at_resolve_submit_date)


def test_obs_002_stale_follow_submit_still_preserves_backdate(db):
    co = _setup_company(db)
    erp.st.session_state.update(
        {
            "at_date": SELECTED,
            "at_date_follows_today": True,
            "at_pm": "Cash",
            "at_amount_display": "10",
            "at_currency": "TRY",
            "at_notes_field": "",
            "at_cust": "Walk-in Customer",
        }
    )
    at_date.pre_render_date_sync(erp.st.session_state, today=TODAY)
    at_date.capture_submit_resolved_date(erp.st.session_state, today=TODAY)
    assert erp.st.session_state["at_submit_resolved_date"] == SELECTED
    erp._at_process_submit(
        db,
        currency_default="TRY",
        vendors=[],
        bank_accounts=[],
        open_sales=[],
        txn_type="Sale",
        _TYPE_DISPLAY_MAP={},
    )
    sale = db.query(models.Sale).filter_by(company_id=co.id).one()
    assert sale.date == SELECTED
