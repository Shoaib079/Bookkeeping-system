"""OBS-011 — Banking POS settlement → Statement import upload route regression."""

from __future__ import annotations

import inspect
import sys
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
    sys.modules["streamlit"].session_state = {}

import app as erp
import ui.banking as banking_ui
from registry.nav_keys import NAV_BANKING


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


def test_pos_go_import_uses_canonical_upload_navigator():
    src = inspect.getsource(banking_ui.render_banking_pos_settlement_section)
    assert "banking_navigate_statement_import_upload()" in src
    assert 'banking_section"] = "import"' not in src


def test_canonical_upload_route_sets_upload_tab_and_clears_pos_stale_keys():
    state = {
        "banking_section": "pos_settlement",
        "bsi_section": "match",
        "bsi_pos_entry": True,
        "bsi_match_kind": "card_clearing",
        "bsi_match_row": 42,
        "bsi_queue_sel_row": 99,
    }
    sys.modules["streamlit"].session_state = state
    banking_ui.banking_apply_statement_import_upload_route()
    assert state["banking_section"] == "import"
    assert state["bsi_section"] == "upload"
    assert "bsi_pos_entry" not in state
    assert "bsi_match_kind" not in state
    assert "bsi_match_row" not in state
    assert "bsi_queue_sel_row" not in state


def test_navigate_upload_reruns(monkeypatch):
    state: dict = {}
    reruns: list[int] = []
    monkeypatch.setattr(banking_ui.st, "session_state", state)
    monkeypatch.setattr(banking_ui.st, "rerun", lambda: reruns.append(1))
    banking_ui.banking_navigate_statement_import_upload()
    assert state["bsi_section"] == "upload"
    assert reruns == [1]


def test_import_upload_section_renders_file_uploader():
    src = inspect.getsource(erp.render_bank_statement_import)
    upload_block = src.split('if section == "upload":', 1)[1].split(
        'elif section == "review":', 1
    )[0]
    assert "bsi_file_uploader" in upload_block
    assert "file_uploader" in upload_block


def test_pos_settlement_route_then_upload_navigator_leaves_match_empty_state():
    """Reproduce OBS-011: stale bsi_section=match must not survive go_import."""
    state = erp._banking_pos_settlement_route_keys()
    sys.modules["streamlit"].session_state = state
    banking_ui.banking_apply_statement_import_upload_route()
    assert state["banking_section"] == "import"
    assert state["bsi_section"] == "upload"
    assert state.get("bsi_pos_entry") is None


def test_settings_go_import_uses_canonical_upload_route():
    src = inspect.getsource(erp._render_banking_page_settings)
    assert "_banking_apply_statement_import_upload_route()" in src


def test_legacy_bank_statement_import_reroute_uses_upload_route():
    main_src = inspect.getsource(erp.main)
    block = main_src.split('== "Bank Statement Import"', 1)[1].split(
        "# Legacy Accounting Tools", 1
    )[0]
    assert "_banking_apply_statement_import_upload_route()" in block


def test_at_statement_import_link_uses_canonical_navigator():
    import ui.banking_workflow_ui as bwu

    src = inspect.getsource(erp._at_render_statement_workflow_callout)
    assert "at_navigate_banking_statement_import()" in src
    nav_src = inspect.getsource(bwu.at_navigate_banking_statement_import)
    assert "banking_navigate_statement_import_upload" in nav_src


def test_cockpit_drill_to_match_unchanged(monkeypatch):
    """Match drill-through intentionally stays on match tab (not upload)."""
    state: dict = {}
    reruns: list[int] = []
    monkeypatch.setattr(banking_ui.st, "session_state", state)
    monkeypatch.setattr(banking_ui.st, "rerun", lambda: reruns.append(1))
    banking_ui.banking_cockpit_drill_to("match")
    assert state["banking_section"] == "import"
    assert state["bsi_section"] == "match"
    assert reruns == [1]
