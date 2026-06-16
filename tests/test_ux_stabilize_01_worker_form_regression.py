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


def test_apply_transitions_clears_categories_on_worker_entry(monkeypatch):
    state = _FakeSessionState({"at_expense_mode": "worker"})
    monkeypatch.setattr(erp.st, "session_state", state)
    cleared = []
    monkeypatch.setattr(erp, "_at_clear_category_session_state", lambda: cleared.append("cat"))
    erp._at_apply_worker_expense_mode_transitions()
    assert cleared == ["cat"]
    assert state["_at_worker_expense_active"] is True


def test_apply_transitions_clears_worker_on_general_entry(monkeypatch):
    state = _FakeSessionState(
        {"at_expense_mode": "general", "_at_worker_expense_active": True, "at_worker_id": 3}
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    cleared = []
    monkeypatch.setattr(erp, "_at_clear_worker_entry_session_state", lambda: cleared.append("w"))
    erp._at_apply_worker_expense_mode_transitions()
    assert cleared == ["w"]
    assert state["_at_worker_expense_active"] is False


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
    expense_block = src.split('elif txn_type == "Expense":', 1)[1].split(
        'elif txn_type == "Purchase":', 1
    )[0]
    assert '["general", "worker"]' in expense_block
    assert "_has_active_workers" not in expense_block


def test_shared_worker_panel_helper_exists():
    assert hasattr(erp, "_at_render_worker_expense_panel")
    assert hasattr(erp, "_at_presync_salary_expense_mode")
    assert hasattr(erp, "_at_apply_worker_expense_mode_transitions")
