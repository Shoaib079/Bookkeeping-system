"""TXH-DETAIL-01 — expanded transaction detail JE / Edit History polish."""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import app as erp

ROOT = Path(__file__).resolve().parents[1]
DESKTOP_CSS = ROOT / "ui" / "desktop_txn_history.css"

_TXH_DETAIL_CLASSES = (
    "erp-txh-je-head",
    "erp-txh-je-line",
    "erp-txh-je-account",
    "erp-txh-je-dr",
    "erp-txh-je-cr",
    "erp-txh-edit-head",
    "erp-txh-edit-line",
    "erp-txh-edit-old",
    "erp-txh-edit-new",
)


def _je_edit_render_sources() -> str:
    je = inspect.getsource(erp._txh_render_view_je_block)
    edit = inspect.getsource(erp._txh_render_view_edit_history_block)
    panel = inspect.getsource(erp._txh_render_row_panels)
    return je + edit + panel


def test_txh_detail_no_inline_styles_in_je_edit_blocks():
    src = _je_edit_render_sources()
    assert 'style="' not in src
    assert "style='" not in src


def test_txh_detail_semantic_classes_in_app_helpers():
    je = inspect.getsource(erp._txh_render_view_je_block)
    edit = inspect.getsource(erp._txh_render_view_edit_history_block)
    for cls in _TXH_DETAIL_CLASSES:
        assert cls in je or cls in edit, f"missing class {cls} in JE/Edit helpers"


def test_txh_detail_panel_calls_helpers_not_inline_je():
    panel = inspect.getsource(erp._txh_render_row_panels)
    assert "_txh_render_view_je_block" in panel
    assert "_txh_render_view_edit_history_block" in panel
    view_block = panel.split("txh_active_view")[1].split("txh_active_edit")[0]
    assert "erp-txh-je-head" not in view_block or "_txh_render_view_je_block" in view_block


def test_txh_detail_classes_in_desktop_css_owner():
    css = DESKTOP_CSS.read_text(encoding="utf-8")
    assert "TXH-DETAIL-01" in css
    for cls in _TXH_DETAIL_CLASSES:
        assert f".{cls}" in css, f"missing .{cls} in desktop_txn_history.css"


def test_txh_detail_edit_diff_uses_contrast_text_tokens():
    css = DESKTOP_CSS.read_text(encoding="utf-8")
    old_block = css.split(".erp-txh-edit-old", 1)[1].split("}", 1)[0]
    new_block = css.split(".erp-txh-edit-new", 1)[1].split("}", 1)[0]
    assert "--theme-danger-text" in old_block
    assert "--theme-success-text" in new_block
    assert "--theme-danger)" not in old_block
    assert "--theme-success)" not in new_block


def test_txh_detail_je_grid_layout_in_css():
    css = DESKTOP_CSS.read_text(encoding="utf-8")
    je_line = css.split(".erp-txh-je-line {", 1)[1].split("}", 1)[0]
    assert "grid-template-columns" in je_line
    dr_cr = css.split(".erp-txh-je-dr,", 1)[1].split("}", 1)[0]
    assert "text-align: right" in dr_cr
    assert "tabular-nums" in dr_cr
