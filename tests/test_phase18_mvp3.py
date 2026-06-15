"""Phase 18-MVP-3 — Manual bank statement match & post."""

import datetime
import json
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
from reconciliation.clearing import get_unsettled_card_sales
from reconciliation.match_post import (
    MatchPostError,
    post_deposit_clearing_match,
    post_vendor_outflow,
)
from registry.coa_seed import ensure_accounts_for_company
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
        ("4000", "Sales Revenue", "Income"),
        ("2000", "Accounts Payable", "Liability"),
        ("5100", "Office Expense", "Expense"),
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
    ensure_accounts_for_company(db, co.id)
    db.commit()
    return co


def _bank(db, co):
    ba = models.BankAccount(
        name="Main TRY",
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=0.0,
    )
    db.add(ba)
    db.commit()
    return ba


def _stmt_row(db, co, ba, *, credit=True, amount=100.0):
    imp = models.BankStatementImport(
        company_id=co.id,
        bank_account_id=ba.id,
        file_name="t.csv",
        file_hash="abc",
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
        description="Test deposit",
        debit_amount=None if credit else amount,
        credit_amount=amount if credit else None,
        amount=amount,
        currency="TRY",
        original_amount=amount,
        parsed_successfully=True,
        created_at=utc_now_naive(),
    )
    db.add(row)
    db.commit()
    return row, imp


class TestSchema:
    def test_bank_statement_row_posting_columns(self):
        cols = set(models.BankStatementRow.__table__.columns.keys())
        assert "match_type" in cols
        assert "posted_journal_entry_id" in cols
        assert "clearing_sale_ids_json" in cols


class TestMatchPost:
    def test_deposit_clearing_match_posts_je_and_marks_row(self, db):
        co = _company(db)
        set_setting(db, "banking.card_settlement_enabled", True, company_id=co.id)
        db.commit()
        ba = _bank(db, co)
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="INV-1",
            customer_name="Walk-in",
            amount=100.0,
            sale_type="Card",
            status="Paid",
            company_id=co.id,
        )
        db.add(sale)
        db.commit()
        erp_app.post_card_sale(db, sale.id, 100.0, sale.date, currency="TRY")

        row, _imp = _stmt_row(db, co, ba, credit=True, amount=100.0)
        post_deposit_clearing_match(
            db,
            row_id=row.id,
            company_id=co.id,
            sale_ids=[sale.id],
            user_id=1,
        )
        db.refresh(row)
        assert row.status == "posted"
        assert row.match_type == "deposit_clearing"
        assert row.bank_transaction_id is not None
        assert json.loads(row.clearing_sale_ids_json) == [sale.id]

        clearing = get_unsettled_card_sales(
            db,
            co.id,
            date_from=datetime.date.today(),
            date_to=datetime.date.today(),
            get_account_by_name=erp_app.get_account_by_name,
        )
        assert clearing == []

        btxn = db.get(models.BankTransaction, row.bank_transaction_id)
        assert btxn.is_reconciled is True
        assert btxn.statement_ref == f"bsr:{row.id}"

    def test_deposit_clearing_amount_mismatch_raises(self, db):
        co = _company(db)
        set_setting(db, "banking.card_settlement_enabled", True, company_id=co.id)
        db.commit()
        ba = _bank(db, co)
        sale = models.Sale(
            date=datetime.date.today(),
            invoice_number="INV-2",
            customer_name="Walk-in",
            amount=50.0,
            sale_type="Card",
            status="Paid",
            company_id=co.id,
        )
        db.add(sale)
        db.commit()
        erp_app.post_card_sale(db, sale.id, 50.0, sale.date, currency="TRY")
        row, _ = _stmt_row(db, co, ba, credit=True, amount=100.0)
        with pytest.raises(MatchPostError):
            post_deposit_clearing_match(
                db,
                row_id=row.id,
                company_id=co.id,
                sale_ids=[sale.id],
                user_id=None,
            )

    def test_vendor_adhoc_expense_posts(self, db):
        co = _company(db)
        ba = _bank(db, co)
        vendor = models.Vendor(name="Supplier A", company_id=co.id, is_active=True)
        db.add(vendor)
        db.commit()
        row, _ = _stmt_row(db, co, ba, credit=False, amount=75.0)
        post_vendor_outflow(
            db,
            row_id=row.id,
            company_id=co.id,
            vendor_id=vendor.id,
            user_id=2,
            create_expense=True,
            expense_category="Office Expense",
        )
        db.refresh(row)
        assert row.status == "posted"
        assert row.match_type == "adhoc_expense"
        assert row.expense_record_id is not None
        exp = db.get(models.ExpenseRecord, row.expense_record_id)
        assert exp.amount == 75.0
