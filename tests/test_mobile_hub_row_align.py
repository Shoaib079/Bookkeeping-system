"""MOBILE-HUB-ROW-ICON-ALIGN-01 / MOBILE-HUB-CHEVRON-ALIGN-01 — hub sheet rows."""
from __future__ import annotations

import inspect
from pathlib import Path

import app as erp

ROOT = Path(__file__).resolve().parents[1]


def _read_css(name: str) -> str:
    return (ROOT / "ui" / name).read_text(encoding="utf-8")


def test_mob_hub_icon_nav_row_helper_wires_svg_button_and_chevron():
    src = inspect.getsource(erp._mob_hub_icon_nav_row)
    assert 'key=f"mob_hub_row_{hub_key}_{item_idx}"' in src
    assert "nav_page_icon_html" in src
    assert 'key=f"mob_hub_{hub_key}_{item_idx}"' in src
    assert "_mobile_hub_nav" in src
    assert "chev_col" in src
    assert "erp-mob-hub-chevron" in src
    assert "st.columns([0.08, 0.84, 0.08]" in src


def test_render_mobile_hub_sheet_uses_icon_nav_row_for_page_and_accordion():
    src = inspect.getsource(erp._render_mobile_hub_sheet)
    assert "_mob_hub_icon_nav_row" in src
    assert 'st.columns([0.1, 0.9]' not in src
    assert src.count("_mob_hub_icon_nav_row(") >= 2


def test_mobile_hub_row_css_same_row_layout_in_mobile_shell():
    shell = _read_css("mobile_shell.css")
    assert "MOBILE-HUB-CHEVRON-ALIGN-01" in shell
    assert "st-key-mob_hub_row_" in shell
    assert "grid-template-columns: 28px minmax(0, 1fr) 20px" in shell
    assert "min-height: 44px" in shell


def test_mobile_hub_row_css_fixed_chevron_column():
    shell = _read_css("mobile_shell.css")
    assert "erp-mob-hub-chevron" in shell
    assert ":nth-child(3)" in shell
    assert "justify-self: end" in shell
    assert 'st-key-mob_hub_row_"] button::after' in shell
    assert "content: none" in shell


def test_bottom_nav_css_unchanged():
    shell = _read_css("mobile_shell.css")
    assert "st-key-erp_mob_bottom_bar" in shell
    assert "erp-mob-bar-ico" in shell
    # Hub row rules must not replace bottom-bar grid ownership.
    bottom_idx = shell.index("st-key-erp_mob_bottom_bar")
    hub_row_idx = shell.index("st-key-mob_hub_row_")
    assert bottom_idx < hub_row_idx


def test_desktop_nav_button_unchanged():
    src = inspect.getsource(erp._nav_page_button)
    assert "nav_page_icon_html" in src
    assert "def _nav_page_button" in inspect.getsource(erp)
