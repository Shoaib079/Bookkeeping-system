"""P0-4 — Transaction Ledger type filter displays localized labels."""

from __future__ import annotations

import inspect

import app as erp
from registry.i18n import t

_TXH_TYPE_FILTER_I18N = erp._TXH_TYPE_FILTER_I18N


def test_txh_type_filter_map_covers_all_filter_values():
    assert set(_TXH_TYPE_FILTER_I18N) == {
        "Sale",
        "Expense",
        "Purchase",
        "Banking",
        "Payable",
    }


def test_txh_type_filter_tr_labels():
    assert t(_TXH_TYPE_FILTER_I18N["Sale"], "tr") == "Satış"
    assert t(_TXH_TYPE_FILTER_I18N["Banking"], "tr") == "Bankacılık"
    assert t(_TXH_TYPE_FILTER_I18N["Payable"], "tr") == "Borç"


def test_render_txh_type_selectbox_uses_format_func():
    src = inspect.getsource(erp.render_transaction_history)
    assert "_TXH_TYPE_FILTER_I18N" in src
    assert "format_func=lambda v: v if v == _txh_all else _i18n_db(_TXH_TYPE_FILTER_I18N, v)" in src
