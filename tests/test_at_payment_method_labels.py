"""Add Transaction — context-specific payment method display labels."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

import app as erp


@pytest.fixture(autouse=True)
def _no_company_cc(monkeypatch):
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)


def test_sale_stored_credit_displays_as_on_account():
    label = erp._at_payment_method_label("Sale", "Credit")
    assert label == erp._t("txn.pm.sale_on_account")
    assert label == "On Account"


def test_purchase_stored_credit_displays_as_pay_later():
    label = erp._at_payment_method_label("Purchase", "Credit")
    assert label == erp._t("txn.pm.purchase_pay_later")
    assert label == "Pay Later"


def test_company_credit_card_distinct_from_sale_card(monkeypatch):
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: True)
    cc_label = erp._at_payment_method_label("Purchase", erp._COMPANY_CC_METHOD)
    card_label = erp._at_payment_method_label("Sale", "Card")
    assert cc_label == "Company Credit Card"
    assert card_label == "Card"
    assert cc_label != card_label


def test_stored_payment_values_unchanged():
    session = MagicMock()
    assert erp._at_allowed_pay_methods(session, "Sale") == ["Cash", "Card", "Credit"]
    assert erp._at_purchase_pay_methods(session) == ["Credit", "Cash", "Bank"]
    assert erp._at_expense_pay_methods(session) == ["Cash", "Bank"]


def test_global_credit_label_unchanged_outside_at_context():
    """PAYMENT_METHOD_I18N Credit stays generic for non-AT surfaces."""
    assert erp._i18n_db(erp.PAYMENT_METHOD_I18N, "Credit") == erp._t("expense.pay.credit")


def test_at_chip_labels_use_context_labels():
    chips = erp._at_pm_chip_labels("Sale", ["Cash", "Card", "Credit"])
    assert chips[2] == ("Credit", "On Account")
    assert chips[1] == ("Card", "Card")
