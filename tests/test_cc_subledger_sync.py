"""AD-011 — Company credit card sub-ledger sync with GL 2110."""

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
    cc_subledger_stmt_ref,
    post_credit_card_bill_payment,
)
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
        ("1150", "Card Sales Clearing", "Asset"),
        ("2000", "Accounts Payable", "Liability"),
        ("2110", "Credit Card Payable", "Liability"),
        ("4000", "Sales Revenue", "Income"),
        ("5100", "Office Expense", "Expense"),
        ("1200", "Inventory", "Asset"),
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


def _company(db, *, cc_enabled=True):
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
    if cc_enabled:
        set_setting(db, "banking.company_card_enabled", True, company_id=co.id)
        set_setting(db, "banking.reconciliation_enabled", True, company_id=co.id)
    db.commit()
    return co


def _cc_card(db, co, *, name="Company Visa", balance=0.0):
    ba = models.BankAccount(
        name=name,
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=balance,
        kind="credit_card",
    )
    db.add(ba)
    db.commit()
    return ba


def _bank(db, co, *, balance=10000.0):
    ba = models.BankAccount(
        name="Main TRY",
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=balance,
        kind="bank",
    )
    db.add(ba)
    db.commit()
    return ba


def _vendor(db, co):
    v = models.Vendor(name="Supplier", company_id=co.id, is_active=True)
    db.add(v)
    db.commit()
    return v


def _gl_2110(db, co):
    return (
        db.query(models.ChartOfAccounts)
        .filter_by(account_name="Credit Card Payable", company_id=co.id)
        .one()
    )


def _stmt_row(db, co, bank, *, amount=100.0):
    imp = models.BankStatementImport(
        company_id=co.id,
        bank_account_id=bank.id,
        file_name="t.csv",
        file_hash="sync1",
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
        description="KK ODEME",
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


class TestCcExpenseSubledger:
    def test_cc_expense_syncs_2110_and_card(self, db):
        co = _company(db)
        card = _cc_card(db, co)
        exp = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="Expense",
            category="Office Expense",
            description="Supplies",
            amount=75.0,
            payment_method="Credit Card",
            company_id=co.id,
        )
        db.add(exp)
        db.commit()
        erp_app.post_expense(
            db, exp.id, 75.0, exp.date, "Office Expense", payment_method="Credit Card"
        )
        db.commit()
        db.refresh(card)
        db.refresh(exp)
        cc_gl = _gl_2110(db, co)
        assert erp_app.calculate_account_balance(db, cc_gl) == 75.0
        assert card.balance == 75.0
        assert exp.credit_card_account_id == card.id
        btxn = (
            db.query(models.BankTransaction)
            .filter_by(statement_ref=cc_subledger_stmt_ref("Expense", exp.id))
            .one()
        )
        assert btxn.type == "withdrawal"
        assert btxn.amount == 75.0


class TestCcPurchaseSubledger:
    def test_cc_purchase_syncs_2110_and_card(self, db):
        co = _company(db)
        card = _cc_card(db, co)
        vendor = _vendor(db, co)
        pur = models.Purchase(
            date=datetime.date.today(),
            vendor_id=vendor.id,
            amount=120.0,
            description="Stock",
            purchase_type="Credit Card",
            gl_debit="Inventory",
            company_id=co.id,
        )
        db.add(pur)
        db.commit()
        erp_app.post_purchase(
            db, pur.id, 120.0, pur.date, "Credit Card", "Inventory"
        )
        db.commit()
        db.refresh(card)
        db.refresh(pur)
        cc_gl = _gl_2110(db, co)
        assert erp_app.calculate_account_balance(db, cc_gl) == 120.0
        assert card.balance == 120.0
        assert pur.credit_card_account_id == card.id


class TestCcPayablePaymentSubledger:
    def test_cc_payable_payment_syncs_2110_and_card(self, db):
        co = _company(db)
        card = _cc_card(db, co)
        vendor = _vendor(db, co)
        payable = models.Payable(
            vendor_id=vendor.id,
            amount=90.0,
            balance=90.0,
            paid_amount=0.0,
            date=datetime.date.today(),
            due_date=datetime.date.today(),
            company_id=co.id,
        )
        db.add(payable)
        db.commit()
        erp_app.post_payable_payment(
            db, payable.id, 90.0, payable.date, payment_method="Credit Card"
        )
        db.commit()
        db.refresh(card)
        db.refresh(payable)
        cc_gl = _gl_2110(db, co)
        assert erp_app.calculate_account_balance(db, cc_gl) == 90.0
        assert card.balance == 90.0
        assert payable.credit_card_account_id == card.id


class TestBillPayAfterSyncedCharge:
    def test_bill_pay_zeros_gl_and_card(self, db):
        co = _company(db)
        card = _cc_card(db, co, balance=0.0)
        bank = _bank(db, co)
        exp = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="Expense",
            category="Office Expense",
            description="Charge",
            amount=100.0,
            payment_method="Credit Card",
            company_id=co.id,
        )
        db.add(exp)
        db.commit()
        erp_app.post_expense(
            db, exp.id, 100.0, exp.date, "Office Expense", payment_method="Credit Card"
        )
        db.commit()
        row = _stmt_row(db, co, bank, amount=100.0)
        post_credit_card_bill_payment(
            db,
            row_id=row.id,
            company_id=co.id,
            credit_card_account_id=card.id,
            user_id=None,
        )
        db.refresh(card)
        cc_gl = _gl_2110(db, co)
        assert erp_app.calculate_account_balance(db, cc_gl) == 0.0
        assert card.balance == 0.0


class TestMultipleCards:
    def test_requires_explicit_card_when_multiple(self, db):
        co = _company(db)
        _cc_card(db, co, name="Visa")
        _cc_card(db, co, name="Amex")
        exp = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="Expense",
            category="Office Expense",
            description="Supplies",
            amount=40.0,
            payment_method="Credit Card",
            company_id=co.id,
        )
        db.add(exp)
        db.commit()
        with pytest.raises(ValueError, match="Select which company credit card"):
            erp_app.post_expense(
                db, exp.id, 40.0, exp.date, "Office Expense", payment_method="Credit Card"
            )

    def test_posts_to_selected_card(self, db):
        co = _company(db)
        visa = _cc_card(db, co, name="Visa")
        amex = _cc_card(db, co, name="Amex")
        exp = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="Expense",
            category="Office Expense",
            description="Supplies",
            amount=40.0,
            payment_method="Credit Card",
            company_id=co.id,
        )
        db.add(exp)
        db.commit()
        erp_app.post_expense(
            db, exp.id, 40.0, exp.date, "Office Expense",
            payment_method="Credit Card", credit_card_account_id=amex.id,
        )
        db.commit()
        db.refresh(visa)
        db.refresh(amex)
        assert visa.balance == 0.0
        assert amex.balance == 40.0


class TestNoCards:
    def test_cc_posting_blocked_without_card_account(self, db):
        co = _company(db)
        exp = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="Expense",
            category="Office Expense",
            description="Supplies",
            amount=25.0,
            payment_method="Credit Card",
            company_id=co.id,
        )
        db.add(exp)
        db.commit()
        with pytest.raises(ValueError, match="No active company credit card"):
            erp_app.post_expense(
                db, exp.id, 25.0, exp.date, "Office Expense", payment_method="Credit Card"
            )


class TestVoidSymmetry:
    def test_void_cc_expense_reverses_card(self, db):
        co = _company(db)
        card = _cc_card(db, co)
        exp = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="Expense",
            category="Office Expense",
            description="Supplies",
            amount=55.0,
            payment_method="Credit Card",
            company_id=co.id,
        )
        db.add(exp)
        db.commit()
        erp_app.post_expense(
            db, exp.id, 55.0, exp.date, "Office Expense", payment_method="Credit Card"
        )
        db.commit()
        erp_app.void_expense(db, exp.id, "test void")
        db.refresh(card)
        cc_gl = _gl_2110(db, co)
        assert erp_app.calculate_account_balance(db, cc_gl) == 0.0
        assert card.balance == 0.0

    def test_void_cc_purchase_reverses_card(self, db):
        co = _company(db)
        card = _cc_card(db, co)
        vendor = _vendor(db, co)
        pur = models.Purchase(
            date=datetime.date.today(),
            vendor_id=vendor.id,
            amount=80.0,
            description="Stock",
            purchase_type="Credit Card",
            gl_debit="Inventory",
            company_id=co.id,
        )
        db.add(pur)
        db.commit()
        erp_app.post_purchase(
            db, pur.id, 80.0, pur.date, "Credit Card", "Inventory"
        )
        db.commit()
        erp_app.void_purchase(db, pur.id, "test void")
        db.refresh(card)
        cc_gl = _gl_2110(db, co)
        assert erp_app.calculate_account_balance(db, cc_gl) == 0.0
        assert card.balance == 0.0


class TestEditCcPurchase:
    def test_edit_amount_reverses_and_reposts_card(self, db):
        co = _company(db)
        card = _cc_card(db, co)
        vendor = _vendor(db, co)
        pur = models.Purchase(
            date=datetime.date.today(),
            vendor_id=vendor.id,
            amount=50.0,
            description="Stock",
            purchase_type="Credit Card",
            gl_debit="Inventory",
            company_id=co.id,
        )
        db.add(pur)
        db.commit()
        erp_app.post_purchase(
            db, pur.id, 50.0, pur.date, "Credit Card", "Inventory"
        )
        db.commit()
        ok, err = erp_app.edit_purchase(db, pur.id, {"amount": 70.0})
        assert ok and err is None
        db.refresh(card)
        cc_gl = _gl_2110(db, co)
        assert erp_app.calculate_account_balance(db, cc_gl) == 70.0
        assert card.balance == 70.0


class TestCustomerCardSaleRegression:
    def test_card_sale_untouched(self, db):
        co = _company(db)
        card = _cc_card(db, co, balance=0.0)
        bank = _bank(db, co, balance=500.0)
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="INV-1",
            customer_name="Walk-in",
            description="Card sale",
            amount=200.0,
            sale_type="Card",
            paid_amount=200.0,
            balance=0.0,
            status="Paid",
            company_id=co.id,
        )
        db.add(sale)
        db.commit()
        erp_app.post_card_sale(db, sale.id, 200.0, sale.date)
        db.commit()
        db.refresh(card)
        cc_gl = _gl_2110(db, co)
        assert erp_app.calculate_account_balance(db, cc_gl) == 0.0
        assert card.balance == 0.0
        assert (
            db.query(models.JournalEntry)
            .filter_by(reference_type="CardPurchase", reference_id=sale.id)
            .count()
        ) == 0
