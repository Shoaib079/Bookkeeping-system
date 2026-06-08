"""Transaction Ledger — separate desktop table vs mobile card presentation."""

from __future__ import annotations

import inspect
from pathlib import Path

import app as erp

ROOT = Path(__file__).resolve().parents[1]


def test_shared_row_fetch_helper_exists():
    assert hasattr(erp, "_txh_fetch_filtered_rows")
    assert hasattr(erp, "_txh_rows_to_dataframe")


def test_separate_presentation_helpers():
    assert hasattr(erp, "_txh_render_mobile_card")
    assert hasattr(erp, "_txh_render_desktop_row")
    assert hasattr(erp, "_txh_render_desktop_table_header")
    assert hasattr(erp, "_txh_render_transaction_list")


def test_shared_action_logic_and_panel_handlers():
    assert hasattr(erp, "_txh_action_defs")
    assert hasattr(erp, "_txh_bind_action_buttons")
    assert hasattr(erp, "_txh_render_row_panels")


def test_separate_action_presentations():
    assert hasattr(erp, "_txh_render_mobile_actions")
    assert hasattr(erp, "_txh_render_desktop_actions")
    mob = inspect.getsource(erp._txh_render_mobile_actions)
    desk = inspect.getsource(erp._txh_render_desktop_actions)
    assert "txh_actions_" in mob
    assert "txh_dt_actions_" in desk
    assert "st.columns(4)" in mob
    assert "st.columns(4)" in desk
    assert not hasattr(erp, "_txh_render_row_actions")


def test_mobile_desktop_host_markers():
    src = inspect.getsource(erp.render_transaction_history)
    assert "erp-txh-mobile-host" in src
    assert "erp-txh-desktop-host" in src
    assert "_sync_mobile_ui_flag_from_cookie()" in src


def test_desktop_table_columns_wired():
    src = inspect.getsource(erp._txh_render_desktop_table_header)
    assert "erp-txh-dt-head" in src
    assert '_t("col.date")' in src
    assert '_t("col.description")' in src
    assert '_t("col.actions")' in src


def test_desktop_row_uses_separate_action_keys():
    src = inspect.getsource(erp._txh_render_desktop_row)
    assert "txh_dt_row_" in src
    assert "_txh_render_desktop_actions" in src
    assert "txh_row_" not in src
    assert "txh_actions_" not in src


def test_list_dispatches_on_mobile_flag():
    src = inspect.getsource(erp._txh_render_transaction_list)
    assert "_txh_render_mobile_card" in src
    assert "_txh_render_desktop_row" in src
    assert "if mobile:" in src


def test_desktop_css_file_loaded():
    css = (ROOT / "ui" / "desktop_txn_history.css").read_text(encoding="utf-8")
    assert "erp-txh-dt-head" in css
    assert "erp-txh-desktop-host" in css
    assert "position: sticky" in css
    assert "erp-txh-dt-cell--amt" in css
    assert "white-space: nowrap" in css
    theme = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    assert "desktop_txn_history.css" in theme


def test_desktop_column_weights_and_amount_nbsp():
    assert erp._TXH_DESKTOP_COL_WEIGHTS[3] > 2.5  # description wider than original
    src = inspect.getsource(erp._txh_render_desktop_row)
    assert "_TXH_DESKTOP_COL_WEIGHTS" in src
    assert "\\u00a0" in src or "\u00a0" in src
    assert "erp-txh-dt-cell--status" in src


def test_desktop_sticky_header_shell():
    src = inspect.getsource(erp._txh_render_desktop_table_header)
    assert "erp-txh-dt-shell" in src
    assert "erp-txh-dt-head-amt" in src
    list_src = inspect.getsource(erp._txh_render_transaction_list)
    assert '</div></div>' in list_src
