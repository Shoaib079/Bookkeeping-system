"""P0 — reset stale at_pm when Add Transaction type changes."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

import app as erp


class _FakeSessionState(dict):
    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


@pytest.fixture(autouse=True)
def _no_company_cc(monkeypatch):
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)


def _state(monkeypatch, **kwargs) -> _FakeSessionState:
    state = _FakeSessionState(kwargs)
    monkeypatch.setattr(erp.st, "session_state", state)
    return state


def test_sale_card_to_expense_resets_payment_method(monkeypatch):
    state = _state(monkeypatch, at_pm="Card", at_card_bank_acct="Main Bank")
    erp._coerce_at_payment_method(MagicMock(), "Expense")
    assert state["at_pm"] == "Cash"
    assert "at_card_bank_acct" not in state


def test_purchase_credit_to_supplier_payment_resets_payment_method(monkeypatch):
    state = _state(monkeypatch, at_pm="Credit")
    erp._coerce_at_payment_method(MagicMock(), "Supplier Payment")
    assert state["at_pm"] == "Cash"


def test_expense_bank_to_purchase_keeps_bank(monkeypatch):
    state = _state(monkeypatch, at_pm="Bank", at_bank_pay_acct="Operating")
    erp._coerce_at_payment_method(MagicMock(), "Purchase")
    assert state["at_pm"] == "Bank"
    assert state["at_bank_pay_acct"] == "Operating"


def test_purchase_bank_to_supplier_payment_keeps_bank(monkeypatch):
    state = _state(monkeypatch, at_pm="Bank", at_bank_pay_acct="Operating")
    erp._coerce_at_payment_method(MagicMock(), "Supplier Payment")
    assert state["at_pm"] == "Bank"
    assert state["at_bank_pay_acct"] == "Operating"


def test_sale_cash_to_expense_keeps_cash(monkeypatch):
    state = _state(monkeypatch, at_pm="Cash")
    erp._coerce_at_payment_method(MagicMock(), "Expense")
    assert state["at_pm"] == "Cash"


def test_invalid_submitted_payment_method_is_coerced_before_submit(monkeypatch):
    state = _state(monkeypatch, at_pm="Card")
    err = erp._at_validate_payment_method_for_submit(MagicMock(), "Expense")
    assert err is None
    assert state["at_pm"] == "Cash"


def test_invalid_payment_method_returns_error_when_no_allowed(monkeypatch):
    state = _state(monkeypatch, at_pm="Card")
    monkeypatch.setattr(erp, "_at_allowed_pay_methods", lambda _s, _t: [])
    err = erp._at_validate_payment_method_for_submit(MagicMock(), "Expense")
    assert err is not None
    assert "Card" in err


def test_allowed_pay_methods_per_type():
    session = MagicMock()
    assert erp._at_allowed_pay_methods(session, "Sale") == ["Cash", "Card", "Credit"]
    assert erp._at_allowed_pay_methods(session, "Expense") == ["Cash", "Bank"]
    assert erp._at_allowed_pay_methods(session, "Purchase") == [
        "Credit",
        "Cash",
        "Bank",
    ]
    assert erp._at_allowed_pay_methods(session, "Supplier Payment") == [
        "Cash",
        "Bank",
    ]
    assert erp._at_allowed_pay_methods(session, "Customer Payment") == [
        "Cash",
        "Bank",
    ]
