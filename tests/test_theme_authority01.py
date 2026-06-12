"""THEME-AUTHORITY-01 — single source of truth for app + chart theme."""

from __future__ import annotations

import inspect
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def theme_module():
    saved = sys.modules.get("streamlit")
    st = types.ModuleType("streamlit")
    st.session_state = {}
    st.markdown = MagicMock()
    st.iframe = MagicMock()
    sys.modules["streamlit"] = st
    sys.path.insert(0, str(ROOT))
    import importlib.util

    spec = importlib.util.spec_from_file_location("ui.theme_auth_test", ROOT / "ui" / "theme.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.st.session_state = st.session_state
    mod.st.markdown = st.markdown
    mod.st.iframe = st.iframe
    mod.st.context = types.SimpleNamespace(cookies={}, headers={})
    try:
        yield mod, st
    finally:
        st.session_state.clear()
        if saved is not None:
            sys.modules["streamlit"] = saved


def test_explicit_light_ignores_dark_os_cookie(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "light"
    st.session_state["dark_mode"] = False
    st.context = types.SimpleNamespace(cookies={"erp_os_dark": "1"}, headers={})
    assert theme.resolve_effective_dark() is False
    assert theme.chart_theme_tokens()["card"] == theme.LIGHT_ROOT_VARS["--theme-card"]
    assert theme.sync_os_dark_flag_from_cookie() is False


def test_explicit_dark_ignores_light_os_cookie(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "dark"
    st.session_state["dark_mode"] = True
    st.context = types.SimpleNamespace(cookies={"erp_os_dark": "0"}, headers={})
    assert theme.resolve_effective_dark() is True
    assert theme.chart_theme_tokens()["card"] == theme.DARK_ROOT_VARS["--theme-card"]
    assert theme.sync_os_dark_flag_from_cookie() is True


def test_system_mode_follows_os_cookie(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "system"
    st.session_state["dark_mode"] = False
    st.context = types.SimpleNamespace(cookies={"erp_os_dark": "1"}, headers={})
    assert theme.resolve_effective_dark() is True
    assert theme.chart_theme_tokens()["card"] == theme.DARK_ROOT_VARS["--theme-card"]


def test_sync_os_dark_no_dark_mode_fallback(theme_module):
    theme, st = theme_module
    src = inspect.getsource(theme.sync_os_dark_flag_from_cookie)
    assert "dark_mode" not in src


def test_bootstrap_explicit_light_injects_light_vars(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "light"
    st.context = types.SimpleNamespace(cookies={"erp_os_dark": "1"}, headers={})
    st.markdown.reset_mock()
    theme.bootstrap_theme(lambda: MagicMock(), None)
    inject_calls = [
        c.args[0] for c in st.markdown.call_args_list if c.args and ":root{" in c.args[0]
    ]
    assert len(inject_calls) == 1
    assert theme.LIGHT_ROOT_VARS["--theme-bg"] in inject_calls[0]
    marker_calls = [
        c.args[0]
        for c in st.markdown.call_args_list
        if c.args and "data-erp-theme" in c.args[0] and "<script>" in c.args[0]
    ]
    assert marker_calls and "light" in marker_calls[0]


def test_bootstrap_system_no_inject_without_os_hint(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "system"
    st.context = types.SimpleNamespace(cookies={}, headers={})
    st.markdown.reset_mock()
    theme.bootstrap_theme(lambda: MagicMock(), None)
    inject_calls = [
        c.args[0] for c in st.markdown.call_args_list if c.args and ":root{" in c.args[0]
    ]
    assert inject_calls == []


def test_apply_altair_theme_transparent_background(theme_module):
    import altair as alt
    import pandas as pd

    theme, _st = theme_module
    chart = alt.Chart(pd.DataFrame({"x": [1], "y": [2]})).mark_bar().encode(x="x", y="y")
    themed = theme.apply_altair_theme(chart, dark=False)
    cfg = themed.to_dict()["config"]
    assert cfg["background"] == "transparent"
    assert cfg["view"]["fill"] == "transparent"
    assert cfg["axis"]["labelColor"] == theme.LIGHT_ROOT_VARS["--theme-muted"]


def test_theme_css_media_scoped_to_system():
    css = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")
    assert "THEME-AUTHORITY-01" in css
    assert 'html[data-erp-theme="system"] :root' in css
    assert "html:not([data-erp-theme]) :root" in css


def test_widgets_chart_background_transparent():
    css = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    block = css.split("CHART-01", 1)[1].split("/* ── Alerts", 1)[0]
    assert "rect.background" in block
    assert "transparent" in block
    assert "prefers-color-scheme: dark" not in block.split("rect.background")[1].split("/*")[0]


def test_company_picker_preserves_theme_mode():
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    block = app_src.split("def _go_to_company_picker", 1)[1].split("\ndef ", 1)[0]
    assert '"theme_mode"' in block


def test_ui_theme_exports_sync_derived_dark_mode():
    from ui.theme import sync_derived_dark_mode as imported_fn
    import ui.theme as theme_mod

    assert hasattr(theme_mod, "sync_derived_dark_mode")
    assert callable(theme_mod.sync_derived_dark_mode)
    assert imported_fn is theme_mod.sync_derived_dark_mode
    assert "sync_derived_dark_mode" in theme_mod.__all__


def test_sync_derived_dark_mode_import_and_call_no_crash(theme_module):
    from ui.theme import sync_derived_dark_mode as imported_fn

    theme, st = theme_module
    st.session_state["theme_mode"] = "light"
    st.context = types.SimpleNamespace(cookies={}, headers={})
    assert callable(imported_fn)
    # Call through fixture-loaded module: ui.theme may already be bound to real st.
    assert theme.sync_derived_dark_mode() is False


def test_sync_derived_dark_mode_explicit_light(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "light"
    st.context = types.SimpleNamespace(cookies={"erp_os_dark": "1"}, headers={})
    assert theme.sync_derived_dark_mode() is False
    assert st.session_state["dark_mode"] is False


def test_sync_derived_dark_mode_explicit_dark(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "dark"
    st.context = types.SimpleNamespace(cookies={"erp_os_dark": "0"}, headers={})
    assert theme.sync_derived_dark_mode() is True
    assert st.session_state["dark_mode"] is True


def test_sync_derived_dark_mode_system_follows_os_hint(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "system"
    st.context = types.SimpleNamespace(cookies={"erp_os_dark": "1"}, headers={})
    assert theme.sync_derived_dark_mode() is True
    assert st.session_state["dark_mode"] is True
    st.context = types.SimpleNamespace(cookies={"erp_os_dark": "0"}, headers={})
    assert theme.sync_derived_dark_mode() is False
    assert st.session_state["dark_mode"] is False
