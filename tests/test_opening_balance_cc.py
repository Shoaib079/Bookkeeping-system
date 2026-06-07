"""Opening balance — bank vs company credit card (OBBank)."""

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
from reconciliation.company_card import compute_cc_payable_recon_health


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
        ("1010", "Bank", "Asset"),
        ("1011", "Cash", "Asset"),
        ("1150", "Card Sales Clearing", "Asset"),
        ("2110", "Credit Card Payable", "Liability"),
        ("3900", "Opening Balance Equity", "Equity"),
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


def _company(db, *, cc_on=True):
    from registry.service import set_setting

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
    if cc_on:
        set_setting(db, "banking.company_card_enabled", True, company_id=co.id)
    db.commit()
    return co


def _obe(db, co):
    return (
        db.query(models.ChartOfAccounts)
        .filter_by(account_name="Opening Balance Equity", company_id=co.id)
        .one()
    )


def _bank_acct(db, co, *, name="Main TRY", kind="bank"):
    ba = models.BankAccount(
        name=name,
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=0.0,
        kind=kind,
    )
    db.add(ba)
    db.commit()
    return ba


class TestBankOpeningBalance:
    def test_bank_posts_dr_bank_cr_obe(self, db):
        co = _company(db, cc_on=False)
        ba = _bank_acct(db, co, kind="bank")
        obe = _obe(db, co)
        erp_app._post_opening_balance_bank_account(
            db, ba, datetime.date.today(), 5000.0, obe
        )
        db.commit()
        db.refresh(ba)
        je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="OBBank", reference_id=ba.id)
            .one()
        )
        lines = (
            db.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .all()
        )
        bank_gl = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Bank", company_id=co.id)
            .one()
        )
        assert ba.balance == 5000.0
        assert sum(l.debit for l in lines if l.account_id == bank_gl.id) == 5000.0
        assert sum(l.credit for l in lines if l.account_id == obe.id) == 5000.0
        txn = (
            db.query(models.BankTransaction)
            .filter_by(account_id=ba.id, description="Opening Balance")
            .one()
        )
        assert txn.type == "deposit"

    def test_duplicate_opening_balance_blocked(self, db):
        co = _company(db, cc_on=False)
        ba = _bank_acct(db, co, kind="bank")
        obe = _obe(db, co)
        erp_app._post_opening_balance_bank_account(
            db, ba, datetime.date.today(), 100.0, obe
        )
        db.commit()
        with pytest.raises(ValueError, match="already posted"):
            erp_app._post_opening_balance_bank_account(
                db, ba, datetime.date.today(), 200.0, obe
            )


class TestCreditCardOpeningBalance:
    def test_cc_posts_dr_obe_cr_2110(self, db):
        co = _company(db, cc_on=True)
        card = _bank_acct(db, co, name="Company Visa", kind="credit_card")
        obe = _obe(db, co)
        erp_app._post_opening_balance_bank_account(
            db, card, datetime.date.today(), 750.0, obe
        )
        db.commit()
        db.refresh(card)
        je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="OBBank", reference_id=card.id)
            .one()
        )
        lines = (
            db.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .all()
        )
        cc_gl = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Credit Card Payable", company_id=co.id)
            .one()
        )
        assert card.balance == 750.0
        assert sum(l.debit for l in lines if l.account_id == obe.id) == 750.0
        assert sum(l.credit for l in lines if l.account_id == cc_gl.id) == 750.0
        txn = (
            db.query(models.BankTransaction)
            .filter_by(account_id=card.id, description="Opening Balance")
            .one()
        )
        assert txn.type == "withdrawal"

    def test_recon_health_clean_after_cc_opening(self, db):
        co = _company(db, cc_on=True)
        card = _bank_acct(db, co, name="Visa", kind="credit_card")
        obe = _obe(db, co)
        erp_app._post_opening_balance_bank_account(
            db, card, datetime.date.today(), 1200.0, obe
        )
        db.commit()
        health = compute_cc_payable_recon_health(db, co.id)
        assert health["difference"] == 0.0
        assert health["gl_balance"] == 1200.0
        assert health["subledger_total"] == 1200.0

    def test_cc_blocked_when_feature_disabled(self, db):
        co = _company(db, cc_on=False)
        card = _bank_acct(db, co, name="Visa", kind="credit_card")
        obe = _obe(db, co)
        with pytest.raises(ValueError, match="disabled"):
            erp_app._post_opening_balance_bank_account(
                db, card, datetime.date.today(), 100.0, obe
            )


class TestCardSaleUnaffected:
    def test_card_sale_does_not_use_cc_payable_2110(self, db):
        co = _company(db, cc_on=True)
        _bank_acct(db, co, name="POS Bank", kind="bank")
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="INV-001",
            customer_name="Walk-in",
            amount=99.0,
            sale_type="Card",
            status="Paid",
            company_id=co.id,
        )
        db.add(sale)
        db.flush()
        erp_app.post_card_sale(db, sale.id, 99.0, datetime.date.today())
        db.commit()
        je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="CardSale")
            .one()
        )
        assert je is not None
        cc_gl = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Credit Card Payable", company_id=co.id)
            .one()
        )
        lines = (
            db.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .all()
        )
        assert sum(l.credit for l in lines if l.account_id == cc_gl.id) == 0.0
