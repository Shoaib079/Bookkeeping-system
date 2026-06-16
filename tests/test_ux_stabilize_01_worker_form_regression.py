"""UX-STABILIZE-01 regression — worker salary/advance form must hide categories and show worker picker."""

from __future__ import annotations

import inspect
import sys
from unittest.mock import MagicMock, patch

import pytest

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock
else:
    _st_mock = sys.modules["streamlit"]
    if not isinstance(getattr(_st_mock, "session_state", None), dict):
        _st_mock.session_state = {}

import app as erp


class _FakeSessionState(dict):
    def get(self, key, default=None):
        return super().get(key, default)

    def pop(self, key, default=None):
        if key in self:
            return super().pop(key)
        return default

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


def test_presync_sets_worker_mode_for_mobile_salary_flags():
    state = _FakeSessionState(
        {"mob_at_tab": 3, "mob_at_more_idx": erp._MOB_AT_SALARY_IDX}
    )
    with patch.object(erp.st, "session_state", state):
        erp._at_presync_salary_expense_mode()
    assert state["at_expense_mode"] == "worker"
    assert state["at_worker_mv_type"] == "Salary"


def test_is_worker_true_when_salary_flags_but_expense_mode_general():
    """Desktop/mobile tab sync can imply worker entry before the radio catches up."""
    state = _FakeSessionState(
        {
            "mob_at_tab": 3,
            "mob_at_more_idx": erp._MOB_AT_SALARY_IDX,
            "at_expense_mode": "general",
        }
    )
    with patch.object(erp.st, "session_state", state):
        assert erp._at_is_worker_expense_entry() is True


def test_expense_mode_change_clears_categories_on_worker(monkeypatch):
    state = _FakeSessionState({"at_expense_mode": "worker"})
    monkeypatch.setattr(erp.st, "session_state", state)
    cleared = []
    monkeypatch.setattr(erp, "_at_clear_category_session_state", lambda: cleared.append("cat"))
    erp._at_on_desktop_expense_mode_change()
    assert cleared == ["cat"]


def test_expense_mode_change_clears_worker_on_general(monkeypatch):
    state = _FakeSessionState({"at_expense_mode": "general", "at_worker_id": 3})
    monkeypatch.setattr(erp.st, "session_state", state)
    cleared = []
    monkeypatch.setattr(erp, "_at_clear_worker_entry_session_state", lambda: cleared.append("w"))
    erp._at_on_desktop_expense_mode_change()
    assert cleared == ["w"]


def test_render_add_transaction_uses_is_worker_not_expense_mode_var():
    src = inspect.getsource(erp.render_add_transaction)
    assert "if _at_is_worker_expense_entry():" in src
    assert 'if expense_mode == "worker":' not in src


def test_render_add_transaction_skips_cat_lookup_in_worker_mode():
    src = inspect.getsource(erp.render_add_transaction)
    assert "_at_is_worker_expense_entry()" in src.split("cats         = []", 1)[1].split(
        "_at_render_flash", 1
    )[0]


def test_mobile_context_uses_worker_panel_not_salary_only_branch():
    src = inspect.getsource(erp._render_add_transaction_mobile)
    assert "_at_render_worker_expense_panel(" in src
    assert "_mob_at_render_quick_cat_chips" in src
    worker_block = src.split("if _at_is_worker_expense_entry():", 1)[1].split(
        "elif at_idx == 0:", 1
    )[0]
    assert "_mob_at_render_quick_cat_chips" not in worker_block


def test_worker_panel_includes_mv_type_and_no_empty_selectbox():
    src = inspect.getsource(erp._at_render_worker_expense_panel)
    assert "at_worker_mv_type" in src
    assert '["Salary", "Advance"]' in src
    assert "if workers:" in src
    assert "worker.add_workers_first" in src or "_at_render_worker_expense_no_workers" in src


def test_desktop_always_offers_worker_radio():
    src = inspect.getsource(erp.render_add_transaction)
    expense_block = src.split('if txn_type == "Expense":', 1)[1].split(
        'with st.form("at_entry_form"', 1
    )[0]
    assert '["general", "worker"]' in expense_block
    assert 'key="at_expense_mode"' in expense_block
    assert "_has_active_workers" not in expense_block


def test_desktop_expense_radio_outside_entry_form():
    src = inspect.getsource(erp.render_add_transaction)
    form_marker = 'with st.form("at_entry_form", clear_on_submit=False):'
    form_start = src.index(form_marker)
    radio_before_form = src.rfind('key="at_expense_mode"', 0, form_start)
    assert radio_before_form != -1, "at_expense_mode radio must render before at_entry_form"
    expense_in_form = src[form_start:].split('elif txn_type == "Expense":', 1)
    assert len(expense_in_form) > 1
    expense_form_block = expense_in_form[1].split('elif txn_type == "Purchase":', 1)[0]
    assert 'key="at_expense_mode"' not in expense_form_block


def test_desktop_expense_radio_uses_on_change_for_immediate_rerun():
    src = inspect.getsource(erp.render_add_transaction)
    pre_form = src.split('with st.form("at_entry_form"', 1)[0]
    assert "on_change=_at_on_desktop_expense_mode_change" in pre_form


def test_worker_mode_form_branch_hides_category_shows_worker_panel():
    src = inspect.getsource(erp.render_add_transaction)
    expense_form = src.split('elif txn_type == "Expense":', 1)[1].split(
        'elif txn_type == "Purchase":', 1
    )[0]
    worker_branch = expense_form.split("if _at_is_worker_expense_entry():", 1)[1].split(
        "else:", 1
    )[0]
    assert "_at_render_worker_expense_panel(" in worker_branch
    assert "_inline_cat_row" not in worker_branch
    general_branch = expense_form.split("else:", 1)[1]
    assert "_inline_cat_row" in general_branch
    assert "_at_render_worker_expense_panel(" not in general_branch


def test_shared_worker_panel_helper_exists():
    assert hasattr(erp, "_at_render_worker_expense_panel")
    assert hasattr(erp, "_at_presync_salary_expense_mode")
    assert hasattr(erp, "_at_on_desktop_expense_mode_change")
    assert not hasattr(erp, "_at_apply_worker_expense_mode_transitions")
    assert not hasattr(erp, "_mob_at_render_salary_fields")
