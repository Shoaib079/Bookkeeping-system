"""P0 — SETUP-01 create-company entry points and overlay/session cleanup."""

from __future__ import annotations

import inspect
import sys

import pytest

import app as erp
from registry.setup01_wizard import (
    SETUP01_SESSION_ACTIVE,
    SETUP01_SESSION_STEP,
    is_setup01_active,
)

if "streamlit" not in sys.modules:
    import streamlit as st
else:
    st = sys.modules["streamlit"]
    if not isinstance(getattr(st, "session_state", None), dict):
        st.session_state = {}


@pytest.fixture(autouse=True)
def clear_session():
    st.session_state.clear()
    yield
    st.session_state.clear()


def test_start_helper_clears_overlays_and_company_context(monkeypatch):
    rerun_calls: list[int] = []
    monkeypatch.setattr(erp.st, "rerun", lambda: rerun_calls.append(1))

    st.session_state.update(
        {
            "_confirm_company_switch": True,
            "_hdr_open_create_after_picker": True,
            "_switch_target_company_id": 9,
            "mob_profile_open": True,
            "mob_co_switch_open": True,
            "mobile_hub_open": "transactions",
            "picker_expand_create": True,
            "active_company_id": 1,
            "active_company_role": "owner",
            "active_company_name": "Spice Corner",
        }
    )

    erp._start_create_company_wizard()

    assert rerun_calls == [1]
    assert is_setup01_active()
    assert st.session_state[SETUP01_SESSION_STEP] == "details"
    assert "_confirm_company_switch" not in st.session_state
    assert "_hdr_open_create_after_picker" not in st.session_state
    assert "_switch_target_company_id" not in st.session_state
    assert "mob_profile_open" not in st.session_state
    assert "mob_co_switch_open" not in st.session_state
    assert "mobile_hub_open" not in st.session_state
    assert "picker_expand_create" not in st.session_state
    assert "active_company_id" not in st.session_state


def test_desktop_profile_create_uses_shared_helper_when_no_active_company():
    src = inspect.getsource(erp._render_hdr_profile_panel_content)
    assert "_start_create_company_wizard" in src
    assert "_current_company_id()" in src


def test_company_switch_confirm_routes_create_to_shared_helper():
    src = inspect.getsource(erp._render_company_switch_confirm)
    assert "_start_create_company_wizard" in src
    assert "expand_create=_expand" not in src


def test_picker_start_wizard_calls_shared_helper():
    src = inspect.getsource(erp.render_company_picker)
    assert "_start_create_company_wizard" in src
    assert "begin_setup01_wizard" not in src


def test_main_gate_starts_wizard_before_restore_last_company():
    src = inspect.getsource(erp.main)
    gate_start = src.index("# ── Phase 14B: company context gate")
    gate_block = src[gate_start : gate_start + 2800]
    expand_idx = gate_block.index("_start_create_company_wizard")
    restore_idx = gate_block.index("_try_restore_last_active_company")
    assert expand_idx < restore_idx


def test_no_picker_expand_create_only_path_on_go_to_picker():
    src = inspect.getsource(erp._go_to_company_picker)
    assert "picker_expand_create" not in src
    assert "expand_create" not in src


def test_no_legacy_create_company_form():
    assert not hasattr(erp, "_render_create_company_form")
