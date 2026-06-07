"""Recon Health — Credit Card Payable GL (2110) vs card sub-ledger total."""

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
from reconciliation.company_card import (
    apply_account_balance_delta,
    compute_cc_payable_recon_health,
    post_credit_card_bill_payment,
)


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
                company_id=co.id,
            )
        )
    db.commit()


def _company(db):
    from registry.service import set_setting

    co = models.Company(
        name="Acme",
        slug="acme",
        is_active=True,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(co)
    db.commit()
    erp_app.st.session_state["active_company_id"] = co.id
    _seed_coa(db, co)
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


def _stmt_row(db, co, bank, *, amount=100.0):
    imp = models.BankStatementImport(
        company_id=co.id,
        bank_account_id=bank.id,
        file_name="t.csv",
        file_hash="rh1",
        file_size=10,
        file_path="/tmp/t.csv",
        status="staging",
        import_date=datetime.date.today(),
        row_count=1,
        valid_count=1,
        flagged_count=0,
        error_count=0,
        currency="TRY",
        created_at=datetime.datetime.utcnow(),
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
        created_at=datetime.datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    return row


def _health(db, co):
    return compute_cc_payable_recon_health(db, co.id)


class TestSyncedNoDrift:
    def test_cc_expense_no_drift(self, db):
        co = _company(db)
        _cc_card(db, co)
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
        h = _health(db, co)
        assert h["status"] == "ok"
        assert abs(h["difference"]) < 0.01
        assert h["gl_balance"] == 75.0
        assert h["subledger_total"] == 75.0

    def test_cc_purchase_no_drift(self, db):
        co = _company(db)
        _cc_card(db, co)
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
        h = _health(db, co)
        assert h["status"] == "ok"
        assert h["gl_balance"] == h["subledger_total"] == 120.0

    def test_cc_payable_payment_no_drift(self, db):
        co = _company(db)
        _cc_card(db, co)
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
        h = _health(db, co)
        assert h["status"] == "ok"
        assert h["gl_balance"] == h["subledger_total"] == 90.0

    def test_bill_payment_keeps_no_drift(self, db):
        co = _company(db)
        card = _cc_card(db, co)
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
        db.commit()
        h = _health(db, co)
        assert h["status"] == "ok"
        assert abs(h["difference"]) < 0.01
        assert h["gl_balance"] == 0.0
        assert h["subledger_total"] == 0.0


class TestDriftWarning:
    def test_manual_cc_withdrawal_creates_drift(self, db):
        co = _company(db)
        card = _cc_card(db, co)
        exp = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="Expense",
            category="Office Expense",
            description="Synced",
            amount=50.0,
            payment_method="Credit Card",
            company_id=co.id,
        )
        db.add(exp)
        db.commit()
        erp_app.post_expense(
            db, exp.id, 50.0, exp.date, "Office Expense", payment_method="Credit Card"
        )
        db.commit()
        # Manual sub-ledger-only withdrawal (no GL) — mimics Banking manual CC entry
        apply_account_balance_delta(card, "withdrawal", 25.0)
        db.add(
            models.BankTransaction(
                account_id=card.id,
                date=datetime.date.today(),
                amount=25.0,
                type="withdrawal",
                description="Manual CC adjustment",
                company_id=co.id,
            )
        )
        db.add(card)
        db.commit()
        h = _health(db, co)
        assert h["status"] == "warning"
        assert h["gl_balance"] == 50.0
        assert h["subledger_total"] == 75.0
        assert h["difference"] == -25.0


class TestMultipleCards:
    def test_sums_active_card_balances(self, db):
        co = _company(db)
        visa = _cc_card(db, co, name="Visa")
        amex = _cc_card(db, co, name="Amex")
        for card, amt in ((visa, 30.0), (amex, 20.0)):
            exp = models.ExpenseRecord(
                date=datetime.date.today(),
                expense_type="Expense",
                category="Office Expense",
                description=card.name,
                amount=amt,
                payment_method="Credit Card",
                company_id=co.id,
            )
            db.add(exp)
            db.commit()
            erp_app.post_expense(
                db, exp.id, amt, exp.date, "Office Expense",
                payment_method="Credit Card", credit_card_account_id=card.id,
            )
            db.commit()
        h = _health(db, co)
        assert h["status"] == "ok"
        assert h["gl_balance"] == 50.0
        assert h["subledger_total"] == 50.0
        assert len(h["cards"]) == 2
        names = {c["name"] for c in h["cards"]}
        assert names == {"Visa", "Amex"}


class TestCustomerCardSaleRegression:
    def test_card_sale_does_not_affect_cc_health(self, db):
        co = _company(db)
        _cc_card(db, co)
        bank = _bank(db, co)
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="INV-RH-1",
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
        h = _health(db, co)
        assert h["status"] == "ok"
        assert h["gl_balance"] == 0.0
        assert h["subledger_total"] == 0.0
