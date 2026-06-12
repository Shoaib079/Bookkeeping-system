"""DATE-FORMAT-01 — Add Transaction respects profile date-format preference."""

from __future__ import annotations

import datetime
import inspect
import sys
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

import app as erp


class _FakeSessionState(dict):
    def get(self, key, default=None):
        return super().get(key, default)


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.mark.parametrize(
    "pref,expected",
    [
        ("DD.MM.YYYY", "12.06.2026"),
        ("YYYY-MM-DD", "2026-06-12"),
        ("DD/MM/YYYY", "12/06/2026"),
    ],
)
def test_format_date_for_user_pref_displays_preference(pref, expected):
    d = datetime.date(2026, 6, 12)
    assert erp._format_date_for_user_pref(d, pref) == expected


@pytest.mark.parametrize(
    "legacy,canonical",
    [
        ("DD MMM YYYY", "DD.MM.YYYY"),
        ("MM/DD/YYYY", "DD/MM/YYYY"),
    ],
)
def test_canonical_user_date_format_maps_legacy_profile_values(legacy, canonical):
    assert erp._canonical_user_date_format(legacy) == canonical


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2026-06-12", datetime.date(2026, 6, 12)),
        ("12.06.2026", datetime.date(2026, 6, 12)),
        ("12/06/2026", datetime.date(2026, 6, 12)),
    ],
)
def test_parse_date_text_remains_format_agnostic(raw, expected):
    assert erp._at_parse_date_text(raw) == expected


@pytest.mark.parametrize("pref", ["DD.MM.YYYY", "YYYY-MM-DD", "DD/MM/YYYY"])
@pytest.mark.parametrize(
    "typed",
    ["2026-06-12", "12.06.2026", "12/06/2026"],
)
def test_resolve_entry_date_stores_same_underlying_date(pref, typed, monkeypatch):
    state = _FakeSessionState(
        {
            "_user_date_format": pref,
            "at_date_text": typed,
            "at_date": datetime.date(2020, 1, 1),
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    resolved = erp._at_resolve_entry_date()
    assert resolved == datetime.date(2026, 6, 12)
    assert state["at_date"] == datetime.date(2026, 6, 12)
    assert state["at_date_text"] == erp._format_date_for_user_pref(
        datetime.date(2026, 6, 12), pref
    )


def test_refresh_date_text_display_uses_active_preference(monkeypatch):
    state = _FakeSessionState(
        {
            "_user_date_format": "DD.MM.YYYY",
            "at_date": datetime.date(2026, 6, 12),
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_refresh_date_text_display()
    assert state["at_date_text"] == "12.06.2026"
    assert state["mob_at_date_custom_str"] == "12.06.2026"


def test_desktop_date_field_uses_preference_formatter_not_isoformat():
    src = inspect.getsource(erp._at_render_desktop_date_field)
    assert "_format_at_display_date" in src
    assert "isoformat()" not in src
    assert "_at_date_input_placeholder()" in src


def test_mobile_custom_date_uses_preference_formatter():
    src = inspect.getsource(erp._mob_at_render_date_picker_sheet)
    assert "_format_at_display_date" in src
    assert "_at_date_input_placeholder()" in src
    assert "isoformat()" not in src


def test_mobile_row1_date_label_uses_preference_formatter(monkeypatch):
    state = _FakeSessionState(
        {
            "_user_date_format": "DD/MM/YYYY",
            "at_date": datetime.date(2026, 6, 12),
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._mob_at_c_row1_date_label() == "12/06/2026"


def test_profile_date_format_options_are_canonical():
    src = inspect.getsource(erp.render_my_account)
    assert "_DATE_FORMAT_OPTIONS" in src
    assert '"DD MMM YYYY"' not in src
