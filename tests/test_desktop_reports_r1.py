"""REPORTS-DESKTOP-01 R1 + REPORTS-DESKTOP-02 — Reports chip selector ownership."""
from __future__ import annotations

import inspect
from pathlib import Path

import app as erp
from ui.theme import load_theme_css

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_CSS = ROOT / "ui" / "desktop_reports.css"
MOBILE_CSS = ROOT / "ui" / "mobile_reports.css"
THEME_PY = ROOT / "ui" / "theme.py"


def _read(name: str) -> str:
    return (ROOT / "ui" / name).read_text(encoding="utf-8")


def test_desktop_reports_css_registered_in_theme_loader():
    assert DESKTOP_CSS.is_file()
    theme_py = THEME_PY.read_text(encoding="utf-8")
    assert "desktop_reports.css" in theme_py
    assert "_DESKTOP_REPORTS_CSS_PATH" in theme_py
    bundled = load_theme_css()
    assert DESKTOP_CSS.read_text(encoding="utf-8") in bundled


def test_mgmt_report_select_chips_only_no_desktop_selectbox():
    src = inspect.getsource(erp._mgmt_report_select)
    assert "mob_rpt_sel_" in src
    assert "erp-rpt-sel-chip-host" in src
    assert "st.selectbox" not in src
    assert "erp_rpt_sel_desktop_" not in src
    assert "erp-rpt-sel-desktop-host" not in src
    assert "return st.session_state[widget_key]" in src


def test_render_reports_no_desktop_selectbox_references():
    src = inspect.getsource(erp.render_reports)
    assert "erp_rpt_sel_desktop_" not in src


def test_chip_layout_in_desktop_reports_css():
    css = _read("desktop_reports.css")
    assert "REPORTS-DESKTOP-02" in css
    assert "erp-rpt-sel-chip-host" in css
    assert "st-key-mob_rpt_sel_" in css
    assert "grid-template-columns: repeat(2" in css
    assert "display: none" not in css


def test_mobile_reports_no_desktop_selectbox_visibility_rules():
    css = _read("mobile_reports.css")
    assert "erp_rpt_sel_desktop_" not in css
    assert "erp-rpt-sel-desktop-host" not in css


def test_desktop_reports_not_in_mobile_viewport_owner_list():
    theme_py = THEME_PY.read_text(encoding="utf-8")
    block = theme_py.split("MOBILE_VIEWPORT_CSS_OWNER_FILES")[1].split(")")[0]
    assert "desktop_reports.css" not in block
