"""Purchase edit/void — linked payable lifecycle when purchase_type changes."""

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
import app as erp_app
from registry.service import set_setting


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    erp_app.st.session_state = {}
    with Session() as session:
        yield session


def _seed_coa(db, co):
    for code, name, atype in (
        ("1010", "Cash", "Asset"),
        ("1020", "Bank", "Asset"),
        ("1200", "Inventory", "Asset"),
        ("2000", "Accounts Payable", "Liability"),
        ("2110", "Credit Card Payable", "Liability"),
    ):
        db.add(
            models.ChartOfAccounts(
                account_code=code,
                account_name=name,
                account_type=atype,
                company_id=co.id,
            )
        )
    db.commit()


def _company(db):
    co = models.Company(
        name="Acme",
        slug="acme",
        is_active=True,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    db.add(co)
    db.commit()
    erp_app.st.session_state["active_company_id"] = co.id
    _seed_coa(db, co)
    set_setting(db, "banking.company_card_enabled", True, company_id=co.id)
    _cc_card(db, co)
    db.commit()
    return co


def _vendor(db, co, name="Supplier"):
    v = models.Vendor(name=name, company_id=co.id, is_active=True)
    db.add(v)
    db.commit()
    return v


def _cc_card(db, co):
    ba = models.BankAccount(
        name="Company Visa",
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=0.0,
        kind="credit_card",
    )
    db.add(ba)
    db.commit()
    return ba


def _linked_payable(db, purchase_id):
    return (
        db.query(models.Payable)
        .filter_by(purchase_id=purchase_id)
        .order_by(models.Payable.id)
        .first()
    )


def _open_payables(db):
    return (
        db.query(models.Payable)
        .filter_by(is_void=False, paid=False)
        .all()
    )


def _open_ap_outstanding(db):
    return sum(
        (p.amount or 0) - (p.paid_amount or 0) for p in _open_payables(db)
    )


def _create_purchase(
    db,
    co,
    vendor,
    *,
    amount=100.0,
    purchase_type="Credit",
    with_payable=None,
):
    """Create purchase, post GL, optionally attach payable (Credit default)."""
    if with_payable is None:
        with_payable = purchase_type == "Credit"
    pur = models.Purchase(
        date=datetime.date.today(),
        vendor_id=vendor.id,
        amount=amount,
        description="Test purchase",
        purchase_type=purchase_type,
        gl_debit="Inventory",
        company_id=co.id,
    )
    db.add(pur)
    db.commit()
    erp_app.post_purchase(
        db, pur.id, amount, pur.date, purchase_type, "Inventory"
    )
    if with_payable:
        db.add(
            models.Payable(
                date=pur.date,
                vendor_id=vendor.id,
                amount=amount,
                due_date=pur.date + datetime.timedelta(days=30),
                paid=False,
                paid_amount=0.0,
                description=f"From Purchase #{pur.id}: Test purchase",
                expense_category="Inventory",
                purchase_id=pur.id,
                company_id=co.id,
            )
        )
        db.commit()
    return pur


class TestCreditPurchasePayableSync:
    def test_edit_amount_keeps_payable_current(self, db):
        co = _company(db)
        vendor = _vendor(db, co)
        pur = _create_purchase(db, co, vendor, amount=100.0, purchase_type="Credit")

        ok, err = erp_app.edit_purchase(db, pur.id, {"amount": 175.0})
        assert ok is True
        assert err is None

        pay = _linked_payable(db, pur.id)
        assert pay is not None
        assert pay.is_void is False
        assert pay.amount == 175.0
        assert _open_ap_outstanding(db) == 175.0

    def test_edit_vendor_updates_payable(self, db):
        co = _company(db)
        vendor_a = _vendor(db, co, "Supplier A")
        vendor_b = _vendor(db, co, "Supplier B")
        pur = _create_purchase(db, co, vendor_a, purchase_type="Credit")

        ok, _ = erp_app.edit_purchase(db, pur.id, {"vendor_id": vendor_b.id})
        assert ok is True
        pay = _linked_payable(db, pur.id)
        assert pay.vendor_id == vendor_b.id


class TestCreditToNonCreditClosesPayable:
    @pytest.mark.parametrize("new_type", ["Cash", "Bank", "Credit Card"])
    def test_credit_edit_to_immediate_payment_voids_payable(self, db, new_type):
        co = _company(db)
        vendor = _vendor(db, co)
        pur = _create_purchase(db, co, vendor, amount=100.0, purchase_type="Credit")
        assert _open_ap_outstanding(db) == 100.0

        ok, err = erp_app.edit_purchase(db, pur.id, {"purchase_type": new_type})
        assert ok is True
        assert err is None

        pay = _linked_payable(db, pur.id)
        assert pay.is_void is True
        assert _open_ap_outstanding(db) == 0.0


class TestNonCreditToCreditCreatesPayable:
    @pytest.mark.parametrize("orig_type", ["Cash", "Bank", "Credit Card"])
    def test_immediate_payment_edit_to_credit_creates_payable(self, db, orig_type):
        co = _company(db)
        vendor = _vendor(db, co)
        pur = _create_purchase(
            db, co, vendor, amount=120.0, purchase_type=orig_type, with_payable=False
        )
        assert _linked_payable(db, pur.id) is None

        ok, err = erp_app.edit_purchase(db, pur.id, {"purchase_type": "Credit"})
        assert ok is True
        assert err is None

        pay = _linked_payable(db, pur.id)
        assert pay is not None
        assert pay.is_void is False
        assert pay.amount == 120.0
        assert pay.purchase_id == pur.id
        assert _open_ap_outstanding(db) == 120.0


class TestVoidPurchasePayable:
    def test_void_credit_purchase_closes_linked_payable(self, db):
        co = _company(db)
        vendor = _vendor(db, co)
        pur = _create_purchase(db, co, vendor, purchase_type="Credit")
        assert _open_ap_outstanding(db) == 100.0

        assert erp_app.void_purchase(db, pur.id, "test void") is True

        pay = _linked_payable(db, pur.id)
        assert pay.is_void is True
        assert _open_ap_outstanding(db) == 0.0

    def test_void_non_credit_purchase_has_no_payable_side_effects(self, db):
        co = _company(db)
        vendor = _vendor(db, co)
        pur = _create_purchase(
            db, co, vendor, purchase_type="Cash", with_payable=False
        )

        assert erp_app.void_purchase(db, pur.id, "test void") is True
        assert _linked_payable(db, pur.id) is None
        assert _open_payables(db) == []

    def test_paid_linked_payable_blocks_tier2_edit(self, db):
        co = _company(db)
        vendor = _vendor(db, co)
        pur = _create_purchase(db, co, vendor, purchase_type="Credit")
        pay = _linked_payable(db, pur.id)
        pay.paid = True
        pay.paid_amount = pay.amount
        db.commit()

        ok, err = erp_app.edit_purchase(db, pur.id, {"amount": 50.0})
        assert ok is False
        assert "already paid" in (err or "").lower()
