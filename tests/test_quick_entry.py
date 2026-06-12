"""QUICK-ENTRY-01 — mobile Add Transaction category quick chips."""

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


def _cat(cid: int, name: str):
    class _C:
        transaction_type = "Sale"
        is_active = True

        def __init__(self):
            self.id = cid
            self.name = name

    return _C()


def _make_sale_options(count: int) -> list[erp._MobAtGridPick]:
    return [
        erp._MobAtGridPick(f"c{i}", f"Cat {chr(64 + i)}", cat_id=i)
        for i in range(1, count + 1)
    ]


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


def test_mob_at_quick_chips_returns_top_five_alphabetically(monkeypatch):
    options = _make_sale_options(7)
    monkeypatch.setattr(erp, "_mob_at_category_options", lambda _s, _t: options)
    chips = erp._mob_at_quick_chips(None, "Sale")
    assert len(chips) == 5
    assert [c.label for c in chips] == ["Cat A", "Cat B", "Cat C", "Cat D", "Cat E"]


def test_mob_at_quick_chips_keeps_selected_outside_top_five(monkeypatch):
    options = _make_sale_options(7)
    state = _FakeSessionState({"mob_at_cat_id": 7})
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "_mob_at_category_options", lambda _s, _t: options)
    chips = erp._mob_at_quick_chips(None, "Sale")
    assert len(chips) == 5
    assert chips[-1].key == "c7"
    assert chips[-1].label == "Cat G"


def test_mob_at_quick_chips_is_pure_helper(monkeypatch):
    options = _make_sale_options(3)
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "_mob_at_category_options", lambda _s, _t: options)
    erp._mob_at_quick_chips(None, "Sale")
    assert "mob_at_cat_id" not in state


def test_mob_at_apply_category_pick_resets_subcategory(monkeypatch):
    state = _FakeSessionState({"mob_at_subcat_id": 9, "at_subcat": "Office"})
    monkeypatch.setattr(erp.st, "session_state", state)
    pick = erp._MobAtGridPick("c3", "Fuel", cat_id=3)
    erp._mob_at_apply_category_pick(None, pick, txn_type="Expense")
    assert state["mob_at_cat_id"] == 3
    assert "mob_at_subcat_id" not in state
    assert "at_subcat" not in state
    assert "mob_at_last_cat_expense" not in state


def test_mob_at_category_memory_disabled(monkeypatch):
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_apply_category_pick(
        None, erp._MobAtGridPick("c1", "Retail", cat_id=1), txn_type="Sale"
    )
    erp._mob_at_apply_category_pick(
        None, erp._MobAtGridPick("c2", "Rent", cat_id=2), txn_type="Expense"
    )
    assert "mob_at_last_cat_sale" not in state
    assert "mob_at_last_cat_expense" not in state


def test_mob_at_seed_visible_category_is_noop(monkeypatch):
    options = [
        erp._MobAtGridPick("c1", "Alpha", cat_id=1),
        erp._MobAtGridPick("c2", "Beta", cat_id=2),
    ]
    state = _FakeSessionState({"mob_at_last_cat_sale": 2})
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "_mob_at_category_options", lambda _s, _t: options)
    monkeypatch.setattr(erp, "_mob_at_subcategory_options", lambda _s, _cid: [])

    class _Session:
        def get(self, model, cid):
            cat = _cat(cid, "Beta")
            cat.transaction_type = "Sale"
            return cat if cid == 2 else None

    erp._mob_at_seed_visible_category(_Session(), "Sale")
    assert "mob_at_cat_id" not in state


def test_mob_at_seed_visible_category_does_not_auto_pick(monkeypatch):
    options = [erp._MobAtGridPick("c9", "Only", cat_id=9)]
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "_mob_at_category_options", lambda _s, _t: options)
    erp._mob_at_seed_visible_category(None, "Purchase")
    assert "mob_at_cat_id" not in state
    assert "mob_at_last_cat_purchase" not in state


def test_company_scoped_keys_include_last_category_memory():
    for key in (
        "mob_at_last_cat_sale",
        "mob_at_last_cat_expense",
        "mob_at_last_cat_purchase",
    ):
        assert key in erp._COMPANY_SCOPED_AT_KEYS


def test_clear_company_scoped_session_state_clears_last_category_memory():
    st = sys.modules["streamlit"].session_state
    st.update(
        {
            "mob_at_last_cat_sale": 1,
            "mob_at_last_cat_expense": 2,
            "mob_at_last_cat_purchase": 3,
        }
    )
    erp._clear_company_scoped_session_state()
    assert "mob_at_last_cat_sale" not in st
    assert "mob_at_last_cat_expense" not in st
    assert "mob_at_last_cat_purchase" not in st


def test_mobile_at_wires_quick_chips_for_expense_purchase_only():
    src = inspect.getsource(erp._render_add_transaction_mobile)
    assert '_mob_at_render_quick_cat_chips(session, "Sale"' not in src
    assert '_mob_at_render_quick_cat_chips(session, "Expense"' in src
    assert '_mob_at_render_quick_cat_chips(session, "Purchase"' in src
    assert src.count("_mob_at_render_c_cat_row(") == 0


def test_mob_at_render_c_cat_row_still_available():
    assert callable(erp._mob_at_render_c_cat_row)


def test_non_category_transaction_types_unchanged():
    src = inspect.getsource(erp._render_add_transaction_mobile)
    supplier_block = src.split('elif txn_type == "Supplier Payment"', 1)[1].split("elif txn_type ==", 1)[0]
    assert "_mob_at_render_quick_cat_chips" not in supplier_block
    assert "_at_clear_category_session_state()" in supplier_block
    bank_block = src.split('elif txn_type == "Bank Transaction"', 1)[1].split("elif ", 1)[0]
    assert "_mob_at_render_quick_cat_chips" not in bank_block


def test_quick_chip_renderer_opens_existing_picker(monkeypatch):
    state = _FakeSessionState()
    opened: list[str] = []
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(
        erp,
        "_mob_at_category_options",
        lambda _s, _t: [erp._MobAtGridPick("c1", "Rent", cat_id=1)],
    )
    monkeypatch.setattr(erp, "_mob_at_open_picker", lambda kind: opened.append(kind))

    class _Col:
        def __init__(self):
            self._handlers = []

        def button(self, _label, key=None, **_kw):
            self._handlers.append((key, _kw.get("type")))
            return key.endswith("_more")

    class _Cols(list):
        def __getitem__(self, idx):
            return self[idx]

    cols = [_Col(), _Col()]

    class _Container:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(erp.st, "container", lambda **_kw: _Container())
    monkeypatch.setattr(erp.st, "columns", lambda n, **_kw: cols[:n])

    assert erp._mob_at_render_quick_cat_chips(None, "Expense", picker_kind="expense_cat") is True
    assert opened == ["expense_cat"]


def test_quick_cat_chips_css_contract():
    css = (ROOT / "ui" / "mobile_txn.css").read_text(encoding="utf-8")
    block = css.split("QUICK-ENTRY-01", 1)[1].split("Category row:", 1)[0]
    light = css.split("AT-LIGHT-01", 1)[1].split("Keyed rows", 1)[0]
    assert "st-key-mob_at_quick_cat_chips" in block
    assert "flex-wrap: wrap" in block
    assert "gap: 6px" in block
    assert "st-key-mob_at_quick_cat_chips" in light
    assert "background: transparent" in light
    assert "--mob-at-chip-idle-bg" in block, "idle chip token must be set in QUICK-ENTRY-01 block"
    assert "--mob-at-chip-idle-fg" in block, "idle chip fg token must be set in QUICK-ENTRY-01 block"
    assert "--mob-at-chip-idle-border" in block, "idle chip border token must be set in QUICK-ENTRY-01 block"
