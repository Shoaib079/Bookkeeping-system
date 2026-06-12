"""WO-A1 — supplier quick-add helpers (no Streamlit dialog runtime)."""

from __future__ import annotations

import datetime
import inspect
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


def test_vendor_create_new(db):
    co = _company(db)
    vendor, err = erp._vendor_create_or_reactivate(
        db, name="Ahmad Chicken", phone="555-0100", contact="Ahmad"
    )
    assert err is None
    assert vendor is not None
    assert vendor.name == "Ahmad Chicken"
    assert vendor.company_id == co.id
    assert vendor.is_active is True
    assert vendor.phone == "555-0100"


def test_vendor_duplicate_active_rejected(db):
    _company(db)
    erp._vendor_create_or_reactivate(db, name="Dup Co")
    vendor, err = erp._vendor_create_or_reactivate(db, name="dup co")
    assert vendor is None
    assert err is not None
    assert "dup co" in err.lower() or "Dup" in err


def test_vendor_reactivate_inactive(db):
    co = _company(db)
    inactive = models.Vendor(
        name="Old Supplier",
        company_id=co.id,
        is_active=False,
        notes="legacy",
    )
    db.add(inactive)
    db.commit()
    vendor, err = erp._vendor_create_or_reactivate(
        db, name="old supplier", phone="999", notes="updated"
    )
    assert err is None
    assert vendor.id == inactive.id
    assert vendor.is_active is True
    assert vendor.phone == "999"
    assert vendor.notes == "updated"
    assert db.query(models.Vendor).count() == 1


def test_vendor_select_in_at(monkeypatch):
    state = _FakeSessionState({"at_payable_id": 42, "at_last_vendor": "X"})
    monkeypatch.setattr(erp.st, "session_state", state)
    v = models.Vendor(id=7, name="Fresh Farm", is_active=True)
    erp._vendor_select_in_at(v)
    assert state["at_vendor"] == "Fresh Farm"
    assert state["mob_at_vendor_sel"] == "Fresh Farm"
    assert "at_payable_id" not in state


def test_vendor_rename_excludes_self(db):
    _company(db)
    v1, _ = erp._vendor_create_or_reactivate(db, name="Alpha")
    v2, _ = erp._vendor_create_or_reactivate(db, name="Beta")
    assert erp._vendor_validate_name(db, "alpha", exclude_id=v1.id) is None
    assert erp._vendor_validate_name(db, "beta", exclude_id=v1.id) is not None
    v1.name = "Alpha Renamed"
    db.commit()
    assert v2.name == "Beta"


def test_vendor_linked_counts(db):
    co = _company(db)
    vendor, _ = erp._vendor_create_or_reactivate(db, name="Linked Co")
    db.add(
        models.Purchase(
            date=datetime.date.today(),
            vendor_id=vendor.id,
            amount=100.0,
            company_id=co.id,
        )
    )
    db.add(
        models.Payable(
            date=datetime.date.today(),
            vendor_id=vendor.id,
            amount=50.0,
            due_date=datetime.date.today(),
            company_id=co.id,
        )
    )
    db.commit()
    pur, pay = erp._vendor_linked_counts(db, vendor.id)
    assert pur == 1
    assert pay == 1


def test_inline_vendor_row_wired_in_at_purchase_and_supplier_payment():
    src = inspect.getsource(erp.render_add_transaction)
    assert "_inline_vendor_row(" in src
    assert "inside_form=True" in src
    assert src.count("_inline_vendor_row(") >= 2
    assert 'elif txn_type == "Purchase"' in src


def test_vendor_dialogs_and_buttons_present():
    src = inspect.getsource(erp)
    assert "def _vendor_add_dialog" in src
    assert "def _vendor_manage_dialog" in src
    assert 'key="vendor_add_btn"' in src
    assert 'key="vendor_cog_btn"' in src


def test_mob_supplier_payment_vendor_trigger_accepts_session():
    src = inspect.getsource(erp._mob_at_render_vendor_trigger)
    assert "session" in inspect.signature(erp._mob_at_render_vendor_trigger).parameters
    assert '_mob_at_render_vendor_trigger(session, vendors)' in inspect.getsource(erp)


def test_vendor_create_empty_name_rejected(db):
    _company(db)
    vendor, err = erp._vendor_create_or_reactivate(db, name="   ")
    assert vendor is None
    assert err is not None
