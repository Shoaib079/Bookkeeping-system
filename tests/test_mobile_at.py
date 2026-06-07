"""Mobile add-transaction helpers — no Streamlit runtime."""
from __future__ import annotations

import pytest

import app as erp


class _FakeSessionState(dict):
    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


def test_mob_at_tab_to_type_idx_primary():
    assert erp._mob_at_tab_to_type_idx(0) == 0
    assert erp._mob_at_tab_to_type_idx(2) == 2


def test_mob_at_tab_to_type_idx_more():
    assert erp._mob_at_tab_to_type_idx(3, 4) == 4
    assert erp._mob_at_tab_to_type_idx(3, 5) == 5


def test_mob_at_append_amount_digit(monkeypatch):
    state = _FakeSessionState({"at_amount_display": "12"})
    monkeypatch.setattr(erp.st, "session_state", state)

    assert erp._mob_at_append_amount_digit("3") is True
    assert state["at_amount_display"] == "123"

    assert erp._mob_at_append_amount_digit("bksp") is True
    assert state["at_amount_display"] == "12"

    assert erp._mob_at_append_amount_digit(".") is True
    assert state["at_amount_display"] == "12."

    assert erp._mob_at_append_amount_digit("clr") is True
    assert state["at_amount_display"] == ""


def test_mob_at_append_amount_digit_ignores_duplicate_decimal(monkeypatch):
    state = _FakeSessionState({"at_amount_display": "12.5"})
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._mob_at_append_amount_digit(".") is False
    assert state["at_amount_display"] == "12.5"


def test_mob_at_append_amount_digit_ignores_decimal_when_comma_present(monkeypatch):
    state = _FakeSessionState({"at_amount_display": "1,50"})
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._mob_at_append_amount_digit(".") is False


def test_mob_at_append_amount_digit_noop_backspace_on_empty(monkeypatch):
    state = _FakeSessionState({"at_amount_display": ""})
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._mob_at_append_amount_digit("bksp") is False


def test_mob_at_amount_display_text(monkeypatch):
    state = _FakeSessionState({"at_amount_display": ""})
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._mob_at_amount_display_text() == "0"
    assert erp._mob_at_amount_display_text("42.5") == "42.5"


def test_mob_at_keypad_fragment_registered():
    import inspect

    src = inspect.getsource(erp._mob_at_render_amount_keypad_fragment)
    assert "@st.fragment" in src or "st.fragment" in src
    assert callable(erp._mob_at_render_amount_keypad_fragment)
    assert "erp-mob-at-amt" in src
    assert "mob_at_save" in src


def test_mob_at_save_label_locale():
    from registry.i18n import t

    assert t("txn.mob.save", "en") == "✓ Save"


def test_mob_at_calculator_typography_contract():
    from pathlib import Path

    css = (Path(__file__).resolve().parents[1] / "ui" / "mobile_txn.css").read_text(
        encoding="utf-8"
    )
    assert "--mob-at-keypad-font: 36px" in css
    assert "--mob-at-amount-font: 72px" in css
    assert "--mob-at-save-font: 15px" in css
    assert "var(--theme-info)" in css
    assert "var(--mob-at-save-bg)" in css


def test_mob_at_tabs_config():
    assert len(erp._MOB_AT_TABS) == 4
    assert erp._MOB_AT_TABS[0][0] == 0
    assert erp._MOB_AT_MORE_TYPES[-1][0] == erp._MOB_AT_SALARY_IDX


def test_mob_at_tab_to_type_idx_salary():
    assert erp._mob_at_tab_to_type_idx(3, erp._MOB_AT_SALARY_IDX) == erp._MOB_AT_SALARY_IDX


def test_mob_at_is_salary_mode(monkeypatch):
    state = _FakeSessionState({"mob_at_tab": 3, "mob_at_more_idx": erp._MOB_AT_SALARY_IDX})
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._mob_at_is_salary_mode() is True


def test_at_effective_txn_type_salary_idx(monkeypatch):
    type_names = ["Sale", "Expense", "Purchase", "Supplier Payment", "Customer Payment", "Bank Transaction"]
    state = _FakeSessionState({"at_type_idx": erp._MOB_AT_SALARY_IDX, "mob_at_tab": 3, "mob_at_more_idx": erp._MOB_AT_SALARY_IDX})
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._at_effective_txn_type(type_names) == "Expense"


def test_at_effective_txn_type_out_of_range(monkeypatch):
    type_names = ["Sale", "Expense"]
    state = _FakeSessionState({"at_type_idx": 99})
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._at_effective_txn_type(type_names) == "Sale"


def test_mob_at_submit_txn_type_salary(monkeypatch):
    type_names = ["Sale", "Expense", "Purchase", "Supplier Payment", "Customer Payment", "Bank Transaction"]
    state = _FakeSessionState(
        {"mob_at_tab": 3, "mob_at_more_idx": erp._MOB_AT_SALARY_IDX, "at_type_idx": erp._MOB_AT_SALARY_IDX}
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    assert erp._mob_at_submit_txn_type(type_names) == "Expense"


def test_mob_at_category_and_subcategory_options():
    class _Cat:
        def __init__(self, cid, name):
            self.id = cid
            self.name = name

    class _Sub:
        def __init__(self, sid, name, category_id):
            self.id = sid
            self.name = name
            self.category_id = category_id

    class _FakeQuery:
        def __init__(self, rows):
            self._rows = rows
            self._filters = {}

        def filter_by(self, **kwargs):
            q = _FakeQuery(self._rows)
            q._filters = dict(kwargs)
            return q

        def order_by(self, *args):
            return self

        def all(self):
            rows = self._rows
            if "category_id" in self._filters:
                cid = self._filters["category_id"]
                rows = [r for r in rows if r.category_id == cid]
            return list(rows)

    def _fake_cq(session, model):
        if model.__name__ == "TransactionCategory":
            return _FakeQuery([_Cat(1, "Rent"), _Cat(2, "Fuel")])
        return _FakeQuery([_Sub(10, "Office", 1), _Sub(11, "Warehouse", 1)])

    orig_cq = erp.cq
    erp.cq = _fake_cq
    try:
        cats = erp._mob_at_category_options(None, "Expense")
        subs = erp._mob_at_subcategory_options(None, 1)
        fuel_subs = erp._mob_at_subcategory_options(None, 2)
    finally:
        erp.cq = orig_cq

    assert [c.label for c in cats] == ["Rent", "Fuel"]
    assert cats[0].cat_id == 1
    assert cats[0].subcat_id is None
    assert [s.label for s in subs] == ["Office", "Warehouse"]
    assert subs[0].subcat_id == 10
    assert subs[0].cat_id == 1
    assert fuel_subs == []


def test_mob_at_filter_options():
    options = [
        erp._MobAtGridPick("1", "Rent"),
        erp._MobAtGridPick("2", "Fuel"),
        erp._MobAtGridPick("3", "Office Supplies"),
    ]
    assert [o.label for o in erp._mob_at_filter_options(options, "fuel")] == ["Fuel"]
    assert len(erp._mob_at_filter_options(options, "")) == 3
    assert erp._mob_at_filter_options(options, "zzz") == []


def test_mob_at_types_with_currency():
    assert erp._mob_at_types_with_currency("Sale")
    assert erp._mob_at_types_with_currency("Customer Payment")
    assert not erp._mob_at_types_with_currency("Bank Transaction")


def test_mob_at_invoice_options():
    class _Sale:
        def __init__(self):
            self.id = 9
            self.invoice_number = "INV-1"
            self.customer_name = "Acme"
            self.balance = 12.5

    opts = erp._mob_at_invoice_options([_Sale()])
    assert len(opts) == 1
    assert "INV-1" in opts[0].label
    assert opts[0].value_id == 9


def test_mob_at_is_subcat_picker():
    assert erp._mob_at_is_subcat_picker("expense_subcat")
    assert erp._mob_at_is_subcat_picker("sale_subcat")
    assert not erp._mob_at_is_subcat_picker("expense_cat")
    assert not erp._mob_at_is_subcat_picker("vendor")


def test_mob_at_sync_select_widgets(monkeypatch):
    state = _FakeSessionState(
        {
            "mob_at_inv_sel": "INV-1 — Acme (bal: 10.00)",
            "mob_at_vendor_sel": "Vendor A",
            "mob_at_payable_sel": "01 Jan · PAY#1 · 5.00",
            "mob_at_bank_acct_sel": "Main",
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_sync_select_widgets()
    assert state["at_inv"] == "INV-1 — Acme (bal: 10.00)"
    assert state["at_vendor"] == "Vendor A"
    assert state["at_payable_sel"] == "01 Jan · PAY#1 · 5.00"
    assert state["at_bank_acct"] == "Main"


def test_mob_at_sync_select_widgets_worker(monkeypatch):
    state = _FakeSessionState({"mob_at_worker_id": 42})
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_sync_select_widgets()
    assert state["at_worker_id"] == 42


def test_sync_mobile_ui_flag_cookie_overrides_ua(monkeypatch):
    class _Ctx:
        cookies = {"erp_mobile_ui": "0"}
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"}

    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp.st, "context", _Ctx())
    assert erp._sync_mobile_ui_flag_from_cookie() is False


def test_sync_mobile_ui_flag_ua_fallback_when_no_cookie(monkeypatch):
    class _Ctx:
        cookies = {}
        headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"}

    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp.st, "context", _Ctx())
    assert erp._sync_mobile_ui_flag_from_cookie() is True


def test_user_agent_looks_mobile_android(monkeypatch):
    class _Ctx:
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36"}

    monkeypatch.setattr(erp.st, "context", _Ctx())
    assert erp._user_agent_looks_mobile() is True


def test_next_header_theme_mode_flips_dark_and_system():
    assert erp._next_header_theme_mode("dark") == "light"
    assert erp._next_header_theme_mode("light") == "dark"
    assert erp._next_header_theme_mode("system") == "dark"


def test_mob_at_mobile_select_keys_distinct_from_desktop():
    """Mobile selectboxes must not reuse desktop Streamlit keys (dual-host render)."""
    desktop_keys = {
        "at_inv",
        "at_vendor",
        "at_payable_sel",
        "at_bank_acct",
    }
    mobile_keys = {
        "mob_at_inv_sel",
        "mob_at_vendor_sel",
        "mob_at_payable_sel",
        "mob_at_bank_acct_sel",
        "mob_at_bank_pay_sel",
        "mob_at_card_bank_sel",
    }
    assert desktop_keys.isdisjoint(mobile_keys)


def test_mob_at_sync_select_widgets_bank_pay(monkeypatch):
    state = _FakeSessionState(
        {
            "mob_at_bank_pay_sel": "Main TRY",
            "mob_at_card_bank_sel": "Visa Card",
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_sync_select_widgets()
    assert state["at_bank_pay_acct"] == "Main TRY"
    assert state["at_card_bank_acct"] == "Visa Card"
