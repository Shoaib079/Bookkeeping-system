"""Company CC expense form — visibility gating, save path, no silent reset."""

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
from reconciliation.company_card import cc_subledger_stmt_ref
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


def _company(db, *, cc_enabled: bool = True, with_card: bool = True):
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
    if with_card:
        db.add(
            models.BankAccount(
                name="Company Visa",
                currency="TRY",
                company_id=co.id,
                is_active=True,
                balance=0.0,
                kind="credit_card",
            )
        )
        db.commit()
    return co


class TestCcVisibility:
    def test_cc_hidden_when_toggle_off(self, db):
        _company(db, cc_enabled=False, with_card=False)
        assert "Credit Card" not in erp_app._at_expense_pay_methods(db)
        assert "Credit Card" not in erp_app._business_pay_methods(db)

    def test_cc_hidden_when_enabled_but_no_card(self, db):
        _company(db, cc_enabled=True, with_card=False)
        assert not erp_app._company_cc_charge_ready(db)
        assert "Credit Card" not in erp_app._at_expense_pay_methods(db)
        assert "Credit Card" not in erp_app._business_pay_methods(db)

    def test_cc_hidden_from_expense_entry_when_ready(self, db):
        """OBS-007 — CC posting remains; Expense entry UI excludes company CC."""
        _company(db, cc_enabled=True, with_card=True)
        assert erp_app._company_cc_charge_ready(db)
        assert "Credit Card" not in erp_app._at_expense_pay_methods(db)
        assert "Credit Card" not in erp_app._expense_form_pay_methods(db)
        assert "Credit Card" in erp_app._business_pay_methods(db)


class TestCcCardResolution:
    def test_auto_select_one_card(self, db):
        co = _company(db)
        card = (
            db.query(models.BankAccount)
            .filter_by(company_id=co.id, kind="credit_card")
            .one()
        )
        resolved = erp_app._resolve_submit_company_cc_card_id(db, "Credit Card", None)
        assert resolved == card.id

    def test_multiple_cards_requires_explicit_id(self, db):
        co = _company(db)
        db.add(
            models.BankAccount(
                name="Amex",
                currency="TRY",
                company_id=co.id,
                is_active=True,
                balance=0.0,
                kind="credit_card",
            )
        )
        db.commit()
        assert erp_app._resolve_submit_company_cc_card_id(db, "Credit Card", None) is None
        err = erp_app._validate_company_cc_card(db, "Credit Card", None)
        assert err is not None


class TestNewTransactionTypeState:
    def test_desktop_sync_keeps_expense_type(self):
        erp_app.st.session_state["at_type_idx"] = 1
        erp_app.st.session_state["mob_at_tab"] = 0
        erp_app.st.session_state["_erp_mobile_ui"] = False
        erp_app._at_sync_desktop_type_to_mobile_tabs()
        erp_app._mob_at_sync_type_from_tab()
        assert erp_app.st.session_state["at_type_idx"] == 1
        assert erp_app.st.session_state["mob_at_tab"] == 1

    def test_mobile_sync_drives_type_on_mobile_ui(self):
        erp_app.st.session_state["at_type_idx"] = 1
        erp_app.st.session_state["mob_at_tab"] = 0
        erp_app.st.session_state["_erp_mobile_ui"] = True
        erp_app._mob_at_sync_type_from_tab()
        assert erp_app.st.session_state["at_type_idx"] == 0

    def test_flash_survives_rerun_simulation(self):
        erp_app._at_set_flash("error", "Select which company credit card")
        assert erp_app.st.session_state["at_flash_message"] == "Select which company credit card"
        assert erp_app.st.session_state["at_flash_level"] == "error"

    def test_success_flag_sets_flash(self):
        erp_app._mark_at_save_succeeded("Expense recorded")
        assert erp_app.st.session_state["_at_save_succeeded"] is True
        assert erp_app.st.session_state["at_flash_message"] == "Expense recorded"
        assert erp_app.st.session_state["at_flash_level"] == "success"

    def test_bank_pm_change_preserves_type_and_amount(self, db):
        erp_app.st.session_state["at_type_idx"] = 1
        erp_app.st.session_state["at_pm"] = "Cash"
        erp_app.st.session_state["at_amount_display"] = "42.50"
        erp_app.st.session_state["_erp_mobile_ui"] = False
        erp_app.st.session_state["at_pm"] = "Bank"
        erp_app._coerce_at_payment_method(db, "Expense")
        erp_app._mob_at_sync_type_from_tab()
        assert erp_app.st.session_state["at_type_idx"] == 1
        assert erp_app.st.session_state["at_pm"] == "Bank"
        assert erp_app.st.session_state["at_amount_display"] == "42.50"

    def test_customer_select_preserves_form_state(self):
        erp_app.st.session_state.update(
            {
                "at_type_idx": 0,
                "at_pm": "Credit",
                "at_cust_sel": "Acme Corp",
                "at_amount_display": "100.00",
                "at_notes_field": "test note",
                "_erp_mobile_ui": False,
            }
        )
        erp_app.st.session_state["at_cust"] = erp_app.st.session_state["at_cust_sel"]
        erp_app._mob_at_sync_type_from_tab()
        assert erp_app.st.session_state["at_type_idx"] == 0
        assert erp_app.st.session_state["at_pm"] == "Credit"
        assert erp_app.st.session_state["at_amount_display"] == "100.00"
        assert erp_app.st.session_state["at_notes_field"] == "test note"

    def test_desktop_sync_does_not_overwrite_at_pm(self):
        erp_app.st.session_state.update(
            {
                "at_type_idx": 1,
                "at_pm": "Bank",
                "mob_at_tab": 0,
                "_erp_mobile_ui": False,
            }
        )
        erp_app._at_sync_desktop_type_to_mobile_tabs()
        erp_app._mob_at_sync_type_from_tab()
        assert erp_app.st.session_state["at_pm"] == "Bank"
        assert erp_app.st.session_state["at_type_idx"] == 1
        assert erp_app.st.session_state["mob_at_tab"] == 1

    def test_clear_stale_mobile_overlay_state(self):
        erp_app.st.session_state["mob_at_picker"] = "bank_pay"
        erp_app.st.session_state["mob_at_picker_search"] = "main"
        erp_app._at_clear_stale_mobile_overlay_state()
        assert "mob_at_picker" not in erp_app.st.session_state
        assert "mob_at_picker_search" not in erp_app.st.session_state


class TestExpenseSavePath:
    def test_save_and_post_updates_gl_and_subledger(self, db):
        co = _company(db)
        card = (
            db.query(models.BankAccount)
            .filter_by(company_id=co.id, kind="credit_card")
            .one()
        )
        record = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="Expense",
            category="Office Expense",
            description="Supplies",
            amount=85.0,
            payment_method="Credit Card",
            company_id=co.id,
        )
        ok, err = erp_app._save_and_post_expense_record(
            db,
            record,
            category="Office Expense",
            payment_method="Credit Card",
        )
        assert ok is True
        assert err is None
        db.refresh(card)
        db.refresh(record)
        assert record.credit_card_account_id == card.id
        assert card.balance == 85.0
        cc_gl = (
            db.query(models.ChartOfAccounts)
            .filter_by(account_name="Credit Card Payable", company_id=co.id)
            .one()
        )
        je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="Expense", reference_id=record.id)
            .one()
        )
        lines = (
            db.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .all()
        )
        assert sum(l.credit for l in lines if l.account_id == cc_gl.id) == 85.0
        stmt_ref = cc_subledger_stmt_ref("Expense", record.id)
        txn = (
            db.query(models.BankTransaction)
            .filter_by(statement_ref=stmt_ref, is_void=False)
            .one()
        )
        assert txn.account_id == card.id
        assert txn.amount == 85.0

    def test_save_failure_returns_error_not_success_flag(self, db):
        co = _company(db, with_card=False)
        set_setting(db, "banking.company_card_enabled", True, company_id=co.id)
        record = models.ExpenseRecord(
            date=datetime.date.today(),
            expense_type="Expense",
            category="Office Expense",
            description="Supplies",
            amount=50.0,
            payment_method="Credit Card",
            company_id=co.id,
        )
        ok, err = erp_app._save_and_post_expense_record(
            db,
            record,
            category="Office Expense",
            payment_method="Credit Card",
        )
        assert ok is False
        assert err
        assert (
            db.query(models.ExpenseRecord)
            .filter_by(description="Supplies")
            .count()
            == 0
        )

    def test_at_save_cc_expense_sets_success_flag(self, db):
        co = _company(db)
        erp_app.st.session_state["at_expense_mode"] = "general"
        erp_app.st.session_state["_at_save_succeeded"] = False
        erp_app._at_save(
            db,
            txn_type="Expense",
            date=datetime.date.today(),
            amount=120.0,
            currency="TRY",
            payment_method="Credit Card",
            notes="Office supplies",
            customer_name="",
            category="Office Expense",
            vendor_name=None,
            invoice_choices=[],
            invoice_choice_val=None,
            open_sales=[],
            bank_sub="Deposit",
            bank_acct_val=None,
            bank_dest_val=None,
            bank_accounts=[],
            vendors=[],
            credit_card_account_id=erp_app._resolve_submit_company_cc_card_id(
                db, "Credit Card", None
            ),
        )
        assert erp_app.st.session_state.get("_at_save_succeeded") is True
        exp = db.query(models.ExpenseRecord).one()
        assert exp.payment_method == "Credit Card"
        assert exp.company_id == co.id

    def test_at_save_cc_failure_does_not_set_success_flag(self, db):
        _company(db, with_card=False)
        set_setting(
            db,
            "banking.company_card_enabled",
            True,
            company_id=erp_app.st.session_state["active_company_id"],
        )
        erp_app.st.session_state["at_expense_mode"] = "general"
        erp_app.st.session_state["_at_save_succeeded"] = False
        erp_app._at_save(
            db,
            txn_type="Expense",
            date=datetime.date.today(),
            amount=40.0,
            currency="TRY",
            payment_method="Credit Card",
            notes="Test",
            customer_name="",
            category="Office Expense",
            vendor_name=None,
            invoice_choices=[],
            invoice_choice_val=None,
            open_sales=[],
            bank_sub="Deposit",
            bank_acct_val=None,
            bank_dest_val=None,
            bank_accounts=[],
            vendors=[],
            credit_card_account_id=None,
        )
        assert erp_app.st.session_state.get("_at_save_succeeded") is not True
