"""UX-04 — Repeat Last Transaction v1 (Transaction History row action)."""

from __future__ import annotations

import datetime
import inspect
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock
else:
    _st_mock = sys.modules["streamlit"]
    if not isinstance(getattr(_st_mock, "session_state", None), dict):
        _st_mock.session_state = {}

import app as erp
import models
from db import Base


class _FakeSessionState(dict):
    def get(self, key, default=None):
        return super().get(key, default)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture(autouse=True)
def allow_edit(monkeypatch):
    monkeypatch.setattr(erp, "_can", lambda _perm: True)


@pytest.fixture(autouse=True)
def no_company_cc(monkeypatch):
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        erp._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        yield s


def _company(db, company_id: int = 1):
    c = models.Company(
        id=company_id,
        name="Alpha",
        slug="alpha",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(c)
    db.flush()
    return c


def _set_active(company_id: int) -> None:
    sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _expense(**kwargs):
    defaults = dict(
        id=1,
        date=datetime.date(2020, 1, 1),
        expense_type="Expense",
        description="Lunch",
        amount=42.5,
        payment_method="Cash",
        is_void=False,
        tx_category_id=None,
        tx_subcategory_id=None,
        company_id=1,
        currency="USD",
        employee_name=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _purchase(**kwargs):
    defaults = dict(
        id=2,
        date=datetime.date(2020, 6, 15),
        description="Supplies",
        amount=100.0,
        purchase_type="Credit",
        is_void=False,
        tx_category_id=None,
        tx_subcategory_id=None,
        vendor_id=None,
        company_id=1,
        currency="USD",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _bind_src() -> str:
    return inspect.getsource(erp._txh_bind_action_buttons)


def _action_defs_src() -> str:
    return inspect.getsource(erp._txh_action_defs)


# ── Visibility / eligibility ─────────────────────────────────────────────────


def test_eligible_expense_row_can_repeat():
    e = _expense()
    assert erp._txh_repeat_eligible("ExpenseRecord", e, is_void_row=False) is True
    assert "can_repeat" in _action_defs_src()
    assert 'key=f"txh_r_{row_key}"' in _bind_src()


def test_eligible_purchase_row_can_repeat():
    e = _purchase()
    assert erp._txh_repeat_eligible("Purchase", e, is_void_row=False) is True


def test_sale_rows_do_not_show_repeat():
    sale = SimpleNamespace(id=1, is_void=False, company_id=1, amount=10, description="")
    assert erp._txh_repeat_eligible("Sale", sale, is_void_row=False) is False
    defs = erp._txh_action_defs("Sale", sale, is_void_row=False)
    assert defs["can_repeat"] is False
    assert defs["can_duplicate"] is True


def test_salary_expense_rows_do_not_show_repeat():
    e = _expense(expense_type="Salary", employee_name="Jane")
    assert erp._txh_repeat_eligible("ExpenseRecord", e, is_void_row=False) is False


def test_worker_expense_rows_do_not_show_repeat():
    e = _expense(employee_name="Bob")
    assert erp._txh_repeat_eligible("ExpenseRecord", e, is_void_row=False) is False


def test_payable_rows_do_not_show_repeat():
    p = SimpleNamespace(id=1, is_void=False, company_id=1)
    assert erp._txh_repeat_eligible("Payable", p, is_void_row=False) is False


def test_bank_transaction_rows_do_not_show_repeat():
    t = SimpleNamespace(id=1, is_void=False, company_id=1)
    assert erp._txh_repeat_eligible("BankTransaction", t, is_void_row=False) is False


def test_voided_rows_do_not_show_repeat():
    e = _expense(is_void=True)
    assert erp._txh_repeat_eligible("ExpenseRecord", e, is_void_row=True) is False


def test_handler_refuses_ineligible_rows(monkeypatch):
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    session = MagicMock()
    assert erp._txh_apply_repeat_prefill(session, "Sale", _expense()) is False
    assert "at_amount_display" not in state


def test_company_mismatch_refused(monkeypatch):
    _set_active(1)
    e = _expense(company_id=99)
    assert erp._txh_repeat_eligible("ExpenseRecord", e, is_void_row=False) is False
    assert erp._txh_apply_repeat_prefill(MagicMock(), "ExpenseRecord", e) is False


# ── Prefill behavior ─────────────────────────────────────────────────────────


def test_repeat_date_becomes_today(monkeypatch, db):
    _company(db)
    _set_active(1)
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "load_settings", lambda: {"currency": "USD"})
    e = _expense(date=datetime.date(2019, 5, 5))
    assert erp._txh_apply_repeat_prefill(db, "ExpenseRecord", e) is True
    assert state["at_date"] == datetime.date.today()


def test_repeat_amount_and_notes_copied(monkeypatch, db):
    _company(db)
    _set_active(1)
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "load_settings", lambda: {"currency": "USD"})
    e = _expense(amount=77.25, description="Team lunch")
    erp._txh_apply_repeat_prefill(db, "ExpenseRecord", e)
    assert state["at_amount_display"] == "77.25"
    assert state["at_notes_field"] == "Team lunch"


def test_active_category_and_subcategory_copied(monkeypatch, db):
    co = _company(db)
    _set_active(co.id)
    cat = models.TransactionCategory(
        name="Travel",
        transaction_type="Expense",
        is_active=True,
        company_id=co.id,
    )
    db.add(cat)
    db.flush()
    sub = models.TransactionSubcategory(
        category_id=cat.id,
        name="Meals",
        is_active=True,
        company_id=co.id,
    )
    db.add(sub)
    db.flush()
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "load_settings", lambda: {"currency": "USD"})
    e = _expense(tx_category_id=cat.id, tx_subcategory_id=sub.id)
    erp._txh_apply_repeat_prefill(db, "ExpenseRecord", e)
    assert state["mob_at_cat_id"] == cat.id
    assert state["at_cat"] == "Travel"
    assert state["mob_at_subcat_id"] == sub.id
    assert state["at_subcat"] == "Meals"


def test_inactive_category_and_subcategory_dropped(monkeypatch, db):
    co = _company(db)
    _set_active(co.id)
    cat = models.TransactionCategory(
        name="Old",
        transaction_type="Expense",
        is_active=False,
        company_id=co.id,
    )
    db.add(cat)
    db.flush()
    sub = models.TransactionSubcategory(
        category_id=cat.id,
        name="OldSub",
        is_active=False,
        company_id=co.id,
    )
    db.add(sub)
    db.flush()
    state = _FakeSessionState({"mob_at_cat_id": 999, "at_subcat": "stale"})
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "load_settings", lambda: {"currency": "USD"})
    e = _expense(tx_category_id=cat.id, tx_subcategory_id=sub.id)
    erp._txh_apply_repeat_prefill(db, "ExpenseRecord", e)
    assert "mob_at_cat_id" not in state
    assert "at_subcat" not in state


def test_purchase_vendor_copied_when_active(monkeypatch, db):
    co = _company(db)
    _set_active(co.id)
    vendor = models.Vendor(name="Acme", is_active=True, company_id=co.id)
    db.add(vendor)
    db.flush()
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "load_settings", lambda: {"currency": "USD"})
    p = _purchase(vendor_id=vendor.id)
    erp._txh_apply_repeat_prefill(db, "Purchase", p)
    assert state["at_vendor"] == "Acme"
    assert state["mob_at_vendor_sel"] == "Acme"


def test_inactive_vendor_dropped(monkeypatch, db):
    co = _company(db)
    _set_active(co.id)
    vendor = models.Vendor(name="Gone", is_active=False, company_id=co.id)
    db.add(vendor)
    db.flush()
    state = _FakeSessionState({"at_vendor": "stale"})
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "load_settings", lambda: {"currency": "USD"})
    p = _purchase(vendor_id=vendor.id)
    erp._txh_apply_repeat_prefill(db, "Purchase", p)
    assert "at_vendor" not in state


def test_payment_method_coerces_when_invalid(monkeypatch, db):
    _company(db)
    _set_active(1)
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "load_settings", lambda: {"currency": "USD"})
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)
    e = _expense(payment_method=erp._COMPANY_CC_METHOD)
    erp._txh_apply_repeat_prefill(db, "ExpenseRecord", e)
    assert state["at_pm"] == "Cash"


def test_forbidden_fields_never_copied(monkeypatch, db):
    _company(db)
    _set_active(1)
    state = _FakeSessionState(
        {
            "at_cust": "keep-me-out",
            "at_worker_id": 5,
            "at_payable_id": 9,
        }
    )
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "load_settings", lambda: {"currency": "USD"})
    e = _expense(
        id=99,
        created_by_id=7,
        description="ok",
    )
    erp._txh_apply_repeat_prefill(db, "ExpenseRecord", e)
    assert "at_cust" not in state
    assert "at_worker_id" not in state
    assert "at_payable_id" not in state
    assert state["nav_selection"] == "➕ New Transaction"
    assert state["at_type_idx"] == 1


def test_no_posting_or_save_during_repeat(monkeypatch, db):
    _company(db)
    _set_active(1)
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "load_settings", lambda: {"currency": "USD"})
    save = MagicMock()
    post_exp = MagicMock()
    post_pur = MagicMock()
    monkeypatch.setattr(erp, "_at_save", save)
    monkeypatch.setattr(erp, "post_expense", post_exp)
    monkeypatch.setattr(erp, "post_purchase", post_pur)
    erp._txh_apply_repeat_prefill(db, "ExpenseRecord", _expense())
    save.assert_not_called()
    post_exp.assert_not_called()
    post_pur.assert_not_called()


def test_repeat_navigates_to_add_transaction(monkeypatch, db):
    _company(db)
    _set_active(1)
    state = _FakeSessionState()
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp, "load_settings", lambda: {"currency": "EUR"})
    p = _purchase(currency="EUR")
    erp._txh_apply_repeat_prefill(db, "Purchase", p)
    assert state["at_type_idx"] == 2
    assert state["mob_at_tab"] == 2
    assert state["at_currency"] == "EUR"
