"""DATE-01 — fast mobile date entry (sheet quick choices + rollover + backdated marker)."""

from __future__ import annotations

import datetime
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock
else:
    _st_mock = sys.modules["streamlit"]
    if not isinstance(getattr(_st_mock, "session_state", None), dict):
        _st_mock.session_state = {}

import app as erp
import models
from db import Base


class _FakeSessionState(dict):
    def get(self, key, default=None):
        return super().get(key, default)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


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


# ── Rollover flag ─────────────────────────────────────────────────────────────


def test_flag_in_company_scoped_keys():
    assert "at_date_follows_today" in erp._COMPANY_SCOPED_AT_KEYS


def test_default_and_today_set_follow_flag(monkeypatch):
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    today = datetime.date(2026, 6, 10)
    erp._mob_at_set_date_choice(today, follows_today=True)
    assert state["at_date_follows_today"] is True
    assert state["at_date"] == today


def test_yesterday_clears_follow_flag(monkeypatch):
    state = _FakeSessionState({"at_date_follows_today": True})
    monkeypatch.setattr(erp.st, "session_state", state)
    yesterday = datetime.date(2026, 6, 9)
    erp._mob_at_set_date_choice(yesterday, follows_today=False)
    assert state["at_date_follows_today"] is False
    assert state["at_date"] == yesterday


def test_custom_clears_follow_flag(monkeypatch):
    state = _FakeSessionState({"at_date_follows_today": True})
    monkeypatch.setattr(erp.st, "session_state", state)
    custom = datetime.date(2026, 5, 1)
    erp._mob_at_set_date_choice(custom, follows_today=False)
    assert state["at_date_follows_today"] is False


def test_followed_today_rolls_over_on_date_boundary(monkeypatch):
    state = _FakeSessionState(
        {
            "at_date": datetime.date(2000, 1, 1),
            "at_date_follows_today": True,
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_apply_date_follow_today()
    assert state["at_date"] == datetime.date.today()


def test_explicit_yesterday_survives_date_boundary(monkeypatch):
    pinned = datetime.date(2026, 6, 9)
    state = _FakeSessionState(
        {
            "at_date": pinned,
            "at_date_follows_today": False,
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_apply_date_follow_today()
    assert state["at_date"] == pinned


def test_ensure_defaults_sets_follow_flag_on_first_date(monkeypatch):
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_ensure_defaults(MagicMock(), "Expense", "USD", [])
    assert state["at_date_follows_today"] is True


def test_company_switch_clears_follow_flag():
    sys.modules["streamlit"].session_state["at_date_follows_today"] = True
    erp._clear_company_scoped_session_state()
    assert "at_date_follows_today" not in sys.modules["streamlit"].session_state


# ── Repeat compatibility ──────────────────────────────────────────────────────


def test_repeat_sets_date_to_today_and_follow_flag(monkeypatch, db):
    state = _FakeSessionState({"active_company_id": 1})
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "load_settings", lambda: {"currency": "USD"})
    monkeypatch.setattr(erp, "_current_company_id", lambda: 1)
    monkeypatch.setattr(erp, "_txh_repeat_eligible", lambda *a, **k: True)
    monkeypatch.setattr(erp, "_txh_clear_repeat_forbidden_session_keys", lambda: None)
    monkeypatch.setattr(erp, "_txh_resolve_active_category", lambda *a, **k: None)
    monkeypatch.setattr(erp, "_txh_resolve_active_subcategory", lambda *a, **k: None)
    monkeypatch.setattr(erp, "_txh_coerce_repeat_payment_method", lambda *a, **k: "Cash")
    monkeypatch.setattr(erp, "_at_clear_stale_payment_account_keys", lambda _pm: None)
    monkeypatch.setattr(erp, "_mobile_close_app_surfaces", lambda: None)
    expense = SimpleNamespace(
        amount=10,
        description="",
        payment_method="Cash",
        tx_category_id=None,
        tx_subcategory_id=None,
        currency="USD",
        is_void=False,
        company_id=1,
    )
    erp._txh_apply_repeat_prefill(db, "ExpenseRecord", expense)
    assert state["at_date"] == datetime.date.today()
    assert state["at_date_follows_today"] is True


# ── Closed-period courtesy check ──────────────────────────────────────────────


def test_entry_date_posting_blocked_matches_journal_guard(db):
    fp = models.FiscalPeriod(
        name="May 2026",
        start_date=datetime.date(2026, 5, 1),
        end_date=datetime.date(2026, 5, 31),
        is_closed=True,
        closed_at=datetime.date(2026, 6, 1),
    )
    db.add(fp)
    db.commit()
    blocked = datetime.date(2026, 5, 15)
    msg = erp._entry_date_posting_blocked(db, blocked)
    assert msg is not None
    assert "closed" in msg.lower()
    # PS-P1: guard kernel lives in services/posting.py; app.py shims delegate.
    guard_src = inspect.getsource(erp._entry_date_posting_blocked)
    je_src = inspect.getsource(erp.create_journal_entry)
    assert "posting_service.entry_date_posting_blocked(" in guard_src
    assert "company_id=_current_company_id()" in guard_src
    assert "posting_service.create_journal_entry(" in je_src
    assert (
        "company_id=company_id or _current_company_id()" in je_src
        or "resolve_company_id_for_posting" in je_src
    )
    posting_src = (Path(__file__).resolve().parents[1] / "services" / "posting.py").read_text(
        encoding="utf-8"
    )
    assert "def entry_date_posting_blocked(" in posting_src
    assert "FiscalPeriod" in posting_src and "YearEndClose" in posting_src


def test_date_picker_uses_posting_blocked_helper():
    notice_src = inspect.getsource(erp._mob_at_render_date_closed_period_notice)
    assert "_entry_date_posting_blocked" in notice_src
    picker_src = inspect.getsource(erp._mob_at_render_date_picker_sheet)
    assert "_mob_at_render_date_closed_period_notice" in picker_src


# ── Backdated marker + sheet labels ───────────────────────────────────────────


def test_backdated_marker_renders_only_when_not_today(monkeypatch):
    state = _FakeSessionState({"at_date": datetime.date(2026, 6, 8)})
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._mob_at_date_is_backdated() is True
    row_src = inspect.getsource(erp._mob_at_render_c_row1)
    assert "erp-mob-at-date-backdated-marker" in row_src
    assert "_mob_at_date_is_backdated" in row_src

    state["at_date"] = datetime.date.today()
    assert erp._mob_at_date_is_backdated() is False


def test_sheet_labels_contain_weekday_and_date():
    d = datetime.date(2026, 6, 10)
    detail = erp._mob_at_weekday_date_detail(d)
    assert detail.split()[0] in {
        "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun",
    }
    picker_src = inspect.getsource(erp._mob_at_render_date_picker_sheet)
    assert "_mob_at_date_quick_label" in picker_src
    assert "txn.mob.date_today_choice" in picker_src
    assert "txn.mob.date_yesterday_choice" in picker_src
    assert "txn.mob.date_custom_choice" in picker_src


def test_backdated_css_contract():
    from pathlib import Path

    css = (Path(__file__).resolve().parents[1] / "ui" / "mobile_txn.css").read_text(
        encoding="utf-8"
    )
    assert "erp-mob-at-date-backdated-marker" in css
    assert "st-key-mob_at_c_date_btn" in css


# ── Desktop unchanged ─────────────────────────────────────────────────────────


def test_desktop_date_field_is_single_native_date_input():
    """UX-STABILIZE-03: desktop AT has one native st.date_input (key=at_date)."""
    src = inspect.getsource(erp.render_add_transaction)
    form_pos = src.index('st.form("at_entry_form"')
    assert "_at_render_desktop_date_field()" in src
    assert src.index("_at_render_desktop_date_field()") > form_pos
    date_helper = inspect.getsource(erp._at_render_desktop_date_field)
    assert 'key="at_date"' in date_helper
    assert "st.date_input" in date_helper
    assert date_helper.count("st.date_input") == 1
    for banned in ("st.checkbox", "st.expander", "st.popover", "render_preferred_date_input",
                   "show_calendar", "at_date_manual_entry"):
        assert banned not in date_helper
    desktop_host = src.split('with st.container(key="erp_at_desktop_host")', 1)[1]
    assert "_mob_at_render_date_picker_sheet" not in desktop_host
    mobile_src = inspect.getsource(erp._render_add_transaction_mobile)
    assert "_mob_at_apply_date_follow_today" in mobile_src
