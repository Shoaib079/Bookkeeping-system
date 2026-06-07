"""CardPurchase void/edit — correct GL reference_type reversal and repost."""

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
        ("4000", "Sales Revenue", "Income"),
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


def _vendor(db, co):
    v = models.Vendor(name="Supplier", company_id=co.id, is_active=True)
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


def _acct(db, co, name):
    return (
        db.query(models.ChartOfAccounts)
        .filter_by(account_name=name, company_id=co.id)
        .one()
    )


def _bal(db, account):
    return erp_app.calculate_account_balance(db, account)


_PURCHASE_POSTING_TYPES = ("CardPurchase", "CashPurchase", "BankPurchase", "Purchase")


def _purchase_posting_types(db, purchase_id):
    """Posting JEs for a purchase (excludes Reversal entries keyed by journal id)."""
    return [
        je.reference_type
        for je in db.query(models.JournalEntry)
        .filter(
            models.JournalEntry.reference_id == purchase_id,
            models.JournalEntry.reference_type.in_(_PURCHASE_POSTING_TYPES),
        )
        .order_by(models.JournalEntry.id)
        .all()
    ]


def _create_purchase(db, co, vendor, *, amount=100.0, purchase_type="Credit Card"):
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
    db.commit()
    return pur


class TestCardPurchaseVoid:
    def test_void_reverses_card_purchase_gl_to_net_zero(self, db):
        co = _company(db)
        vendor = _vendor(db, co)
        inv = _acct(db, co, "Inventory")
        cc = _acct(db, co, "Credit Card Payable")
        inv0, cc0 = _bal(db, inv), _bal(db, cc)

        pur = _create_purchase(db, co, vendor, amount=100.0, purchase_type="Credit Card")
        assert _purchase_posting_types(db, pur.id) == ["CardPurchase"]
        assert _bal(db, inv) == inv0 + 100.0
        assert _bal(db, cc) == cc0 + 100.0

        assert erp_app.void_purchase(db, pur.id, "test void") is True
        db.refresh(pur)
        assert pur.is_void is True
        assert _bal(db, inv) == inv0
        assert _bal(db, cc) == cc0

    def test_cash_purchase_void_unchanged(self, db):
        co = _company(db)
        vendor = _vendor(db, co)
        cash = _acct(db, co, "Cash")
        inv = _acct(db, co, "Inventory")
        cash0, inv0 = _bal(db, cash), _bal(db, inv)

        pur = _create_purchase(db, co, vendor, amount=80.0, purchase_type="Cash")
        assert _purchase_posting_types(db, pur.id) == ["CashPurchase"]
        erp_app.void_purchase(db, pur.id, "test void")
        assert _bal(db, cash) == cash0
        assert _bal(db, inv) == inv0


class TestCardPurchaseEdit:
    def test_edit_amount_reverses_and_reposts_card_purchase(self, db):
        co = _company(db)
        vendor = _vendor(db, co)
        inv = _acct(db, co, "Inventory")
        cc = _acct(db, co, "Credit Card Payable")
        inv0, cc0 = _bal(db, inv), _bal(db, cc)

        pur = _create_purchase(db, co, vendor, amount=100.0, purchase_type="Credit Card")
        ok, err = erp_app.edit_purchase(db, pur.id, {"amount": 150.0})
        assert ok is True
        assert err is None
        db.refresh(pur)
        assert pur.amount == 150.0
        assert _purchase_posting_types(db, pur.id) == ["CardPurchase", "CardPurchase"]
        assert _bal(db, inv) == inv0 + 150.0
        assert _bal(db, cc) == cc0 + 150.0

    def test_edit_credit_card_to_cash(self, db):
        co = _company(db)
        vendor = _vendor(db, co)
        inv = _acct(db, co, "Inventory")
        cash = _acct(db, co, "Cash")
        cc = _acct(db, co, "Credit Card Payable")
        inv0, cash0, cc0 = _bal(db, inv), _bal(db, cash), _bal(db, cc)

        pur = _create_purchase(db, co, vendor, amount=100.0, purchase_type="Credit Card")
        ok, _ = erp_app.edit_purchase(db, pur.id, {"purchase_type": "Cash"})
        assert ok is True
        db.refresh(pur)
        assert pur.purchase_type == "Cash"
        assert _purchase_posting_types(db, pur.id) == ["CardPurchase", "CashPurchase"]
        assert _bal(db, inv) == inv0 + 100.0
        assert _bal(db, cash) == cash0 - 100.0
        assert _bal(db, cc) == cc0

    def test_edit_cash_to_credit_card(self, db):
        co = _company(db)
        vendor = _vendor(db, co)
        inv = _acct(db, co, "Inventory")
        cash = _acct(db, co, "Cash")
        cc = _acct(db, co, "Credit Card Payable")
        inv0, cash0, cc0 = _bal(db, inv), _bal(db, cash), _bal(db, cc)

        pur = _create_purchase(db, co, vendor, amount=100.0, purchase_type="Cash")
        ok, _ = erp_app.edit_purchase(db, pur.id, {"purchase_type": "Credit Card"})
        assert ok is True
        db.refresh(pur)
        assert pur.purchase_type == "Credit Card"
        assert _purchase_posting_types(db, pur.id) == ["CashPurchase", "CardPurchase"]
        assert _bal(db, inv) == inv0 + 100.0
        assert _bal(db, cash) == cash0
        assert _bal(db, cc) == cc0 + 100.0

    def test_edit_credit_to_credit_card(self, db):
        co = _company(db)
        vendor = _vendor(db, co)
        inv = _acct(db, co, "Inventory")
        ap = _acct(db, co, "Accounts Payable")
        cc = _acct(db, co, "Credit Card Payable")
        inv0, ap0, cc0 = _bal(db, inv), _bal(db, ap), _bal(db, cc)

        pur = _create_purchase(db, co, vendor, amount=100.0, purchase_type="Credit")
        ok, _ = erp_app.edit_purchase(db, pur.id, {"purchase_type": "Credit Card"})
        assert ok is True
        assert _purchase_posting_types(db, pur.id) == ["Purchase", "CardPurchase"]
        assert _bal(db, inv) == inv0 + 100.0
        assert _bal(db, ap) == ap0
        assert _bal(db, cc) == cc0 + 100.0

    def test_edit_bank_to_credit_card(self, db):
        co = _company(db)
        vendor = _vendor(db, co)
        inv = _acct(db, co, "Inventory")
        bank = _acct(db, co, "Bank")
        cc = _acct(db, co, "Credit Card Payable")
        inv0, bank0, cc0 = _bal(db, inv), _bal(db, bank), _bal(db, cc)

        pur = _create_purchase(db, co, vendor, amount=75.0, purchase_type="Bank")
        ok, _ = erp_app.edit_purchase(db, pur.id, {"purchase_type": "Credit Card"})
        assert ok is True
        assert _purchase_posting_types(db, pur.id) == ["BankPurchase", "CardPurchase"]
        assert _bal(db, inv) == inv0 + 75.0
        assert _bal(db, bank) == bank0
        assert _bal(db, cc) == cc0 + 75.0


class TestCardSaleUnaffected:
    def test_customer_card_sale_uses_card_sale_not_card_purchase(self, db):
        co = _company(db)
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="INV-TEST",
            customer_name="Walk-in",
            description="Card sale",
            amount=50.0,
            sale_type="Card",
            paid_amount=50.0,
            balance=0.0,
            status="Paid",
            company_id=co.id,
        )
        db.add(sale)
        db.commit()
        erp_app.post_card_sale(db, sale.id, 50.0, sale.date)
        db.commit()

        je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="CardSale", reference_id=sale.id)
            .one()
        )
        assert je.reference_type == "CardSale"
        assert (
            db.query(models.JournalEntry)
            .filter_by(reference_type="CardPurchase", reference_id=sale.id)
            .count()
        ) == 0

        assert erp_app.void_sale(db, sale.id, "test") is True
        rev_count = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="Reversal")
            .count()
        )
        assert rev_count >= 1
