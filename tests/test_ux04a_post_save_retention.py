"""UX-04A — post-save state retention in Add Transaction (ADD-TXN-FIX-01: clean next entry)."""

from __future__ import annotations

import datetime
import inspect
import sys
from unittest.mock import MagicMock

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


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


def _state_with_retained_and_transient() -> _FakeSessionState:
    return _FakeSessionState(
        {
            # transient — should clear
            "at_amount_display": "150.00",
            "at_notes_field": "test note",
            "at_cust": "Acme Corp",
            "at_cust_sel": "Acme Corp",
            "at_payable_id": 9,
            "at_last_vendor": "Vendor A",
            "at_worker_gross": "5000",
            "mob_at_worker_gross": "5000",
            "at_worker_ded": "200",
            "mob_at_worker_ded": "200",
            "at_worker_adv_rec": "50",
            "mob_at_worker_adv_rec": "50",
            "at_cat": "Rent",
            "at_subcat": "Office",
            "at_last_cat_id": 3,
            "mob_at_cat_id": 3,
            "mob_at_subcat_id": 7,
            "mob_at_last_cat_expense": 3,
            # retained — should persist
            "at_type_idx": 1,
            "at_pm": "Card",
            "at_date": datetime.date(2026, 6, 10),
            "at_currency": "USD",
            "at_vendor": "Supplier X",
            "at_bank_acct": "Main Bank",
        }
    )


def test_post_save_clears_amount_and_notes(monkeypatch):
    state = _state_with_retained_and_transient()
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_clear_post_save_transient_fields()
    assert "at_amount_display" not in state
    assert "at_notes_field" not in state


def test_post_save_clears_category_state(monkeypatch):
    state = _state_with_retained_and_transient()
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_clear_post_save_transient_fields()
    for key in (
        "at_last_cat_id",
        "at_cat",
        "at_subcat",
        "mob_at_cat_id",
        "mob_at_subcat_id",
        "mob_at_last_cat_expense",
    ):
        assert key not in state


def test_post_save_clears_credit_sale_customer_dropdown(monkeypatch):
    state = _state_with_retained_and_transient()
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_clear_post_save_transient_fields()
    assert "at_cust_sel" not in state
    assert "at_cust" not in state


def test_post_save_clears_worker_salary_amount_fields(monkeypatch):
    state = _state_with_retained_and_transient()
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_clear_post_save_transient_fields()
    for key in (
        "at_worker_gross",
        "mob_at_worker_gross",
        "at_worker_ded",
        "mob_at_worker_ded",
        "at_worker_adv_rec",
        "mob_at_worker_adv_rec",
    ):
        assert key not in state


def test_post_save_retains_type_payment_date_currency(monkeypatch):
    state = _state_with_retained_and_transient()
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_clear_post_save_transient_fields()
    assert state["at_type_idx"] == 1
    assert state["at_pm"] == "Card"
    assert state["at_date"] == datetime.date(2026, 6, 10)
    assert state["at_currency"] == "USD"
    assert "at_vendor" not in state
    assert state["at_bank_acct"] == "Main Bank"


def test_post_save_clear_keys_include_last_cat_id():
    assert "at_last_cat_id" in erp._AT_POST_SAVE_CLEAR_KEYS


def test_process_submit_uses_post_save_clear_helper():
    src = inspect.getsource(erp._at_process_submit)
    assert "_at_clear_post_save_transient_fields()" in src


def test_inline_subcat_row_resets_subcat_when_category_changes():
    src = inspect.getsource(erp._inline_subcat_row)
    assert "at_last_cat_id" in src
    assert "_at_defer_subcat_clear()" in src
    assert "_at_apply_deferred_subcat_sync()" in src
