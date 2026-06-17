"""MONO-THEME-01-S6 — table + status chip grammar migration contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from ui.design_tokens import CHIP_GRAMMAR_EXTENSION_KEYS, TABLE_GRAMMAR_TOKEN_KEYS

ROOT = Path(__file__).resolve().parents[1]

TABLE_KEYS = (
    "--erp-table-border",
    "--erp-table-header-bg",
    "--erp-table-row-hover-bg",
    "--erp-table-total-bg",
)


@pytest.fixture(scope="module")
def theme_css() -> str:
    return (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def widgets_css() -> str:
    return (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")


def test_financial_tables_use_table_grammar(theme_css):
    idx = theme_css.index("Financial statement tables")
    block = theme_css[idx : idx + 2200]
    for key in TABLE_KEYS:
        assert f"var({key})" in block, f"erp-fin-table missing {key}"


def test_data_tables_use_table_grammar(theme_css):
    idx = theme_css.index("Token-themed data table")
    block = theme_css[idx : idx + 1200]
    assert "var(--erp-table-header-bg)" in block
    assert "var(--erp-table-border)" in block


def test_fin_semantic_row_tints_preserved(theme_css):
    idx = theme_css.index("erp-fin-row-ok")
    block = theme_css[max(0, idx - 800) : idx + 400]
    assert "erp-fin-row-ok" in block
    assert "var(--theme-success)" in block
    assert "erp-fin-row-warn" in block
    assert "var(--theme-warning)" in block


def test_widgets_sttable_uses_table_grammar(widgets_css):
    block = widgets_css.split("MONO-THEME-01-S6")[1][:500]
    assert "var(--erp-table-header-bg)" in block
    assert "var(--erp-table-border)" in block


def test_desktop_txh_table_grammar():
    css = (ROOT / "ui" / "desktop_txn_history.css").read_text(encoding="utf-8")
    assert "var(--erp-table-header-bg)" in css
    assert "var(--erp-table-row-hover-bg)" in css
    assert "var(--erp-table-border)" in css


def test_mobile_txh_row_uses_table_border():
    css = (ROOT / "ui" / "mobile_txn_history.css").read_text(encoding="utf-8")
    block = css.split("MONO-THEME-01-S6")[1][:500]
    assert "var(--erp-table-border)" in block
    assert "var(--erp-card-bg)" in block


def test_status_pills_use_chip_extension_grammar():
    components = (ROOT / "ui" / "mobile_components.css").read_text(encoding="utf-8")
    block = components.split("MONO-THEME-01-S6")[1][:400]
    assert "var(--erp-chip-radius)" in block
    assert "var(--erp-chip-padding-y)" in block
    assert "var(--erp-chip-padding-x)" in block


def test_banking_section_chips_in_widgets_primary_block(widgets_css):
    idx = widgets_css.index("st-key-bank_sec_sel_")
    block = widgets_css[idx : idx + 800]
    assert "var(--erp-chip-active-bg)" in block
    assert "var(--erp-chip-idle-bg)" in block or "var(--erp-chip-active-border)" in block


def test_desktop_mobile_table_token_parity(theme_css, widgets_css):
    mobile = (
        (ROOT / "ui" / "desktop_txn_history.css").read_text(encoding="utf-8")
        + (ROOT / "ui" / "mobile_txn_history.css").read_text(encoding="utf-8")
    )
    idx = theme_css.index("Financial statement tables")
    desktop = theme_css[idx : idx + 2200] + widgets_css.split("MONO-THEME-01-S6")[1][:500]
    for key in ("--erp-table-border", "--erp-table-header-bg"):
        assert f"var({key})" in desktop
        assert f"var({key})" in mobile


def test_table_and_chip_extension_keys_documented():
    assert len(TABLE_GRAMMAR_TOKEN_KEYS) == 4
    assert len(CHIP_GRAMMAR_EXTENSION_KEYS) == 4
