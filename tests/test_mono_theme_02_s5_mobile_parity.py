"""MONO-THEME-02-S5 — mobile parity contract tests.

Bottom-nav active grammar, KPI chips, hub sheets, and table density must match
desktop MONO-THEME grammar tokens — no widgets.css mob_bar override drift.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = ROOT / "ui" / "theme.css"
WIDGETS_CSS = ROOT / "ui" / "widgets.css"
SHELL_CSS = ROOT / "ui" / "mobile_shell.css"
CONTRACT_DOC = ROOT / "docs" / "MONO_THEME_02_VISUAL_CONTRACT.md"

ACTIVE_NAV_KEYS = (
    "--erp-nav-active-bg",
    "--erp-nav-active-fg",
    "--erp-nav-active-bar",
)

CARD_SURFACE_KEYS = (
    "--erp-card-bg",
    "--erp-card-border",
    "--erp-card-radius",
    "--erp-card-shadow",
)


@pytest.fixture(scope="module")
def theme_css() -> str:
    return THEME_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def widgets_css() -> str:
    return WIDGETS_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def shell_css() -> str:
    return SHELL_CSS.read_text(encoding="utf-8")


def _s5_theme_block(css: str) -> str:
    start = css.index("MONO-THEME-02-S5 — mobile dashboard KPI")
    end = css.index("@media (min-width: 969px)", start)
    return css[start:end]


def _s5_widgets_block(css: str) -> str:
    start = css.index("MONO-THEME-02-S5 — mobile stTable density")
    return css[start : start + 900]


def _mobile_nav_block(css: str) -> str:
    idx = css.index("st-key-mob_bar_")
    return css[idx : idx + 4500]


def test_s5_marker_present(theme_css, widgets_css, shell_css):
    assert "MONO-THEME-02-S5" in theme_css
    assert "MONO-THEME-02-S5" in widgets_css
    assert "MONO-THEME-02-S5" in shell_css


def test_s5_theme_mobile_media_only(theme_css):
    block = _s5_theme_block(theme_css)
    assert "max-width: 968px" in theme_css[: theme_css.index("MONO-THEME-02-S5")]
    assert "min-width: 969px" not in block


def test_s5_widgets_no_mob_bar_override(widgets_css):
    """widgets.css must not reset bottom-nav active to flat theme-info."""
    assert "mob_bar_" not in _s5_widgets_block(widgets_css)
    mobile_ui1 = widgets_css.split("MONO-THEME-02-S5")[0].split("UI-1 — Mobile chrome")[1]
    assert 'button[kind="primary"]:not([class*="mob_bar_new"])' not in mobile_ui1
    assert "color: var(--theme-info) !important" not in mobile_ui1.split("mob_bar", 1)[0] if "mob_bar" in mobile_ui1 else True


def test_s5_mobile_kpi_chips_use_card_grammar(theme_css):
    block = _s5_theme_block(theme_css)
    chip = block.split(".erp-dash-mobile-kpi-chip")[1][:400]
    for key in CARD_SURFACE_KEYS:
        assert f"var({key})" in chip, f"mobile KPI chip missing {key}"


def test_s5_mobile_arap_host_uses_card_grammar(theme_css):
    block = _s5_theme_block(theme_css)
    assert "erp-dash-mobile-arap-host" in block
    host = block.split("erp-dash-mobile-arap-host")[1][:350]
    assert "var(--erp-card-bg)" in host
    assert "var(--erp-card-border)" in host
    assert "var(--erp-card-shadow)" in host


def test_s5_mobile_table_density(theme_css, widgets_css):
    tblock = _s5_theme_block(theme_css)
    wblock = _s5_widgets_block(widgets_css)
    assert "padding: 8px 10px" in tblock
    assert ".erp-fin-table td" in tblock
    assert "padding: 8px 10px" in wblock
    assert "var(--erp-table-row-hover-bg)" in wblock


def test_s5_mobile_kpi_tabular_nums(theme_css):
    block = _s5_theme_block(theme_css)
    assert "tabular-nums" in block.split(".erp-dash-mobile-kpi-value")[1][:120]


@pytest.mark.parametrize("token", ACTIVE_NAV_KEYS)
def test_s5_bottom_nav_active_still_in_shell(shell_css, token):
    block = _mobile_nav_block(shell_css)
    assert f"var({token})" in block, f"mobile_shell bottom nav missing {token}"


def test_s5_hub_sheet_card_radius(shell_css):
    idx = shell_css.index("MONO-THEME-02-S5 — hub sheet")
    block = shell_css[idx : idx + 950]
    assert "var(--erp-card-radius)" in block
    assert "var(--erp-card-shadow)" in block


def test_s5_scope_no_desktop_sidebar(theme_css):
    block = _s5_theme_block(theme_css)
    assert "stSidebar" not in block
    assert "MONO-THEME-02-S1" not in block


def test_s5_no_route_or_logic_changes(theme_css, widgets_css, shell_css):
    for css in (theme_css, widgets_css, shell_css):
        s5 = css.split("MONO-THEME-02-S5", 1)[1][:1200] if "MONO-THEME-02-S5" in css else ""
        if s5:
            assert "react_route" not in s5
            assert "registry/navigation" not in s5


def test_s5_widgets_mob_bar_not_owned(widgets_css):
    """Regression: widgets must not own mob_bar button resets (mobile_shell.css)."""
    assert not re.search(
        r'st-key-mob_bar_[\s\S]{0,200}?background:\s*transparent\s*!important',
        widgets_css,
    )


def test_contract_doc_lists_s5():
    text = CONTRACT_DOC.read_text(encoding="utf-8")
    assert "MONO-THEME-02-S5" in text
