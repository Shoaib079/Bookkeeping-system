"""UX-04C — safe smart defaults (PM memory + single-bank auto-pick)."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
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

ROOT = Path(__file__).resolve().parents[1]


class _FakeSessionState(dict):
    def get(self, key, default=None):
        return super().get(key, default)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


class _Bank:
    def __init__(self, name: str):
        self.name = name


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture(autouse=True)
def no_company_cc(monkeypatch):
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)


def test_pm_memory_keys_in_company_scoped():
    for key in (
        "mob_at_last_pm_sale",
        "mob_at_last_pm_expense",
        "mob_at_last_pm_purchase",
    ):
        assert key in erp._COMPANY_SCOPED_AT_KEYS


def test_per_type_pm_memory_disabled(monkeypatch):
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_remember_last_pm("Sale", "Card")
    erp._mob_at_remember_last_pm("Expense", "Bank")
    erp._mob_at_remember_last_pm("Purchase", "Credit")
    assert "mob_at_last_pm_sale" not in state
    assert "mob_at_last_pm_expense" not in state
    assert "mob_at_last_pm_purchase" not in state


def test_default_pay_method_ignores_stale_memory(monkeypatch):
    state = _FakeSessionState({"mob_at_last_pm_sale": "Credit"})
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._at_default_pay_method(MagicMock(), "Sale") == "Cash"


def test_invalid_remembered_pm_falls_back_when_cc_disabled(monkeypatch):
    state = _FakeSessionState({"mob_at_last_pm_expense": erp._COMPANY_CC_METHOD})
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)
    assert erp._at_default_pay_method(MagicMock(), "Expense") == "Cash"


def test_type_change_does_not_restore_remembered_pm(monkeypatch):
    state = _FakeSessionState(
        {
            "at_pm": "Cash",
            "mob_at_last_pm_sale": "Card",
            "_mob_at_coerce_pm_type": "Expense",
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._coerce_at_payment_method(MagicMock(), "Sale")
    assert state["at_pm"] == "Cash"


def test_company_switch_clears_pm_memory():
    st = sys.modules["streamlit"].session_state
    st.update(
        {
            "mob_at_last_pm_sale": "Card",
            "mob_at_last_pm_expense": "Bank",
            "mob_at_last_pm_purchase": "Credit",
            "_mob_at_coerce_pm_type": "Sale",
        }
    )
    erp._clear_company_scoped_session_state()
    assert "mob_at_last_pm_sale" not in st
    assert "mob_at_last_pm_expense" not in st
    assert "mob_at_last_pm_purchase" not in st
    assert "_mob_at_coerce_pm_type" not in st


def test_single_bank_auto_pick(monkeypatch):
    state = _FakeSessionState({"at_pm": "Bank"})
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_apply_single_bank_auto_pick([_Bank("Only Bank")])
    assert state["at_bank_pay_acct"] == "Only Bank"
    assert state["mob_at_bank_pay_sel"] == "Only Bank"


def test_two_banks_do_not_auto_pick(monkeypatch):
    state = _FakeSessionState({"at_pm": "Bank"})
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_apply_single_bank_auto_pick([_Bank("A"), _Bank("B")])
    assert "at_bank_pay_acct" not in state
    assert "mob_at_bank_pay_sel" not in state


def test_bank_pay_trigger_does_not_default_first_of_many(monkeypatch):
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "_tf", lambda k, d=None: d or k)

    class _Container:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(erp.st, "container", lambda **_kw: _Container())
    monkeypatch.setattr(
        erp.st,
        "button",
        lambda *_a, **_kw: False,
    )

    erp._mob_at_render_bank_pay_trigger([_Bank("A"), _Bank("B")])
    assert "at_bank_pay_acct" not in state


def test_pm_chip_tap_remembers_pm(monkeypatch):
    state = _FakeSessionState({"at_pm": "Cash"})
    remembered: list[tuple[str, str]] = []
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(
        erp,
        "_mob_at_pm_chip_methods",
        lambda _s, _t: ["Cash", "Card"],
    )
    monkeypatch.setattr(
        erp,
        "_at_pm_chip_labels",
        lambda _t, methods: [(m, m) for m in methods],
    )
    monkeypatch.setattr(
        erp,
        "_mob_at_remember_last_pm",
        lambda txn_type, pm: remembered.append((txn_type, pm)),
    )
    monkeypatch.setattr(erp, "_at_clear_stale_payment_account_keys", lambda _pm: None)

    class _Col:
        def button(self, _label, key=None, **_kw):
            return key == "mob_at_pm_Card"

    class _Container:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(erp.st, "container", lambda **_kw: _Container())
    monkeypatch.setattr(erp.st, "columns", lambda n, **_kw: [_Col(), _Col()][:n])

    assert erp._mob_at_render_pm_chip_row(MagicMock(), "Sale") is True
    assert remembered == [("Sale", "Card")]
    assert state["at_pm"] == "Card"


def test_pm_memory_helpers_do_not_infer_customer_vendor():
    for fn in (
        erp._mob_at_recall_last_pm,
        erp._mob_at_remember_last_pm,
        erp._at_default_pay_method,
        erp._at_apply_single_bank_auto_pick,
    ):
        src = inspect.getsource(fn)
        assert "mob_at_last_vendor" not in src
        assert "at_cust_sel" not in src
        assert "mob_at_worker" not in src
        assert "at_subcat" not in src


def test_pm_chip_handler_calls_remember():
    src = inspect.getsource(erp._mob_at_render_pm_chip_row)
    assert "_mob_at_remember_last_pm(txn_type, pm_val)" in src
