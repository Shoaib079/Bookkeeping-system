"""MONO-THEME-01-S4 — desktop card grammar migration contract tests.

Dashboard, KPI, form containers, and bordered panels on desktop must reference
the shared ``--erp-card-*`` grammar tokens (no new colors).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ui.design_tokens import CARD_GRAMMAR_TOKEN_KEYS, COMPONENT_GRAMMAR_TOKENS

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = ROOT / "ui" / "theme.css"
WIDGETS_CSS = ROOT / "ui" / "widgets.css"

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


def _block_after(css: str, anchor: str, length: int = 500) -> str:
    assert anchor in css, f"anchor missing: {anchor}"
    return css.split(anchor, 1)[1][:length]


@pytest.mark.parametrize(
    "selector",
    (
        ".kpi-card",
        ".erp-page-banner",
        ".erp-dash-welcome-card",
        ".erp-dash-alert-card",
        ".erp-dash-activity-row",
        ".card",
    ),
)
def test_theme_css_card_surfaces_use_grammar_tokens(theme_css, selector):
    block = _block_after(theme_css, selector)
    assert "var(--erp-card-bg)" in block, f"{selector} missing --erp-card-bg"
    assert "var(--erp-card-border)" in block, f"{selector} missing --erp-card-border"
    assert "var(--erp-card-radius)" in block or "var(--erp-radius-md)" in block, (
        f"{selector} missing card radius token"
    )


def test_aging_bucket_uses_muted_card_token(theme_css):
    block = _block_after(theme_css, ".erp-aging-bucket")
    assert "var(--erp-card-muted-bg)" in block
    assert "var(--erp-card-border)" in block


@pytest.mark.parametrize(
    "comment,selector",
    (
        ("Metrics (st.metric) — MONO-THEME-01-S4", "stMetric"),
        ("Bordered cards / containers — MONO-THEME-01-S4", "stVerticalBlockBorderWrapper"),
        ("Expanders — MONO-THEME-01-S4", "stExpander"),
        ("Alerts / status messages — MONO-THEME-01-S4", "stAlert"),
    ),
)
def test_widgets_card_containers_use_grammar_tokens(widgets_css, comment, selector):
    idx = widgets_css.index(comment)
    block = widgets_css[idx : idx + 600]
    assert selector in block
    assert "var(--erp-card-bg)" in block, f"{selector} missing --erp-card-bg"
    assert "var(--erp-card-border)" in block, f"{selector} missing --erp-card-border"


def test_widgets_chart_shells_use_card_grammar(widgets_css):
    block = widgets_css.split("stVegaLiteChart")[1][:600]
    assert "var(--erp-card-bg)" in block
    assert "var(--erp-card-border)" in block


def test_semantic_txn_tip_colors_preserved(theme_css):
    """S4 migrates neutral card shells only — semantic tip tints stay."""
    idx = theme_css.index(".txn-tip-box {")
    block = theme_css[idx : idx + 2500]
    assert "var(--theme-success)" in block or "var(--theme-success-text)" in block
    assert "var(--theme-danger)" in block


def test_card_grammar_keys_complete():
    assert len(CARD_GRAMMAR_TOKEN_KEYS) == 5
    for key in CARD_SURFACE_KEYS:
        assert key in COMPONENT_GRAMMAR_TOKENS


def test_theme_documents_s4_card_grammar(theme_css):
    assert "MONO-THEME-01-S4" in theme_css


def test_widgets_documents_s4_card_grammar(widgets_css):
    assert "MONO-THEME-01-S4" in widgets_css
