"""THEME-01 — checkbox control chrome uses ERP theme tokens."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _widgets_block() -> str:
    widgets = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    return widgets.split("/* THEME-01 — Streamlit 1.58 checkbox DOM", 1)[1].split(
        "/* ── Slider", 1
    )[0]


def test_checkbox_theme_css_contract():
    """Checkbox box chrome: unchecked, checked, disabled — widgets.css only."""
    block = _widgets_block()
    assert '[data-testid="stCheckbox"]' in block
    assert "label > span:first-child" in block
    assert "label:has(input:checked)" in block
    assert "label:has(input:disabled)" in block
    assert "var(--theme-card)" in block
    assert "var(--theme-input-border)" in block
    assert "var(--theme-info)" in block
    assert "%23ffffff" in block  # erp-on-primary tick in checked SVG
    assert "background-image: none" in block


def test_checkbox_label_text_not_checkmark_span():
    """Label copy uses stWidgetLabel / markdown — not label > span color override."""
    widgets = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    assert '[data-testid="stCheckbox"] label span,' not in widgets
    assert '[data-testid="stCheckbox"] [data-testid="stWidgetLabel"]' in widgets


def test_checkbox_rules_scoped_to_st_main_only():
    block = _widgets_block()
    assert block.count('[data-testid="stMain"]') >= 5
    assert not re.search(
        r'^\[data-testid="stCheckbox"\]',
        block,
        re.M,
    )
