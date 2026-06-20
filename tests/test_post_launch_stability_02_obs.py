"""POST-LAUNCH-STABILITY-02 — OBS-005/006/007/009/010 contract regressions."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
    sys.modules["streamlit"].session_state = {}

import app as erp
from registry.navigation import NAV_HOME

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def clear_session():
    erp.st.session_state.clear()
    yield
    erp.st.session_state.clear()


class _FakeSessionState(dict):
    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


# ── OBS-006 company switch → Home ─────────────────────────────────────────────


def test_on_company_switch_success_sets_home_and_clears_page_state(monkeypatch):
    state = _FakeSessionState(
        {
            "nav_selection": "Reports",
            "advanced_subpage": "foo",
            "sidebar_group": "reports",
            "rpt_exec_sel": "sales",
            "mob_reports_tab": "expenses",
            "banking_section": "import",
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "_mobile_close_app_surfaces", lambda: None)
    erp._on_company_switch_success()
    assert state["nav_selection"] == NAV_HOME
    assert "advanced_subpage" not in state
    assert "sidebar_group" not in state
    assert "rpt_exec_sel" not in state
    assert "mob_reports_tab" not in state
    assert "banking_section" not in state


def test_company_scoped_keys_include_worker_and_receipt():
    for key in (
        "at_worker_id",
        "at_worker_mv_type",
        "at_pending_attachment",
        "at_desktop_receipt_upload",
    ):
        assert key in erp._COMPANY_SCOPED_AT_KEYS


def test_switch_confirm_handler_calls_on_company_switch_success():
    src = inspect.getsource(erp._render_company_switch_confirm)
    assert "_on_company_switch_success()" in src


# ── OBS-007 expense CC policy ─────────────────────────────────────────────────


def test_expense_entry_excludes_company_cc_when_enabled(monkeypatch):
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: True)
    assert erp._COMPANY_CC_METHOD not in erp._at_expense_pay_methods(MagicMock())
    assert erp._COMPANY_CC_METHOD not in erp._expense_form_pay_methods(MagicMock())
    assert "Expense" not in erp._AT_COMPANY_CC_TXN_TYPES


def test_purchase_still_allows_company_cc_when_enabled(monkeypatch):
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: True)
    assert erp._COMPANY_CC_METHOD in erp._at_purchase_pay_methods(MagicMock())


# ── OBS-009 desktop receipt entry ─────────────────────────────────────────────


def test_desktop_expense_form_exposes_receipt_upload():
    src = inspect.getsource(erp.render_add_transaction)
    expense_block = src.split('elif txn_type == "Expense":', 1)[1].split(
        'elif txn_type == "Purchase":', 1
    )[0]
    assert "at_desktop_receipt_upload" in expense_block
    assert "txn.attach_receipt_btn" in expense_block or "_t(\"txn.attach_receipt_btn\")" in expense_block


def test_post_save_clear_includes_receipt_keys():
    assert "at_pending_attachment" in erp._AT_POST_SAVE_CLEAR_KEYS
    assert "at_desktop_receipt_upload" in erp._AT_POST_SAVE_CLEAR_KEYS


# ── OBS-010 explicit choices ──────────────────────────────────────────────────


def test_ensure_defaults_does_not_seed_payment_method(monkeypatch):
    state = _FakeSessionState({"at_type_idx": 1})
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_ensure_defaults(MagicMock(), "Expense", "TRY", [])
    assert "at_pm" not in state


def test_presync_salary_does_not_set_movement_type(monkeypatch):
    state = _FakeSessionState(
        {"mob_at_tab": 3, "mob_at_more_idx": erp._MOB_AT_SALARY_IDX}
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_presync_salary_expense_mode()
    assert state["at_expense_mode"] == "worker"
    assert "at_worker_mv_type" not in state


def test_coerce_pm_skips_when_unset(monkeypatch):
    state = _FakeSessionState({})
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)
    erp._coerce_at_payment_method(MagicMock(), "Expense")
    assert "at_pm" not in state


def test_validate_pm_required_when_unset(monkeypatch):
    state = _FakeSessionState({})
    monkeypatch.setattr(erp.st, "session_state", state)
    err = erp._at_validate_payment_method_for_submit(MagicMock(), "Expense")
    assert err == erp._t("txn.pm_required")


def test_apply_default_subcategory_is_noop():
    state = _FakeSessionState()
    erp.st.session_state = state
    erp._mob_at_apply_default_subcategory(MagicMock(), 99)
    assert "mob_at_subcat_id" not in state


def test_worker_panel_uses_placeholders():
    src = inspect.getsource(erp._at_render_worker_expense_panel)
    assert "txn.select_worker_ph" in src
    assert "txn.select_worker_mv_ph" in src
    assert "index=None" in src


def test_inline_subcat_uses_placeholder_when_unset():
    src = inspect.getsource(erp._inline_subcat_row)
    assert "txn.select_subcategory_ph" in src
    assert "else 0" not in src.split("index=_def_idx", 1)[1].split("at_subcat_name", 1)[0]


def test_pm_selectbox_helper_uses_placeholder():
    src = inspect.getsource(erp._at_render_pm_selectbox)
    assert "txn.select_pm_ph" in src
    assert "index=None" in src
