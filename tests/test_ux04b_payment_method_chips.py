"""UX-04B — mobile Add Transaction payment method chips."""

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


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


def test_sale_pm_chip_methods():
    assert erp._mob_at_pm_chip_methods(MagicMock(), "Sale") == erp._at_sale_pay_methods(
        MagicMock()
    )
    assert erp._mob_at_pm_chip_methods(MagicMock(), "Sale") == ["Cash", "Card", "Credit"]


def test_expense_pm_chip_methods_without_cc(monkeypatch):
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)
    assert erp._mob_at_pm_chip_methods(MagicMock(), "Expense") == ["Cash", "Bank"]


def test_expense_pm_chip_methods_with_cc(monkeypatch):
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: True)
    methods = erp._mob_at_pm_chip_methods(MagicMock(), "Expense")
    assert methods == ["Cash", "Bank", erp._COMPANY_CC_METHOD]


def test_purchase_pm_chip_methods_with_cc(monkeypatch):
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: True)
    methods = erp._mob_at_pm_chip_methods(MagicMock(), "Purchase")
    assert methods == ["Credit", "Cash", "Bank", erp._COMPANY_CC_METHOD]


def test_bank_transaction_has_no_pm_chip_row():
    assert erp._mob_at_pm_chip_methods(MagicMock(), "Bank Transaction") == []


def test_pm_chip_tap_sets_at_pm_and_clears_stale_keys(monkeypatch):
    state = _FakeSessionState({"at_pm": "Cash", "at_card_bank_acct": "Main"})
    cleared: list[str] = []
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
        "_at_clear_stale_payment_account_keys",
        lambda pm: cleared.append(pm),
    )

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
    assert state["at_pm"] == "Card"
    assert cleared == ["Card"]


def test_type_change_coerces_invalid_pm(monkeypatch):
    state = _FakeSessionState({"at_pm": "Card"})
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)
    erp._coerce_at_payment_method(MagicMock(), "Expense")
    assert state["at_pm"] == "Cash"


def test_post_save_resets_payment_method(monkeypatch):
    state = _FakeSessionState({"at_pm": "Bank", "at_amount_display": "50", "at_notes_field": "x"})
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)
    erp._at_clear_post_save_transient_fields(
        MagicMock(), txn_type="Expense", currency_default="TRY"
    )
    assert "at_pm" not in state
    assert "at_amount_display" not in state
    assert "at_notes_field" not in state
    erp._mob_at_ensure_defaults(MagicMock(), "Expense", "TRY", [])
    assert state["at_pm"] == "Cash"


def test_row1_has_three_buttons_only():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    start = src.index("def _mob_at_render_c_row1")
    block = src[start : src.index("def _mob_at_render_c_cat_row", start)]
    assert "mob_at_c_type_btn" in block
    assert "mob_at_c_date_btn" in block
    assert "mob_at_c_currency_btn" in block
    assert "mob_at_c_pm_btn" not in block
    assert block.count("st.columns") == 1
    assert "rc = st.columns([2.5, 1.5, 1.0]" in block


def test_payment_picker_retired():
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "_mob_at_render_payment_picker_sheet" not in app_src
    assert 'picker_kind == "payment"' not in app_src
    assert '_mob_at_open_picker("payment")' not in app_src


def test_mob_at_pm2_bank_subtype_untouched():
    mobile = inspect.getsource(erp._render_add_transaction_mobile)
    assert 'row_key="mob_at_pm2"' in mobile
    bank_block = mobile.split('txn_type == "Bank Transaction"', 1)[1].split(
        "_mob_at_render_amount_keypad_fragment", 1
    )[0]
    assert "mob_at_pm2" in bank_block
    assert "_mob_at_render_pm_chip_row" not in bank_block


def test_desktop_at_still_uses_selectbox_for_pm():
    desktop = inspect.getsource(erp.render_add_transaction)
    mobile = inspect.getsource(erp._render_add_transaction_mobile)
    assert "_mob_at_render_pm_chip_row" in mobile
    assert "_mob_at_render_pm_chip_row" not in desktop
    assert 'key="at_pm"' in desktop


def test_pm_chip_row_css_contract():
    css = (ROOT / "ui" / "mobile_txn.css").read_text(encoding="utf-8")
    assert "st-key-mob_at_pm_row" in css
    assert "flex-wrap: wrap" in css.split("mob_at_pm_row", 1)[1].split("mob_at_quick_cat_chips", 1)[0]
    wrapper = css.split("AT-LIGHT-01 — strip Streamlit", 1)[1].split("/* Keyed rows", 1)[0]
    assert "st-key-mob_at_pm_row" in wrapper


def test_widgets_pm_chip_selected_rule():
    css = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    assert "st-key-mob_at_pm_row" in css
    assert "st-key-mob_at_pm_" in css
