"""Transaction Ledger — mobile presentation isolation from desktop."""

from __future__ import annotations

import inspect
from pathlib import Path

import app as erp

ROOT = Path(__file__).resolve().parents[1]


def test_mobile_list_owns_card_shell_and_panels():
    src = inspect.getsource(erp._txh_render_transaction_list)
    mobile_block = src.split("if mobile:")[1].split("else:")[0]
    assert 'key=f"txh_row_{row_key}"' in mobile_block
    assert "_txh_render_mobile_card" in mobile_block
    assert "_txh_render_mobile_actions" in mobile_block
    assert "_txh_render_row_panels" in mobile_block
    assert mobile_block.index("_txh_render_row_panels") > mobile_block.index('key=f"txh_row_{row_key}"')


def test_mobile_actions_not_in_desktop_row():
    desk_row = inspect.getsource(erp._txh_render_desktop_row)
    assert "_txh_render_desktop_actions" in desk_row
    assert "txh_actions_" not in desk_row
    assert "_txh_render_mobile_actions" not in desk_row


def test_mobile_action_css_scoped_to_mobile_host():
    css = (ROOT / "ui" / "mobile_txn_history.css").read_text(encoding="utf-8")
    assert "html.erp-mobile" in css
    assert ":has(.erp-txh-mobile-host)" in css
    assert 'st-key-txh_actions_' in css
    assert "min-height: var(--txh-action-h)" in css
    assert "grid-template-columns: repeat(4" in css
    assert "width: 100% !important" in css
    desk = (ROOT / "ui" / "desktop_txn_history.css").read_text(encoding="utf-8")
    assert "st-key-txh_actions_" not in desk
    assert "st-key-txh_dt_actions_" in desk
    assert ":has(.erp-txh-desktop-host)" in desk


def test_render_txh_syncs_mobile_flag():
    src = inspect.getsource(erp.render_transaction_history)
    assert "_sync_mobile_ui_flag_from_cookie()" in src
    assert "_txh_render_mobile_actions" in inspect.getsource(erp._txh_render_transaction_list)
    list_src = inspect.getsource(erp._txh_render_transaction_list)
    mobile_block = list_src.split("if mobile:")[1].split("else:")[0]
    assert "_txh_render_desktop_actions" not in mobile_block
    desk_block = list_src.split("else:")[1]
    assert "_txh_render_mobile_actions" not in desk_block
    assert "_txh_render_desktop_row" in desk_block
    assert "txh_dt_actions_" in inspect.getsource(erp._txh_render_desktop_actions)


def test_desktop_action_css_scoped_to_desktop_host():
    css = (ROOT / "ui" / "desktop_txn_history.css").read_text(encoding="utf-8")
    assert ":has(.erp-txh-desktop-host)" in css
    assert "width: 22px" in css
    assert "st-key-txh_dt_actions_" in css
