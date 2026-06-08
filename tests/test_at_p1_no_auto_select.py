"""P1 — no auto-selection of payables, invoices, or first vendor in Add Transaction."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

from db import Base
import models
import app as erp


class _FakeSessionState(dict):
    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    erp.st.session_state = _FakeSessionState()
    with Session() as session:
        yield session


def _company(db):
    co = models.Company(
        name="Acme",
        slug="acme",
        is_active=True,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    db.add(co)
    db.commit()
    erp.st.session_state["active_company_id"] = co.id
    return co


def _vendor(db, co, name="Supplier A"):
    v = models.Vendor(name=name, company_id=co.id, is_active=True)
    db.add(v)
    db.commit()
    return v


def _payable(db, co, vendor, amount=100.0):
    p = models.Payable(
        date=datetime.date.today(),
        vendor_id=vendor.id,
        amount=amount,
        paid_amount=0.0,
        balance=amount,
        due_date=datetime.date.today(),
        paid=False,
        company_id=co.id,
    )
    db.add(p)
    db.commit()
    return p


def _credit_sale(db, co, amount=200.0):
    s = models.Sale(
        date=datetime.date.today(),
        invoice_number="INV-100",
        customer_name="Customer",
        amount=amount,
        sale_type="Credit",
        paid_amount=0.0,
        balance=amount,
        due_date=datetime.date.today(),
        status="Open",
        company_id=co.id,
    )
    db.add(s)
    db.commit()
    return s


@pytest.fixture(autouse=True)
def _no_company_cc(monkeypatch):
    monkeypatch.setattr(erp, "_company_cc_charge_ready", lambda _s: False)


def test_purchase_ensure_defaults_does_not_set_first_vendor(monkeypatch):
    state = _FakeSessionState({})
    monkeypatch.setattr(erp.st, "session_state", state)
    vendors = [
        models.Vendor(id=1, name="First", is_active=True),
        models.Vendor(id=2, name="Second", is_active=True),
    ]
    erp._mob_at_ensure_defaults(MagicMock(), "Purchase", "TRY", vendors)
    assert "at_vendor" not in state


def test_supplier_payment_ensure_defaults_does_not_set_first_vendor(monkeypatch):
    state = _FakeSessionState({})
    monkeypatch.setattr(erp.st, "session_state", state)
    vendors = [models.Vendor(id=1, name="First", is_active=True)]
    erp._mob_at_ensure_defaults(MagicMock(), "Supplier Payment", "TRY", vendors)
    assert "at_vendor" not in state


def test_gather_fields_no_invoice_default(monkeypatch):
    state = _FakeSessionState({})
    monkeypatch.setattr(erp.st, "session_state", state)
    sale = models.Sale(
        invoice_number="INV-1",
        customer_name="Cust",
        balance=50.0,
        sale_type="Credit",
    )
    ctx = erp._at_gather_submit_fields(
        MagicMock(), "Customer Payment", "TRY", [], [], [sale]
    )
    assert ctx["invoice_choice_val"] is None


def test_gather_fields_rejects_placeholder_invoice(monkeypatch):
    state = _FakeSessionState({"at_inv": erp._t("txn.select_invoice_ph")})
    monkeypatch.setattr(erp.st, "session_state", state)
    sale = models.Sale(
        date=datetime.date.today(),
        invoice_number="INV-1",
        customer_name="Cust",
        amount=80.0,
        sale_type="Credit",
        balance=80.0,
        status="Open",
    )
    ctx = erp._at_gather_submit_fields(
        MagicMock(), "Customer Payment", "TRY", [], [], [sale]
    )
    assert ctx["invoice_choice_val"] is None


def test_gather_fields_no_vendor_default(monkeypatch, db):
    co = _company(db)
    state = _FakeSessionState({"active_company_id": co.id})
    monkeypatch.setattr(erp.st, "session_state", state)
    vendors = [models.Vendor(id=1, name="Only", company_id=co.id, is_active=True)]
    ctx = erp._at_gather_submit_fields(db, "Purchase", "TRY", vendors, [], [])
    assert ctx["vendor_name_val"] is None


def test_supplier_payment_submit_blocked_without_payable(db):
    co = _company(db)
    vendor = _vendor(db, co)
    _payable(db, co, vendor)
    err = erp._at_supplier_payment_submit_error(
        db, [vendor], vendor.name, None
    )
    assert err == erp._t("txn.payable_none_selected")


def test_supplier_payment_submit_blocked_without_vendor(db):
    co = _company(db)
    vendor = _vendor(db, co)
    err = erp._at_supplier_payment_submit_error(db, [vendor], None, None)
    assert err == erp._t("txn.vendor_required")


def test_supplier_payment_no_open_payable_message(db):
    co = _company(db)
    vendor = _vendor(db, co)
    err = erp._at_supplier_payment_submit_error(
        db, [vendor], vendor.name, None
    )
    assert err == erp._t("txn.no_open_payable")


def test_sale_from_invoice_choice_after_selection():
    sale = models.Sale(
        invoice_number="INV-9",
        customer_name="Alice",
        balance=123.45,
        sale_type="Credit",
    )
    label = erp._at_invoice_choice_label(sale)
    found = erp._at_sale_from_invoice_choice([sale], label)
    assert found is sale
    assert found.balance == 123.45


def test_vendor_quick_add_still_selects_new_supplier(monkeypatch):
    state = _FakeSessionState({"at_payable_id": 99})
    monkeypatch.setattr(erp.st, "session_state", state)
    v = models.Vendor(id=5, name="Fresh Farm", is_active=True)
    erp._vendor_select_in_at(v)
    assert state["at_vendor"] == "Fresh Farm"
    assert "at_payable_id" not in state


def test_placeholder_i18n_keys_exist():
    assert "Select payable" in erp._t("txn.select_payable_ph")
    assert "Select invoice" in erp._t("txn.select_invoice_ph")
    assert erp._at_supplier_placeholder() == erp._t("txn.select_supplier_ph")
    assert "Select supplier" in erp._at_supplier_placeholder()


def test_normalize_vendor_rejects_raw_i18n_key():
    names = ["Acme Supplies"]
    assert erp._at_normalize_vendor_selection("txn.select_supplier_ph", names) is None


def test_normalize_vendor_rejects_translated_placeholder():
    names = ["Acme Supplies"]
    ph = erp._at_supplier_placeholder()
    assert erp._at_normalize_vendor_selection(ph, names) is None


def test_clear_invalid_at_vendor_drops_raw_key(monkeypatch):
    state = _FakeSessionState({"at_vendor": "txn.select_supplier_ph"})
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._at_clear_invalid_at_vendor(["Acme Supplies"])
    assert "at_vendor" not in state
