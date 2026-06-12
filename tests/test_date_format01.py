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


def test_desktop_date_field_uses_shared_preferred_input():
    src = inspect.getsource(erp._at_render_desktop_date_field)
    assert "render_preferred_date_input" in src
    assert "in_form=True" in src
    assert "isoformat()" not in src


def test_mobile_custom_date_uses_shared_preferred_input():
    src = inspect.getsource(erp._mob_at_render_date_picker_sheet)
    assert "render_preferred_date_input" in src
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
    assert "DATE_FORMAT_OPTIONS" in src
    assert '"DD MMM YYYY"' not in src


# ── DATE-MASK-01 — auto separators ───────────────────────────────────────────


@pytest.mark.parametrize(
    "pref,raw,expected",
    [
        ("DD.MM.YYYY", "03062026", "03.06.2026"),
        ("DD/MM/YYYY", "03062026", "03/06/2026"),
        ("YYYY-MM-DD", "20260603", "2026-06-03"),
        ("DD.MM.YYYY", "03", "03"),
        ("DD.MM.YYYY", "0306", "03.06"),
        ("DD/MM/YYYY", "0306", "03/06"),
        ("YYYY-MM-DD", "2026", "2026"),
        ("YYYY-MM-DD", "202606", "2026-06"),
    ],
)
def test_format_date_input_for_preference_masks(pref, raw, expected):
    assert erp.format_date_input_for_preference(raw, pref) == expected


@pytest.mark.parametrize(
    "pref,raw,expected",
    [
        ("DD.MM.YYYY", "03.06.2026", datetime.date(2026, 6, 3)),
        ("DD/MM/YYYY", "03/06/2026", datetime.date(2026, 6, 3)),
        ("YYYY-MM-DD", "2026-06-03", datetime.date(2026, 6, 3)),
        ("DD.MM.YYYY", "03062026", datetime.date(2026, 6, 3)),
        ("DD/MM/YYYY", "03062026", datetime.date(2026, 6, 3)),
        ("YYYY-MM-DD", "20260603", datetime.date(2026, 6, 3)),
    ],
)
def test_parse_date_text_pasted_and_digits(pref, raw, expected):
    assert erp.parse_date_text(raw, pref) == expected


@pytest.mark.parametrize(
    "raw",
    ["31022026", "31.02.2026", "31/02/2026"],
)
def test_parse_date_text_rejects_impossible_dates(raw):
    assert erp.parse_date_text(raw, "DD.MM.YYYY") is None


def test_normalize_date_digits_strips_non_digits():
    assert erp.normalize_date_digits("03.06.2026") == "03062026"
    assert erp.normalize_date_digits("ab03cd06") == "0306"


def test_resolve_entry_date_digit_only_masks_on_save(monkeypatch):
    state = _FakeSessionState(
        {
            "_user_date_format": "DD.MM.YYYY",
            "at_date_text": "03062026",
            "at_date": datetime.date(2020, 1, 1),
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    resolved = erp._at_resolve_entry_date()
    assert resolved == datetime.date(2026, 6, 3)
    assert isinstance(resolved, datetime.date)
    assert state["at_date_text"] == "03.06.2026"


def test_desktop_date_field_single_widget_with_mask_helper():
    src = inspect.getsource(erp._at_render_desktop_date_field)
    assert "render_preferred_date_input" in src
    assert "in_form=True" in src
    assert "st.text_input" not in src
    for banned in ("st.checkbox", "st.date_input", "st.expander", "st.popover"):
        assert banned not in src
