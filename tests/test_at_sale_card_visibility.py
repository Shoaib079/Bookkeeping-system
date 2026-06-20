"""Add Transaction — Sale Card must not expose company credit card UI."""

from __future__ import annotations

import inspect
import sys
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

import app as erp


class _FakeBankAccount:
    def __init__(self, name: str, *, kind: str = "bank"):
        self.name = name
        self.kind = kind


def test_sale_card_deposit_accounts_exclude_company_cc():
    bank = _FakeBankAccount("Main Bank", kind="bank")
    cc = _FakeBankAccount("Amex Corporate", kind="credit_card")
    result = erp._at_sale_card_deposit_accounts([bank, cc])
    assert [a.name for a in result] == ["Main Bank"]


def test_at_txn_allows_company_cc_only_on_outflows():
    assert not erp._at_txn_allows_company_cc("Sale")
    assert not erp._at_txn_allows_company_cc("Customer Payment")
    assert not erp._at_txn_allows_company_cc("Expense")  # OBS-007
    assert erp._at_txn_allows_company_cc("Purchase")
    assert erp._at_txn_allows_company_cc("Supplier Payment")


def test_salary_mode_expense_skips_company_cc():
    erp.st.session_state.update(
        {"mob_at_tab": 3, "mob_at_more_idx": erp._MOB_AT_SALARY_IDX}
    )
    try:
        assert not erp._at_txn_allows_company_cc("Expense")
    finally:
        erp.st.session_state.clear()


def test_mob_company_cc_select_guarded_by_txn_type():
    src = inspect.getsource(erp._mob_at_render_company_cc_select)
    assert "_at_txn_allows_company_cc(txn_type)" in src


def test_desktop_company_cc_select_guarded_by_txn_type():
    src = inspect.getsource(erp._at_render_company_cc_select)
    assert "_at_txn_allows_company_cc(txn_type)" in src


def test_mobile_sale_branch_no_company_cc_select():
    src = inspect.getsource(erp._render_add_transaction_mobile)
    sale_block = src.split("elif at_idx == 0:")[1].split("elif at_idx == 1")[0]
    assert "_mob_at_render_company_cc_select" not in sale_block
    assert "_mob_at_render_card_bank_trigger" in sale_block
    assert "_at_sale_card_deposit_accounts" in sale_block
    assert "not _card_settlement_on(session)" in sale_block


def test_desktop_sale_branch_no_company_cc_select():
    src = inspect.getsource(erp.render_add_transaction)
    sale_block = src.split('if txn_type == "Sale":', 1)[1].split('elif txn_type == "Expense":', 1)[0]
    assert "_at_render_company_cc_select" not in sale_block
    assert "_at_sale_card_deposit_accounts" in sale_block
    assert "not _card_settlement_on(session)" in sale_block


def test_customer_payment_branch_no_company_cc_select():
    src = inspect.getsource(erp._render_add_transaction_mobile)
    cust_block = src.split('if txn_type == "Customer Payment"', 1)[1].split(
        'elif txn_type == "Supplier Payment"', 1
    )[0]
    assert "_mob_at_render_company_cc_select" not in cust_block


@pytest.mark.parametrize(
    "txn_type,pm_key",
    [
        ("Expense", "_mob_at_render_company_cc_select"),
        ("Purchase", "_mob_at_render_company_cc_select"),
        ("Supplier Payment", "_mob_at_render_company_cc_select"),
    ],
)
def test_outflow_branches_still_wire_company_cc_select(txn_type, pm_key):
    src = inspect.getsource(erp._render_add_transaction_mobile)
    assert f'{pm_key}(session, txn_type="{txn_type}")' in src


def test_clear_invalid_card_bank_selection_drops_cc_account(monkeypatch):
    bank = _FakeBankAccount("Main Bank", kind="bank")
    cc = _FakeBankAccount("Amex Corporate", kind="credit_card")
    state = {"at_card_bank_acct": "Amex Corporate", "mob_at_card_bank_sel": "Amex Corporate"}
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_clear_invalid_card_bank_selection([bank, cc])
    assert "at_card_bank_acct" not in state
    assert "mob_at_card_bank_sel" not in state
