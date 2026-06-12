"""Supplier Payment AT UI — category visibility and payment-like label filter."""
from __future__ import annotations

import inspect

import app as erp


def test_payment_like_category_names():
    assert erp._at_is_payment_like_category_name("Cash")
    assert erp._at_is_payment_like_category_name("BANK")
    assert erp._at_is_payment_like_category_name("Credit Card")
    assert erp._at_is_payment_like_category_name("Cash Sale")
    assert not erp._at_is_payment_like_category_name("Utilities")
    assert not erp._at_is_payment_like_category_name("Retail")


class _Named:
    def __init__(self, name: str):
        self.name = name


def test_filter_transaction_categories_drops_payment_labels():
    cats = [
        _Named("Utilities"),
        _Named("Cash"),
        _Named("Bank"),
        _Named("Inventory"),
    ]
    filtered = erp._at_filter_transaction_categories(cats)
    assert [c.name for c in filtered] == ["Utilities", "Inventory"]


def test_supplier_payment_desktop_has_no_category_rows():
    src = inspect.getsource(erp.render_add_transaction)
    sp_start = src.index(
        '                        elif txn_type == "Supplier Payment":\n'
        '                            _at_clear_category_session_state()\n'
        '                            vendor_name_val = _inline_vendor_row'
    )
    sp_end = src.index('                        elif txn_type == "Customer Payment"', sp_start)
    block = src[sp_start:sp_end]
    assert "_inline_cat_row" not in block
    assert "_inline_subcat_row" not in block
    assert "_at_clear_category_session_state()" in block


def test_supplier_payment_mobile_has_no_category_triggers():
    src = inspect.getsource(erp._render_add_transaction_mobile)
    sp_start = src.index('elif txn_type == "Supplier Payment"')
    sp_end = src.index('elif txn_type == "Bank Transaction"')
    block = src[sp_start:sp_end]
    assert "_mob_at_render_cat_subcat_triggers" not in block
    assert "_at_clear_category_session_state()" in block


def test_category_options_filter_in_helpers():
    assert " _at_filter_transaction_categories(" in inspect.getsource(erp._mob_at_category_options)
    assert " _at_filter_transaction_categories(" in inspect.getsource(erp._inline_cat_row)
    assert " _at_filter_transaction_categories(" in inspect.getsource(erp._inline_subcat_row)
