"""Company Credit Card enablement — UI helpers, mobile parity, posting safety."""

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
        ("2110", "Credit Card Payable", "Liability"),
        ("5100", "Office Expense", "Expense"),
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


def _company(db, *, cc_enabled: bool):
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
    set_setting(
        db, "banking.company_card_enabled", cc_enabled, company_id=co.id
    )
    if cc_enabled:
        _cc_card(db, co)
    db.commit()
    return co


class TestPayMethodHelpers:
    def test_cc_hidden_when_disabled(self, db):
        _company(db, cc_enabled=False)
        assert "Credit Card" not in erp_app._business_pay_methods(db)
        assert "Credit Card" not in erp_app._at_expense_pay_methods(db)
        assert "Credit Card" not in erp_app._at_purchase_pay_methods(db)
        assert "Credit Card" not in erp_app._at_supplier_pay_methods(db)

    def test_cc_hidden_from_expense_entry_when_enabled(self, db):
        _company(db, cc_enabled=True)
        assert erp_app._company_cc_charge_ready(db)
        assert "Credit Card" not in erp_app._at_expense_pay_methods(db)
        assert "Credit Card" not in erp_app._expense_form_pay_methods(db)
        assert "Credit Card" in erp_app._business_pay_methods(db)
        assert "Credit Card" in erp_app._at_purchase_pay_methods(db)

    def test_cc_hidden_when_enabled_without_card_account(self, db):
        co = _company(db, cc_enabled=True)
        db.query(models.BankAccount).filter_by(company_id=co.id).delete()
        db.commit()
        assert not erp_app._company_cc_charge_ready(db)
        assert "Credit Card" not in erp_app._at_expense_pay_methods(db)

    def test_new_transaction_helpers_are_shared_source(self, db):
        """Desktop and mobile New Transaction read the same helper lists."""
        _company(db, cc_enabled=True)
        expense = erp_app._at_expense_pay_methods(db)
        purchase = erp_app._at_purchase_pay_methods(db)
        supplier = erp_app._at_supplier_pay_methods(db)
        assert expense == erp_app._at_expense_pay_methods(db)
        assert purchase == erp_app._at_purchase_pay_methods(db)
        assert supplier == erp_app._at_supplier_pay_methods(db)
        assert expense == ["Cash", "Bank"]
        assert purchase[-1] == "Credit Card"
        assert supplier[-1] == "Credit Card"

    def test_validate_company_cc_payment(self, db):
        _company(db, cc_enabled=False)
        assert erp_app._validate_company_cc_payment(db, "Credit Card")
        assert erp_app._validate_company_cc_payment(db, "Cash") is None

    def test_coerce_at_pm_resets_stale_cc_when_disabled(self, db):
        _company(db, cc_enabled=False)
        erp_app.st.session_state["at_pm"] = "Credit Card"
        erp_app._coerce_at_payment_method(db, "Expense")
        assert erp_app.st.session_state["at_pm"] == "Cash"
        erp_app.st.session_state["at_pm"] = "Credit Card"
        erp_app._coerce_at_payment_method(db, "Purchase")
        assert erp_app.st.session_state["at_pm"] == "Credit"


class TestResolvePaymentCreditAccount:
    def test_blocks_company_cc_when_disabled(self, db):
        _company(db, cc_enabled=False)
        with pytest.raises(ValueError, match="Company Credit Card is not enabled"):
            erp_app._resolve_payment_credit_account(db, "Credit Card")

    def test_company_cc_credits_payable_when_enabled(self, db):
        co = _company(db, cc_enabled=True)
        acct = erp_app._resolve_payment_credit_account(db, "Credit Card")
        cc = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Credit Card Payable", company_id=co.id)
            .one()
        )
        assert acct.id == cc.id

    def test_customer_card_sale_type_not_company_cc(self, db):
        """sale_type Card must not route to Credit Card Payable via this resolver."""
        co = _company(db, cc_enabled=True)
        acct = erp_app._resolve_payment_credit_account(db, "Card")
        cc = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Credit Card Payable", company_id=co.id)
            .one()
        )
        assert acct.id != cc.id


class TestPostingSafety:
    def test_post_expense_blocks_cc_when_disabled(self, db):
        co = _company(db, cc_enabled=False)
        exp = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="Expense",
            category="Office Expense",
            description="Supplies",
            amount=50.0,
            payment_method="Credit Card",
            company_id=co.id,
        )
        db.add(exp)
        db.commit()
        with pytest.raises(ValueError, match="Company Credit Card is not enabled"):
            erp_app.post_expense(
                db,
                exp.id,
                50.0,
                exp.date,
                "Office Expense",
                payment_method="Credit Card",
            )

    def test_post_expense_cc_payable_when_enabled(self, db):
        co = _company(db, cc_enabled=True)
        exp = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="Expense",
            category="Office Expense",
            description="Supplies",
            amount=60.0,
            payment_method="Credit Card",
            company_id=co.id,
        )
        db.add(exp)
        db.commit()
        erp_app.post_expense(
            db,
            exp.id,
            60.0,
            exp.date,
            "Office Expense",
            payment_method="Credit Card",
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
        assert sum(l.credit for l in lines if l.account_id == cc.id) == 60.0
