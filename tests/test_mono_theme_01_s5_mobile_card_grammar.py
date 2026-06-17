"""MONO-THEME-01-S5 — mobile card grammar migration contract tests.

Mobile KPI/list/sheet/form surfaces must reference the same ``--erp-card-*``
grammar tokens as desktop S4 (no new colors).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ui.design_tokens import CARD_GRAMMAR_TOKEN_KEYS, COMPONENT_GRAMMAR_TOKENS

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS_CSS = ROOT / "ui" / "mobile_components.css"
SHELL_CSS = ROOT / "ui" / "mobile_shell.css"
TXN_CSS = ROOT / "ui" / "mobile_txn.css"
REPORTS_CSS = ROOT / "ui" / "mobile_reports.css"
THEME_CSS = ROOT / "ui" / "theme.css"
WIDGETS_CSS = ROOT / "ui" / "widgets.css"

CARD_SURFACE_KEYS = (
    "--erp-card-bg",
    "--erp-card-border",
    "--erp-card-radius",
    "--erp-card-shadow",
)


@pytest.fixture(scope="module")
def components_css() -> str:
    return COMPONENTS_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def shell_css() -> str:
    return SHELL_CSS.read_text(encoding="utf-8")


def test_mobile_surface_aliases_reference_card_grammar(components_css):
    root = components_css.split(":root")[1].split("}", 1)[0]
    assert "var(--erp-card-bg)" in root
    assert "var(--erp-card-border)" in root
    assert "var(--erp-card-shadow)" in root


@pytest.mark.parametrize(
    "cls",
    (
        ".erp-mob-kpi-chip",
        ".erp-mob-surface",
        ".erp-mob-list-row",
    ),
)
def test_mobile_component_cards_use_surface_aliases(components_css, cls):
    block = components_css.split(cls)[1][:400]
    assert "var(--mob-surface-bg)" in block
    assert "var(--mob-surface-border)" in block


def test_mobile_txn_surface_aliases_reference_card_grammar():
    css = TXN_CSS.read_text(encoding="utf-8")
    root = css.split(":root")[1].split("}", 1)[0]
    assert "--mob-at-surface: var(--erp-card-bg)" in root
    assert "--mob-at-surface-border: var(--erp-card-border)" in root
    assert "--mob-at-surface-shadow: var(--erp-card-shadow)" in root


def test_mobile_hub_sheet_uses_card_grammar(shell_css):
    idx = shell_css.index("st-key-erp_mob_hub_sheet")
    block = shell_css[idx : idx + 700]
    assert "var(--erp-card-bg)" in block
    assert "var(--erp-card-border)" in block


def test_mobile_profile_and_co_switch_sheets_use_card_grammar(shell_css):
    for key in ("erp_mob_profile_sheet", "erp_mob_co_switch_sheet"):
        block = shell_css.split(key)[1][:500]
        assert "var(--erp-card-bg)" in block, key
        assert "var(--erp-card-border)" in block, key


def test_mobile_quick_create_uses_card_grammar(shell_css):
    block = shell_css.split("st-key-mob_qc_")[1][:500]
    assert "var(--erp-card-bg)" in block
    assert "var(--erp-card-border)" in block


def test_mobile_reports_filters_use_card_grammar():
    css = REPORTS_CSS.read_text(encoding="utf-8")
    idx = css.index('[class*="st-key-erp_mob_rpt_filters"]')
    block = css[idx : idx + 600]
    assert "var(--erp-card-bg)" in block
    assert "var(--erp-card-border)" in block


def test_desktop_mobile_card_token_parity():
    """Both surfaces reference the same card grammar token names."""
    theme = THEME_CSS.read_text(encoding="utf-8")
    widgets = WIDGETS_CSS.read_text(encoding="utf-8")
    mobile = (
        COMPONENTS_CSS.read_text(encoding="utf-8")
        + SHELL_CSS.read_text(encoding="utf-8")
        + TXN_CSS.read_text(encoding="utf-8")
        + REPORTS_CSS.read_text(encoding="utf-8")
    )
    desktop = theme.split("MONO-THEME-01-S4")[1][:4000] + widgets.split("MONO-THEME-01-S4")[1][:3000]
    for key in CARD_SURFACE_KEYS:
        assert f"var({key})" in desktop, f"desktop missing {key}"
        assert f"var({key})" in mobile, f"mobile missing {key}"


def test_card_grammar_keys_complete():
    assert len(CARD_GRAMMAR_TOKEN_KEYS) == 5
    for key in CARD_SURFACE_KEYS:
        assert key in COMPONENT_GRAMMAR_TOKENS


def test_components_documents_s5(components_css):
    assert "MONO-THEME-01-S5" in components_css
