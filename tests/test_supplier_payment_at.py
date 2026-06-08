"""SP1/SP2 — Add Transaction Supplier Payment partial/full/overpay logic."""

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


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    erp.st.session_state = {}
    with Session() as session:
        yield session


def _seed_coa(db, co):
    for code, name, atype in (
        ("1010", "Cash", "Asset"),
        ("1020", "Bank", "Asset"),
        ("1200", "Accounts Receivable", "Asset"),
        ("2000", "Accounts Payable", "Liability"),
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
    erp.st.session_state["active_company_id"] = co.id
    _seed_coa(db, co)
    return co


def _vendor(db, co, name="Supplier"):
    v = models.Vendor(name=name, company_id=co.id, is_active=True)
    db.add(v)
    db.commit()
    return v


def _open_payable(db, co, vendor, amount=100.0, paid_amount=0.0):
    payable = models.Payable(
        date=datetime.date.today(),
        vendor_id=vendor.id,
        amount=amount,
        paid_amount=paid_amount,
        balance=max(round(amount - paid_amount, 2), 0.0),
        due_date=datetime.date.today(),
        paid=False,
        company_id=co.id,
    )
    db.add(payable)
    db.commit()
    return payable


def _credit_sale(db, co, amount=100.0, paid_amount=0.0):
    sale = models.Sale(
        date=datetime.date.today(),
        invoice_number="INV-001",
        customer_name="Customer",
        amount=amount,
        sale_type="Credit",
        paid_amount=paid_amount,
        balance=max(round(amount - paid_amount, 2), 0.0),
        due_date=datetime.date.today(),
        status="Open",
        company_id=co.id,
    )
    db.add(sale)
    db.commit()
    return sale


def test_supplier_payment_equal_balance_marks_paid(db):
    co = _company(db)
    vendor = _vendor(db, co)
    payable = _open_payable(db, co, vendor, amount=100.0)

    assert erp._validate_payable_payment_amount(payable, 100.0, currency="TRY") is None
    erp._apply_payable_payment_state(payable, 100.0)
    db.commit()

    assert payable.paid_amount == 100.0
    assert payable.paid is True
    assert erp._payable_balance(payable) == 0.0


def test_supplier_payment_partial_does_not_mark_paid(db):
    co = _company(db)
    vendor = _vendor(db, co)
    payable = _open_payable(db, co, vendor, amount=100.0)

    assert erp._validate_payable_payment_amount(payable, 40.0, currency="TRY") is None
    erp._apply_payable_payment_state(payable, 40.0)
    db.commit()

    assert payable.paid_amount == 40.0
    assert payable.paid is False
    assert erp._payable_balance(payable) == 60.0


def test_supplier_payment_partial_updates_paid_amount(db):
    co = _company(db)
    vendor = _vendor(db, co)
    payable = _open_payable(db, co, vendor, amount=250.0, paid_amount=50.0)

    erp._apply_payable_payment_state(payable, 75.0)
    db.commit()

    assert payable.paid_amount == 125.0
    assert payable.paid is False
    assert erp._payable_balance(payable) == 125.0


def test_supplier_payment_overpay_blocked(db):
    co = _company(db)
    vendor = _vendor(db, co)
    payable = _open_payable(db, co, vendor, amount=100.0)

    expected = erp._t("txn.payable_overpay_no_advance")
    err = erp._validate_payable_payment_amount(payable, 150.0, currency="TRY")
    assert err == expected
    assert "Supplier advances/prepayments are not supported yet" in err

    assert payable.paid_amount == 0.0
    assert payable.paid is False


def test_supplier_payment_overpay_creates_no_journal_entry(db):
    co = _company(db)
    vendor = _vendor(db, co)
    payable = _open_payable(db, co, vendor, amount=100.0)

    assert erp._validate_payable_payment_amount(payable, 150.0, currency="TRY") is not None

    je_before = db.query(models.JournalEntry).count()
    db.refresh(payable)
    assert payable.paid_amount == 0.0
    assert db.query(models.JournalEntry).count() == je_before


def test_supplier_payment_full_posts_journal_entry(db):
    co = _company(db)
    vendor = _vendor(db, co)
    payable = _open_payable(db, co, vendor, amount=80.0)

    erp._apply_payable_payment_state(payable, 80.0)
    db.commit()
    erp.post_payable_payment(
        db, payable.id, 80.0, payable.date, payment_method="Cash", currency="TRY"
    )
    db.commit()

    je = (
        db.query(models.JournalEntry)
        .filter_by(reference_type="PayablePayment", reference_id=payable.id)
        .one()
    )
    assert je is not None
    assert payable.paid is True


def test_customer_payment_overpay_still_blocked(db):
    co = _company(db)
    sale = _credit_sale(db, co, amount=100.0)

    err = erp.post_receivable_payment(
        db, sale.id, 150.0, datetime.date.today(), payment_method="Cash", currency="TRY"
    )
    assert err == "Payment amount exceeds the remaining balance."
    db.refresh(sale)
    assert sale.paid_amount == 0.0
    assert sale.balance == 100.0


def test_customer_payment_valid_amount_unchanged(db):
    co = _company(db)
    sale = _credit_sale(db, co, amount=100.0)

    err = erp.post_receivable_payment(
        db, sale.id, 40.0, datetime.date.today(), payment_method="Cash", currency="TRY"
    )
    assert err is None
    db.refresh(sale)
    assert sale.paid_amount == 40.0
    assert sale.balance == 60.0
