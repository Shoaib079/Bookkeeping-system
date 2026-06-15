"""AD-014 — Void/unpost BankStmtCCBillPay."""

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
from utc_datetime import utc_now_naive
import models
import app as erp_app
from reconciliation.company_card import (
    post_credit_card_bill_payment,
    void_credit_card_bill_payment,
)
from reconciliation.match_post import MatchPostError
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
        ("1010", "Bank", "Asset"),
        ("2110", "Credit Card Payable", "Liability"),
        ("3900", "Opening Balance Equity", "Equity"),
    ):
        db.add(
            models.ChartOfAccounts(
                account_code=code,
                account_name=name,
                account_type=atype,
                currency="TRY" if name == "Bank" else None,
                company_id=co.id,
            )
        )
    db.commit()


def _company(db):
    co = models.Company(
        name="Acme",
        slug="acme",
        is_active=True,
        created_at=utc_now_naive(),
    )
    db.add(co)
    db.commit()
    erp_app.st.session_state["active_company_id"] = co.id
    _seed_coa(db, co)
    set_setting(db, "banking.company_card_enabled", True, company_id=co.id)
    set_setting(db, "banking.reconciliation_enabled", True, company_id=co.id)
    return co


def _bank(db, co, *, kind="bank", name="Main TRY", balance=10000.0):
    ba = models.BankAccount(
        name=name,
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=balance,
        kind=kind,
    )
    db.add(ba)
    db.commit()
    return ba


def _stmt_row(db, co, ba, *, amount=300.0, desc="KK ODEME"):
    imp = models.BankStatementImport(
        company_id=co.id,
        bank_account_id=ba.id,
        file_name="t.csv",
        file_hash="void1",
        file_size=10,
        file_path="/tmp/t.csv",
        status="staging",
        import_date=datetime.date.today(),
        row_count=1,
        valid_count=1,
        flagged_count=0,
        error_count=0,
        currency="TRY",
        created_at=utc_now_naive(),
    )
    db.add(imp)
    db.flush()
    row = models.BankStatementRow(
        bank_statement_import_id=imp.id,
        status="staging",
        import_row_index=1,
        date=datetime.date.today(),
        description=desc,
        debit_amount=amount,
        credit_amount=None,
        amount=amount,
        currency="TRY",
        original_amount=amount,
        parsed_successfully=True,
        created_at=utc_now_naive(),
    )
    db.add(row)
    db.commit()
    return row


def _post_bill(db, co, bank, card, row, amount=None):
    if amount is not None:
        row.debit_amount = amount
        row.amount = amount
        row.original_amount = amount
        db.commit()
    return post_credit_card_bill_payment(
        db,
        row_id=row.id,
        company_id=co.id,
        credit_card_account_id=card.id,
        user_id=None,
    )


class TestVoidCreditCardBillPayment:
    def test_void_restores_gl_bank_and_card_balances(self, db):
        co = _company(db)
        bank = _bank(db, co, kind="bank", balance=10000.0)
        card = _bank(db, co, kind="credit_card", name="Visa", balance=800.0)
        row = _stmt_row(db, co, bank, amount=250.0)
        cc_gl = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Credit Card Payable", company_id=co.id)
            .one()
        )
        bank_gl = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Bank", company_id=co.id)
            .one()
        )
        cc_before = erp_app.calculate_account_balance(db, cc_gl)
        bank_before = erp_app.calculate_account_balance(db, bank_gl)
        bank_before_bal = bank.balance
        card_before_bal = card.balance

        _post_bill(db, co, bank, card, row)
        db.refresh(bank)
        db.refresh(card)
        assert bank.balance == bank_before_bal - 250.0
        assert card.balance == card_before_bal - 250.0

        void_credit_card_bill_payment(db, row.id, co.id, "Correction")
        db.refresh(row)
        db.refresh(bank)
        db.refresh(card)

        assert row.status == "voided"
        assert bank.balance == bank_before_bal
        assert card.balance == card_before_bal
        assert erp_app.calculate_account_balance(db, cc_gl) == cc_before
        assert erp_app.calculate_account_balance(db, bank_gl) == bank_before

    def test_reversal_je_exists(self, db):
        co = _company(db)
        bank = _bank(db, co)
        card = _bank(db, co, kind="credit_card", name="Visa", balance=500.0)
        row = _stmt_row(db, co, bank, amount=200.0)
        _post_bill(db, co, bank, card, row)

        orig_je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="BankStmtCCBillPay", reference_id=row.id)
            .one()
        )
        void_credit_card_bill_payment(db, row.id, co.id, "Test reversal")

        reversal = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="Reversal", reference_id=orig_je.id)
            .one()
        )
        assert "VOID" in reversal.description

    def test_both_bank_transactions_voided(self, db):
        co = _company(db)
        bank = _bank(db, co)
        card = _bank(db, co, kind="credit_card", name="Visa", balance=500.0)
        row = _stmt_row(db, co, bank, amount=150.0)
        result = _post_bill(db, co, bank, card, row)

        void_credit_card_bill_payment(db, row.id, co.id, "Undo")

        bank_txn = db.get(models.BankTransaction, result["bank_transaction_id"])
        cc_txn = db.get(models.BankTransaction, result["credit_card_transaction_id"])
        assert bank_txn.is_void
        assert cc_txn.is_void

    def test_cannot_void_twice(self, db):
        co = _company(db)
        bank = _bank(db, co)
        card = _bank(db, co, kind="credit_card", name="Visa", balance=500.0)
        row = _stmt_row(db, co, bank, amount=100.0)
        _post_bill(db, co, bank, card, row)
        void_credit_card_bill_payment(db, row.id, co.id, "Once")

        with pytest.raises(MatchPostError, match="already voided"):
            void_credit_card_bill_payment(db, row.id, co.id, "Twice")

    def test_wrong_match_type_raises(self, db):
        co = _company(db)
        bank = _bank(db, co)
        row = _stmt_row(db, co, bank, amount=100.0)
        row.status = "posted"
        row.match_type = "vendor_payment"
        db.commit()

        with pytest.raises(MatchPostError, match="credit card bill payment"):
            void_credit_card_bill_payment(db, row.id, co.id, "Nope")

    def test_direct_void_bank_transaction_blocked(self, db):
        co = _company(db)
        bank = _bank(db, co)
        card = _bank(db, co, kind="credit_card", name="Visa", balance=500.0)
        row = _stmt_row(db, co, bank, amount=120.0)
        result = _post_bill(db, co, bank, card, row)

        with pytest.raises(ValueError, match="Bank Reconciliation"):
            erp_app.void_bank_transaction(
                db, result["bank_transaction_id"], "Direct void"
            )

    def test_wrong_card_void_restores_selected_card(self, db):
        co = _company(db)
        bank = _bank(db, co)
        visa = _bank(db, co, kind="credit_card", name="Visa", balance=600.0)
        amex = _bank(db, co, kind="credit_card", name="Amex", balance=400.0)
        row = _stmt_row(db, co, bank, amount=200.0)
        _post_bill(db, co, bank, card=amex, row=row)

        assert amex.balance == 200.0
        assert visa.balance == 600.0

        void_credit_card_bill_payment(db, row.id, co.id, "Wrong card test")

        db.refresh(amex)
        db.refresh(visa)
        assert amex.balance == 400.0
        assert visa.balance == 600.0

    def test_partial_bill_payment_void(self, db):
        co = _company(db)
        bank = _bank(db, co, balance=5000.0)
        card = _bank(db, co, kind="credit_card", name="Visa", balance=1000.0)
        row = _stmt_row(db, co, bank, amount=175.0)
        _post_bill(db, co, bank, card, row, amount=175.0)

        assert bank.balance == 4825.0
        assert card.balance == 825.0

        void_credit_card_bill_payment(db, row.id, co.id, "Partial undo")

        db.refresh(bank)
        db.refresh(card)
        assert bank.balance == 5000.0
        assert card.balance == 1000.0
