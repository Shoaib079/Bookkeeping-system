"""Phase 18-MVP-5 — Company credit card."""

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
    is_credit_card_account,
    post_credit_card_bill_payment,
)
from reconciliation.match_post import (
    MatchPostError,
    post_equity_statement_match,
    post_partner_statement_match,
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
        ("2000", "Accounts Payable", "Liability"),
        ("2110", "Credit Card Payable", "Liability"),
        ("5100", "Office Expense", "Expense"),
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


def _bank(db, co, *, kind="bank", name="Main TRY"):
    ba = models.BankAccount(
        name=name,
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=10000.0 if kind == "bank" else 500.0,
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
        file_hash="abc5",
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
        description=desc,
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


class TestCompanyCardHelpers:
    def test_credit_card_balance_direction(self):
        ba = models.BankAccount(name="Visa", kind="credit_card", balance=100.0)
        apply_account_balance_delta(ba, "withdrawal", 50)
        assert ba.balance == 150.0
        apply_account_balance_delta(ba, "deposit", 30)
        assert ba.balance == 120.0
        assert is_credit_card_account(ba)
        assert not is_credit_card_account(models.BankAccount(name="Bank", kind="bank"))


class TestPosting:
    def test_expense_on_credit_card_credits_payable(self, db):
        co = _company(db)
        exp = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="Expense",
            category="Office Expense",
            description="Supplies",
            amount=80.0,
            payment_method="Credit Card",
            company_id=co.id,
        )
        db.add(exp)
        db.commit()
        erp_app.post_expense(
            db, exp.id, 80.0, exp.date, "Office Expense", payment_method="Credit Card"
        )
        db.commit()
        je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="Expense", reference_id=exp.id)
            .one()
        )
        lines = (
            db.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .all()
        )
        cc = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Credit Card Payable", company_id=co.id)
            .one()
        )
        assert sum(l.credit for l in lines if l.account_id == cc.id) == 80.0

    def test_payable_payment_by_card(self, db):
        co = _company(db)
        vendor = models.Vendor(name="Supplier", company_id=co.id, is_active=True)
        db.add(vendor)
        db.flush()
        payable = models.Payable(
            vendor_id=vendor.id,
            amount=200.0,
            balance=200.0,
            paid_amount=0.0,
            date=datetime.date.today(),
            due_date=datetime.date.today(),
            company_id=co.id,
        )
        db.add(payable)
        db.commit()
        erp_app.post_payable_payment(
            db, payable.id, 200.0, payable.date, payment_method="Credit Card"
        )
        db.commit()
        je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="PayablePayment", reference_id=payable.id)
            .one()
        )
        lines = (
            db.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .all()
        )
        cc = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Credit Card Payable", company_id=co.id)
            .one()
        )
        assert sum(l.credit for l in lines if l.account_id == cc.id) == 200.0

    def test_post_credit_card_bill_payment(self, db):
        co = _company(db)
        bank = _bank(db, co, kind="bank")
        card = _bank(db, co, kind="credit_card", name="Company Visa")
        row = _stmt_row(db, co, bank, amount=250.0)
        result = post_credit_card_bill_payment(
            db,
            row_id=row.id,
            company_id=co.id,
            credit_card_account_id=card.id,
            user_id=None,
        )
        db.refresh(row)
        db.refresh(bank)
        db.refresh(card)
        assert result["match_type"] == "cc_bill_payment"
        assert row.status == "posted"
        assert row.match_type == "cc_bill_payment"
        assert row.credit_card_account_id == card.id
        assert bank.balance == 10000.0 - 250.0
        assert card.balance == 500.0 - 250.0
        je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="BankStmtCCBillPay", reference_id=row.id)
            .one()
        )
        lines = (
            db.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .all()
        )
        cc = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Credit Card Payable", company_id=co.id)
            .one()
        )
        bank_gl = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Bank", company_id=co.id)
            .one()
        )
        assert sum(l.debit for l in lines if l.account_id == cc.id) == 250.0
        assert sum(l.credit for l in lines if l.account_id == bank_gl.id) == 250.0

    def test_partner_salary_from_statement(self, db):
        co = _company(db)
        bank = _bank(db, co, kind="bank")
        cap = models.ChartOfAccounts(
            account_code="3501",
            account_name="Ali Capital",
            account_type="Equity",
            company_id=co.id,
        )
        cur = models.ChartOfAccounts(
            account_code="3601",
            account_name="Ali Current",
            account_type="Equity",
            company_id=co.id,
        )
        adv = models.ChartOfAccounts(
            account_code="1501",
            account_name="Ali Advances",
            account_type="Asset",
            company_id=co.id,
        )
        db.add_all([cap, cur, adv])
        db.flush()
        partner = models.Partner(
            name="Ali",
            profit_share_pct=50.0,
            capital_account_id=cap.id,
            current_account_id=cur.id,
            advance_account_id=adv.id,
            is_active=True,
            company_id=co.id,
            created_at=datetime.datetime.utcnow(),
        )
        db.add(partner)
        db.commit()
        row = _stmt_row(db, co, bank, amount=1500.0, desc="ORTAK MAAS")
        result = post_partner_statement_match(
            db,
            row_id=row.id,
            company_id=co.id,
            partner_id=partner.id,
            movement_type="Salary",
            user_id=None,
        )
        db.refresh(row)
        assert result["match_type"] == "partner_salary"
        assert row.partner_movement_id is not None
        je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="PartnerSalary", reference_id=row.partner_movement_id)
            .one()
        )
        assert je is not None

    def test_owner_drawing_from_statement(self, db):
        co = _company(db)
        db.add(
            models.ChartOfAccounts(
                account_code="3200",
                account_name="Owner Drawings",
                account_type="Equity",
                company_id=co.id,
            )
        )
        db.commit()
        bank = _bank(db, co, kind="bank")
        row = _stmt_row(db, co, bank, amount=500.0, desc="SAHIP CEKIM")
        post_equity_statement_match(
            db,
            row_id=row.id,
            company_id=co.id,
            equity_kind="owner_drawing",
            user_id=None,
        )
        db.refresh(row)
        assert row.match_type == "owner_drawing"
        je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="BankStmtOwnerDrawing", reference_id=row.id)
            .one()
        )
        assert je is not None

    def test_bill_payment_requires_toggle(self, db):
        co = _company(db)
        set_setting(db, "banking.company_card_enabled", False, company_id=co.id)
        db.commit()
        bank = _bank(db, co)
        card = _bank(db, co, kind="credit_card", name="Visa")
        row = _stmt_row(db, co, bank)
        with pytest.raises(MatchPostError, match="Company credit card"):
            post_credit_card_bill_payment(
                db,
                row_id=row.id,
                company_id=co.id,
                credit_card_account_id=card.id,
                user_id=None,
            )
