"""CHART-01 — ERP chart theme helpers."""

import sys
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
    sys.modules["streamlit"].session_state = {}

import altair as alt

from ui.theme import (
    DARK_ROOT_VARS,
    LIGHT_ROOT_VARS,
    apply_altair_theme,
    chart_accent_color,
    chart_palette,
    chart_reference_color,
    chart_series_color,
    chart_theme_tokens,
)


@pytest.fixture(autouse=True)
def _reset_theme_session():
    st = sys.modules["streamlit"]
    st.session_state.clear()
    st.session_state["theme_mode"] = "light"
    st.session_state["dark_mode"] = False
    yield
    st.session_state.clear()


def test_chart_theme_tokens_light():
    tokens = chart_theme_tokens(dark=False)
    assert tokens["card"] == LIGHT_ROOT_VARS["--theme-card"]
    assert tokens["text"] == LIGHT_ROOT_VARS["--theme-text"]
    assert tokens["border"] == LIGHT_ROOT_VARS["--theme-border"]
    assert tokens["info"] == LIGHT_ROOT_VARS["--theme-info"]


def test_chart_theme_tokens_dark():
    tokens = chart_theme_tokens(dark=True)
    assert tokens["card"] == DARK_ROOT_VARS["--theme-card"]
    assert tokens["text"] == DARK_ROOT_VARS["--theme-text"]
    assert tokens["info"] == DARK_ROOT_VARS["--theme-info"]


def test_chart_theme_tokens_follows_session_dark_mode():
    st = sys.modules["streamlit"]
    st.session_state["theme_mode"] = "dark"
    st.session_state["dark_mode"] = True
    assert chart_theme_tokens()["card"] == DARK_ROOT_VARS["--theme-card"]


def test_chart_theme_tokens_explicit_light_overrides_dark_session():
    st = sys.modules["streamlit"]
    st.session_state["theme_mode"] = "dark"
    st.session_state["dark_mode"] = True
    assert chart_theme_tokens(dark=False)["card"] == LIGHT_ROOT_VARS["--theme-card"]


def test_chart_accent_and_palette_use_tokens():
    assert chart_accent_color(dark=False) == LIGHT_ROOT_VARS["--theme-info"]
    palette = chart_palette(dark=False)
    assert len(palette) == 4
    assert palette[0] == LIGHT_ROOT_VARS["--theme-info"]
    assert palette[1] == LIGHT_ROOT_VARS["--theme-muted"]


def test_chart_series_and_reference_delegate_to_tokens():
    assert chart_series_color() == chart_theme_tokens()["muted"]
    assert chart_reference_color() == chart_theme_tokens()["border"]


def test_apply_altair_theme_configures_background_and_axis():
    import pandas as pd

    chart = alt.Chart(pd.DataFrame({"x": [1], "y": [2]})).mark_bar().encode(x="x", y="y")
    themed = apply_altair_theme(chart, dark=False)
    cfg = themed.to_dict()["config"]
    assert cfg["background"] == LIGHT_ROOT_VARS["--theme-card"]
    assert cfg["axis"]["labelColor"] == LIGHT_ROOT_VARS["--theme-muted"]
    assert cfg["title"]["color"] == LIGHT_ROOT_VARS["--theme-text"]


def test_app_no_native_streamlit_charts():
    from pathlib import Path

    app = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "st.bar_chart(" not in app
    assert "st.line_chart(" not in app


def test_widgets_chart_container_uses_theme_card():
    from pathlib import Path

    widgets = (Path(__file__).resolve().parents[1] / "ui" / "widgets.css").read_text(
        encoding="utf-8"
    )
    block = widgets.split("/* CHART-01", 1)[1].split("/* ── Alerts", 1)[0]
    assert "stVegaLiteChart" in block
    assert "var(--theme-card)" in block
    assert "var(--theme-border)" in block
