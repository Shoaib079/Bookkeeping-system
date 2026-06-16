"""UX-STABILIZE-01 — data-entry state cleanup (worker salary isolation, post-save reset, nav scroll)."""

from __future__ import annotations

import datetime
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


def test_at_is_worker_expense_entry_salary_and_desktop_radio():
    state = _FakeSessionState(
        {"mob_at_tab": 3, "mob_at_more_idx": erp._MOB_AT_SALARY_IDX}
    )
    assert erp._at_is_worker_expense_entry() is False
    with patch.object(erp.st, "session_state", state):
        assert erp._at_is_worker_expense_entry() is True
    state = _FakeSessionState({"at_expense_mode": "worker"})
    with patch.object(erp.st, "session_state", state):
        assert erp._at_is_worker_expense_entry() is True
    state = _FakeSessionState({"at_expense_mode": "general", "mob_at_tab": 1})
    with patch.object(erp.st, "session_state", state):
        assert erp._at_is_worker_expense_entry() is False


def test_gather_submit_skips_category_in_worker_expense_mode(monkeypatch):
    state = _FakeSessionState(
        {
            "at_expense_mode": "worker",
            "mob_at_cat_id": 99,
            "at_cat": "Rent",
            "at_subcat": "Office",
            "at_last_cat_id": 99,
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    session = MagicMock()
    ctx = erp._at_gather_submit_fields(session, "Expense", "TRY", [], [], [])
    assert ctx["at_cat_id"] is None
    assert ctx["at_subcat_name"] is None
    assert ctx["effective_category"] == ""


def test_mob_at_c_apply_type_salary_sets_worker_and_clears_categories(monkeypatch):
    state = _FakeSessionState(
        {
            "mob_at_cat_id": 9,
            "at_cat": "Rent",
            "at_subcat": "Office",
            "at_last_cat_id": 9,
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_c_apply_type(erp._MOB_AT_SALARY_IDX)
    assert state["at_type_idx"] == erp._MOB_AT_SALARY_IDX
    assert state["at_expense_mode"] == "worker"
    assert state["at_worker_mv_type"] == "Salary"
    assert "mob_at_cat_id" not in state
    assert "at_cat" not in state


def test_mob_at_c_apply_type_expense_clears_worker_fields(monkeypatch):
    state = _FakeSessionState(
        {
            "at_expense_mode": "worker",
            "at_worker_id": 3,
            "at_worker_gross": "5000",
            "mob_at_worker_gross": "5000",
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_c_apply_type(1)
    assert state["at_expense_mode"] == "general"
    assert "at_worker_id" not in state
    assert "at_worker_gross" not in state


def test_post_save_clear_invokes_category_helper(monkeypatch):
    state = _FakeSessionState({"at_cat": "Rent", "at_subcat": "Office"})
    monkeypatch.setattr(erp.st, "session_state", state)
    calls = []
    monkeypatch.setattr(
        erp,
        "_at_clear_category_session_state",
        lambda: calls.append("cat"),
    )
    erp._at_clear_post_save_transient_fields()
    assert calls == ["cat"]


def test_post_save_clears_category_keys_after_helper(monkeypatch):
    state = _FakeSessionState(
        {
            "at_type_idx": 1,
            "at_date": datetime.date(2026, 6, 10),
            "at_cat": "Rent",
            "at_subcat": "Office",
            "at_last_cat_id": 2,
            "mob_at_cat_id": 2,
            "mob_at_subcat_id": 5,
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_clear_post_save_transient_fields()
    for key in (
        "at_cat",
        "at_subcat",
        "at_last_cat_id",
        "mob_at_cat_id",
        "mob_at_subcat_id",
    ):
        assert key not in state
    assert state["at_type_idx"] == 1
    assert state["at_date"] == datetime.date(2026, 6, 10)


def test_render_add_transaction_worker_branch_clears_categories():
    src = inspect.getsource(erp.render_add_transaction)
    worker_block = src.split('if expense_mode == "worker":', 1)[1].split("else:", 1)[0]
    assert "_at_clear_category_session_state()" in worker_block


def test_mobile_salary_branch_clears_categories():
    src = inspect.getsource(erp._render_add_transaction_mobile)
    salary_block = src.split("if _mob_at_is_salary_mode():", 1)[1].split(
        "elif at_idx == 0:", 1
    )[0]
    assert "_at_clear_category_session_state()" in salary_block
    assert "_mob_at_render_quick_cat_chips" not in salary_block


def test_main_page_change_calls_scroll_helper():
    src = inspect.getsource(erp.main)
    nav_block = src.split('if st.session_state.get("_current_page") != selection:', 1)[1]
    assert "_scroll_main_to_top()" in nav_block.split("# ── Page dispatch")[0]


def test_scroll_main_to_top_uses_components_html():
    src = inspect.getsource(erp._scroll_main_to_top)
    assert "scrollTo(0,0)" in src
    assert "components.v1" in src or "components.html" in src


def test_desktop_submit_uses_effective_txn_type():
    src = inspect.getsource(erp.render_add_transaction)
    assert "_submit_type = _at_effective_txn_type(_TYPE_NAMES)" in src
