"""UI-REGRESSION-01 — Dashboard charts must follow the OS scheme when theme = "system".

Root cause: Altair charts render server-side with palette hex. When theme_mode is
"system", _resolve_chart_dark must read erp_os_dark (viewport detector), client
hints, or sticky session — not default dark_mode=False. Dashboard 7-day trend uses
render_themed_grouped_bar in render_dashboard().
"""

from __future__ import annotations

import inspect
import re
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
THEME_PY = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
APP_PY = (ROOT / "app.py").read_text(encoding="utf-8")


def test_viewport_detector_writes_os_dark_cookie():
    detector = THEME_PY.split("def inject_mobile_viewport_detector", 1)[1]
    detector = detector.split("def ", 1)[0]
    assert "prefers-color-scheme: dark" in detector, "detector must read OS scheme"
    assert "erp_os_dark" in detector, "detector must write erp_os_dark cookie"
    assert 'addEventListener("change"' in detector, (
        "detector must update the cookie when the OS scheme changes live"
    )


def test_chart_dark_resolver_delegates_to_resolve_effective_dark():
    resolver = THEME_PY.split("def _resolve_chart_dark", 1)[1].split("\ndef ", 1)[0]
    assert "resolve_effective_dark" in resolver
    effective = THEME_PY.split("def resolve_effective_dark", 1)[1].split("\ndef ", 1)[0]
    assert "sync_os_dark_flag_from_cookie" in effective
    sync_src = THEME_PY.split("def sync_os_dark_flag_from_cookie", 1)[1].split("\ndef ", 1)[0]
    assert "erp_os_dark" in sync_src
    assert "dark_mode" not in sync_src
    assert "_os_dark_preferred_signal" in sync_src
    hint_src = THEME_PY.split("def _os_dark_preferred_signal", 1)[1].split("\ndef ", 1)[0]
    assert "_os_dark_from_client_hint" in hint_src


def test_dashboard_7day_trend_uses_render_themed_grouped_bar():
    """Actual Dashboard chart path — not Banking."""
    dash = APP_PY.split("def render_dashboard", 1)[1].split("\ndef ", 1)[0]
    assert "render_themed_grouped_bar" in dash
    assert "st.bar_chart" not in dash and "st.line_chart" not in dash
    assert "last_7_days" in dash or "dash.last_7_days" in dash


@pytest.fixture
def theme_module():
    saved_streamlit = sys.modules.get("streamlit")
    saved_ui_theme = sys.modules.get("ui.theme")
    st = types.ModuleType("streamlit")
    st.session_state = {}
    st.markdown = MagicMock()
    st.iframe = MagicMock()
    st.altair_chart = MagicMock()
    sys.modules["streamlit"] = st
    sys.path.insert(0, str(ROOT))
    import importlib.util

    spec = importlib.util.spec_from_file_location("ui.theme_chart_test", ROOT / "ui" / "theme.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        yield mod, st
    finally:
        st.session_state.clear()
        if saved_streamlit is not None:
            sys.modules["streamlit"] = saved_streamlit
        elif "streamlit" in sys.modules:
            del sys.modules["streamlit"]
        if saved_ui_theme is not None:
            sys.modules["ui.theme"] = saved_ui_theme
        elif "ui.theme" in sys.modules:
            del sys.modules["ui.theme"]


def test_dashboard_grouped_bar_dark_axis_when_system_os_cookie(theme_module):
    """render_themed_grouped_bar (Dashboard path) must use dark axis tokens; bg transparent."""
    theme, st = theme_module
    st.session_state["theme_mode"] = "system"
    st.session_state["dark_mode"] = False
    st.context = types.SimpleNamespace(
        cookies={"erp_os_dark": "1"},
        headers={},
    )
    df = pd.DataFrame({"Date": ["01 Jan"], "Sales": [10.0], "Expenses": [5.0]})
    theme.render_themed_grouped_bar(df, "Date", ["Sales", "Expenses"])
    st.altair_chart.assert_called_once()
    chart = st.altair_chart.call_args[0][0]
    cfg = chart.to_dict()["config"]
    assert cfg["background"] == "transparent"
    assert cfg["axis"]["labelColor"] == theme.DARK_ROOT_VARS["--theme-muted"]


def test_bootstrap_system_injects_only_when_os_scheme_known(theme_module):
    theme, st = theme_module
    st.session_state.clear()
    st.session_state["theme_mode"] = "system"
    st.session_state["dark_mode"] = False
    st.context = types.SimpleNamespace(cookies={}, headers={})
    st.markdown.reset_mock()
    theme.bootstrap_theme(lambda: MagicMock(), None)
    inject_calls = [
        c.args[0] for c in st.markdown.call_args_list if c.args and ":root{" in c.args[0]
    ]
    assert inject_calls == [], "system + unknown OS — no forced :root injection"
    st.session_state.clear()
    st.session_state["theme_mode"] = "system"
    st.context = types.SimpleNamespace(cookies={"erp_os_dark": "1"}, headers={})
    st.markdown.reset_mock()
    theme.bootstrap_theme(lambda: MagicMock(), None)
    inject_calls = [
        c.args[0] for c in st.markdown.call_args_list if c.args and ":root{" in c.args[0]
    ]
    assert len(inject_calls) == 1, "global CSS + marker + dark :root when cookie known"
    assert theme.DARK_ROOT_VARS["--theme-bg"] in inject_calls[0]


def test_chart_palettes_not_white_in_dark():
    """Dark chart axis tokens must never resolve to a white card (shell is CSS-owned)."""
    import sys, types, importlib.util

    stl = types.ModuleType("streamlit")
    stl.session_state = {}
    stl.markdown = lambda *a, **k: None
    stl.iframe = lambda *a, **k: None
    sys.modules.setdefault("streamlit", stl)
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("ui.theme", ROOT / "ui" / "theme.py")
    theme = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(theme)

    dark_tokens = theme.chart_theme_tokens(dark=True)
    for key in ("bg", "card"):
        assert dark_tokens[key].lower() not in ("#fff", "#ffffff"), (
            f"dark chart {key} must not be white: {dark_tokens[key]}"
        )
    light_tokens = theme.chart_theme_tokens(dark=False)
    assert light_tokens["bg"].lower() != dark_tokens["bg"].lower(), (
        "light and dark chart palettes must differ"
    )


def test_banking_locale_keys_complete():
    """No raw locale keys in Banking surfaces — every banking.* key used in app.py
    must exist in the locale catalogs (EN block guarantees the rendered string)."""
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    used = set(re.findall(r'_tf?\(\s*"(banking\.[a-z0-9_.]+)"', src))
    catalogs = (
        (ROOT / "registry" / "locales" / "transactional.py").read_text(encoding="utf-8")
        + (ROOT / "registry" / "locales" / "messages.py").read_text(encoding="utf-8")
    )
    missing = sorted(k for k in used if f'"{k}"' not in catalogs)
    assert not missing, f"raw locale keys would render in Banking: {missing[:8]}"


def test_all_altair_charts_wrapped_in_theme():
    """Every st.altair_chart call must go through apply_altair_theme."""
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    for m in re.finditer(r"st\.altair_chart\(", src):
        window = src[m.end(): m.end() + 120]
        before = src[max(0, m.start() - 40): m.start()]
        assert "apply_altair_theme" in window or "apply_altair_theme" in before, (
            f"unthemed chart near offset {m.start()}: {window[:80]!r}"
        )
    assert "st.bar_chart" not in src and "st.line_chart" not in src, (
        "native Streamlit charts bypass the ERP theme — use Altair + apply_altair_theme"
    )
