"""THEME-FLASH-01 — anti-flash bootstrap contract tests."""

from __future__ import annotations

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
    st.html = MagicMock()
    st.iframe = MagicMock()
    sys.modules["streamlit"] = st
    sys.path.insert(0, str(ROOT))
    import importlib.util

    spec = importlib.util.spec_from_file_location("ui.theme_flash_test", ROOT / "ui" / "theme.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.st.session_state = st.session_state
    mod.st.markdown = st.markdown
    mod.st.html = st.html
    mod.st.iframe = st.iframe
    mod.st.context = types.SimpleNamespace(cookies={}, headers={})
    try:
        yield mod, st
    finally:
        st.session_state.clear()
        if saved is not None:
            sys.modules["streamlit"] = saved


def _style_bundle(st) -> str:
    calls = [
        c.args[0] for c in st.html.call_args_list if c.args and "<style>" in c.args[0]
    ]
    assert len(calls) == 1
    return calls[0]


def test_explicit_dark_prefixes_dark_root_before_light_defaults(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "dark"
    st.context = types.SimpleNamespace(cookies={"erp_os_dark": "0"}, headers={})
    st.markdown.reset_mock()
    st.html.reset_mock()
    theme.bootstrap_theme(lambda: MagicMock(), None)
    bundle = _style_bundle(st)
    dark_bg = theme.DARK_ROOT_VARS["--theme-bg"]
    assert dark_bg in bundle
    assert bundle.index(dark_bg) < bundle.find("#f8fafc")
    script_calls = [c.args[0] for c in st.html.call_args_list if c.args and "data-erp-theme" in c.args[0]]
    assert script_calls and "dark" in script_calls[0]
    assert bundle.count(":root{") == 1


def test_explicit_light_stays_light_single_bundle(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "light"
    st.markdown.reset_mock()
    theme.bootstrap_theme(lambda: MagicMock(), None)
    bundle = _style_bundle(st)
    assert theme.LIGHT_ROOT_VARS["--theme-bg"] in bundle
    assert theme.DARK_ROOT_VARS["--theme-bg"] not in bundle.split("<style>", 1)[1][:200]


def test_system_mode_without_os_hint_keeps_media_fallback(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "system"
    st.context = types.SimpleNamespace(cookies={}, headers={})
    st.html.reset_mock()
    theme.bootstrap_theme(lambda: MagicMock(), None)
    bundle = _style_bundle(st)
    assert ":root{" not in bundle[:200]
    assert 'html[data-erp-theme="system"] :root' in bundle
    assert "prefers-color-scheme: dark" in bundle


def test_system_mode_with_os_cookie_injects_known_scheme(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "system"
    st.context = types.SimpleNamespace(cookies={"erp_os_dark": "1"}, headers={})
    st.markdown.reset_mock()
    theme.bootstrap_theme(lambda: MagicMock(), None)
    bundle = _style_bundle(st)
    assert theme.DARK_ROOT_VARS["--theme-bg"] in bundle
    assert bundle.index(theme.DARK_ROOT_VARS["--theme-bg"]) < bundle.find("#f8fafc")


def test_no_separate_theme_override_block(theme_module):
    theme, st = theme_module
    st.session_state["theme_mode"] = "dark"
    st.html.reset_mock()
    theme.bootstrap_theme(lambda: MagicMock(), None)
    style_blocks = [
        c.args[0] for c in st.html.call_args_list if c.args and "<style>" in c.args[0]
    ]
    assert len(style_blocks) == 1


def test_main_restores_auth_before_bootstrap_theme():
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    main_block = app_src.split("def main():", 1)[1].split("\nif __name__", 1)[0]
    restore_idx = main_block.index("_early_restore_auth_session()")
    bootstrap_idx = main_block.index("bootstrap_theme(")
    assert restore_idx < bootstrap_idx


def test_strip_first_root_block_removes_theme_css_defaults(theme_module):
    theme, _st = theme_module
    sample = ":root { --theme-bg: #f8fafc; }\n.rule { color: red; }"
    stripped = theme._strip_first_root_block(sample)
    assert stripped.startswith(".rule")
    assert "#f8fafc" not in stripped
