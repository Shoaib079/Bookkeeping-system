"""POSTING-SERVICE-01 PS-P2c-CHAR — pre-extraction characterization.

Pins app.py behavior for expense/purchase posting, company CC subledger sync,
and related entry-point errors. No extraction in this phase.
"""
from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app
from reconciliation.company_card import CompanyCardError, cc_subledger_stmt_ref
from registry.coa_seed import seed_chart_of_accounts_for_company
from registry.service import set_setting

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 5, 20)
CC_NO_CARDS_MSG = app._t("form.err.company_cc_no_cards")
CC_DEDUP_PREFIX = "Sub-ledger charge already recorded"
CC_AMOUNT_MSG = "Charge amount must be positive."


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    _seed_dev_auth_user()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        co = models.Company(
            name="P2c Char Co",
            slug="p2c_char_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        seed_chart_of_accounts_for_company(s, co.id)
        set_setting(s, "banking.company_card_enabled", True, company_id=co.id)
        s.commit()
        yield s, co.id


def _cc_card(session, company_id, *, name="Company Visa"):
    ba = models.BankAccount(
        name=name,
        currency="TRY",
        company_id=company_id,
        is_active=True,
        balance=0.0,
        kind="credit_card",
    )
    session.add(ba)
    session.flush()
    return ba


def _vendor(session):
    v = models.Vendor(name="Vendor P2c", is_active=True)
    session.add(v)
    session.flush()
    return v


def _acct(session, name, currency=None):
    return app.get_account_by_name(session, name, currency=currency)


def _entries_for(session, ref_type, ref_id):
    return (
        session.query(models.JournalEntry)
        .filter_by(reference_type=ref_type, reference_id=ref_id)
        .all()
    )


def _line_tuples(session, journal_entry_id):
    lines = (
        session.query(models.JournalEntryLine)
        .filter_by(journal_entry_id=journal_entry_id)
        .order_by(models.JournalEntryLine.id)
        .all()
    )
    return [(ln.account_id, ln.debit or 0.0, ln.credit or 0.0) for ln in lines]


# ─── 1. statement_ref exact strings ──────────────────────────────────────────


class TestCcStatementRefStrings:
    def test_expense_statement_ref(self, session):
        db, cid = session
        card = _cc_card(db, cid)
        exp = models.ExpenseRecord(
            date=POST_DATE,
            expense_type="Expense",
            category="Office",
            description="Supplies",
            amount=50.0,
            payment_method="Credit Card",
            company_id=cid,
        )
        db.add(exp)
        db.commit()
        app.post_expense(
            db, exp.id, 50.0, POST_DATE, "Office", payment_method="Credit Card"
        )
        db.commit()
        expected = cc_subledger_stmt_ref("Expense", exp.id)
        assert expected == f"ccc:Expense:{exp.id}"
        btxn = db.query(models.BankTransaction).filter_by(statement_ref=expected).one()
        assert btxn.account_id == card.id

    def test_card_purchase_statement_ref(self, session):
        db, cid = session
        card = _cc_card(db, cid)
        vendor = _vendor(db)
        pur = models.Purchase(
            date=POST_DATE,
            vendor_id=vendor.id,
            amount=80.0,
            description="Stock",
            purchase_type="Credit Card",
            gl_debit="Inventory",
            company_id=cid,
        )
        db.add(pur)
        db.commit()
        app.post_purchase(
            db, pur.id, 80.0, POST_DATE, "Credit Card", "Inventory"
        )
        db.commit()
        expected = cc_subledger_stmt_ref("CardPurchase", pur.id)
        assert expected == f"ccc:CardPurchase:{pur.id}"
        btxn = db.query(models.BankTransaction).filter_by(statement_ref=expected).one()
        assert btxn.account_id == card.id

    def test_payable_payment_statement_ref_uses_je_id_not_payable_id(self, session):
        db, cid = session
        card = _cc_card(db, cid)
        vendor = _vendor(db)
        # Spacer JE so journal-entry id differs from payable id when both start at 1.
        cash = _acct(db, "Cash")
        revenue = _acct(db, "Sales Revenue")
        app.create_journal_entry(
            db, POST_DATE, "spacer", "Characterization", None,
            [(cash.id, 1.0, 0.0), (revenue.id, 0.0, 1.0)],
        )
        payable = models.Payable(
            date=POST_DATE,
            vendor_id=vendor.id,
            amount=60.0,
            paid_amount=0.0,
            balance=60.0,
            due_date=POST_DATE,
            paid=False,
            company_id=cid,
        )
        db.add(payable)
        db.commit()
        app.post_payable_payment(
            db, payable.id, 60.0, POST_DATE, payment_method="Credit Card"
        )
        db.commit()
        je = _entries_for(db, "PayablePayment", payable.id)[0]
        assert je.id != payable.id
        expected = cc_subledger_stmt_ref("PayablePayment", je.id)
        assert expected == f"ccc:PayablePayment:{je.id}"
        assert expected != f"ccc:PayablePayment:{payable.id}"
        btxn = db.query(models.BankTransaction).filter_by(statement_ref=expected).one()
        assert btxn.account_id == card.id


# ─── 2. _sync_company_cc_subledger ───────────────────────────────────────────


class TestSyncCompanyCcSubledger:
    def test_company_id_none_raises_exact_message(self, session):
        db, _cid = session
        sys.modules["streamlit"].session_state.pop("active_company_id", None)
        with pytest.raises(ValueError) as exc:
            app._sync_company_cc_subledger(
                db,
                "Credit Card",
                company_id=None,
                credit_card_account_id=None,
                amount=10.0,
                txn_date=POST_DATE,
                description="test",
                reference_type="Expense",
                reference_id=1,
            )
        assert str(exc.value) == CC_NO_CARDS_MSG

    def test_ambient_company_fallback_when_company_id_none(self, session):
        db, cid = session
        card = _cc_card(db, cid)
        app._sync_company_cc_subledger(
            db,
            "Credit Card",
            company_id=None,
            credit_card_account_id=card.id,
            amount=25.0,
            txn_date=POST_DATE,
            description="ambient sync",
            reference_type="Expense",
            reference_id=99,
        )
        db.commit()
        ref = cc_subledger_stmt_ref("Expense", 99)
        btxn = db.query(models.BankTransaction).filter_by(statement_ref=ref).one()
        assert btxn.company_id == cid

    def test_non_credit_card_method_is_noop(self, session):
        db, cid = session
        _cc_card(db, cid)
        before = db.query(models.BankTransaction).count()
        app._sync_company_cc_subledger(
            db,
            "Cash",
            company_id=cid,
            credit_card_account_id=None,
            amount=10.0,
            txn_date=POST_DATE,
            description="noop",
            reference_type="Expense",
            reference_id=1,
        )
        assert db.query(models.BankTransaction).count() == before


# ─── 3. Split-commit behavior ────────────────────────────────────────────────


class TestSplitCommitBehavior:
    def test_je_committed_subledger_pending_until_caller_commit(self, session):
        db, cid = session
        card = _cc_card(db, cid)
        exp = models.ExpenseRecord(
            date=POST_DATE,
            expense_type="Expense",
            category="Office",
            description="Split commit",
            amount=45.0,
            payment_method="Credit Card",
            company_id=cid,
        )
        db.add(exp)
        db.commit()

        app.post_expense(
            db, exp.id, 45.0, POST_DATE, "Office", payment_method="Credit Card"
        )

        je = _entries_for(db, "Expense", exp.id)[0]
        stmt_ref = cc_subledger_stmt_ref("Expense", exp.id)
        assert db.query(models.BankTransaction).filter_by(statement_ref=stmt_ref).count() == 1

        db.rollback()

        assert db.get(models.JournalEntry, je.id) is not None
        assert db.query(models.BankTransaction).filter_by(statement_ref=stmt_ref).count() == 0


# ─── 4. post_purchase ────────────────────────────────────────────────────────


class TestPostPurchaseCharacterization:
    def test_cash_purchase_je_tuples_and_ref_type(self, session):
        db, _cid = session
        vendor = _vendor(db)
        pur = models.Purchase(
            date=POST_DATE,
            vendor_id=vendor.id,
            amount=110.0,
            purchase_type="Cash",
            gl_debit="Inventory",
            company_id=_cid,
        )
        db.add(pur)
        db.commit()
        app.post_purchase(
            db, pur.id, 110.0, POST_DATE, purchase_type="Cash", gl_debit="Inventory"
        )
        entries = _entries_for(db, "CashPurchase", pur.id)
        assert len(entries) == 1
        je = entries[0]
        assert je.description == f"Cash Purchase (ID: {pur.id})"
        inventory = _acct(db, "Inventory")
        cash = _acct(db, "Cash")
        assert _line_tuples(db, je.id) == [
            (inventory.id, 110.0, 0.0),
            (cash.id, 0.0, 110.0),
        ]

    def test_bank_purchase_je_tuples_and_ref_type(self, session):
        db, _cid = session
        vendor = _vendor(db)
        pur = models.Purchase(
            date=POST_DATE,
            vendor_id=vendor.id,
            amount=95.0,
            purchase_type="Bank",
            gl_debit="Rent",
            company_id=_cid,
        )
        db.add(pur)
        db.commit()
        app.post_purchase(
            db, pur.id, 95.0, POST_DATE, purchase_type="Bank", gl_debit="Rent"
        )
        entries = _entries_for(db, "BankPurchase", pur.id)
        assert len(entries) == 1
        je = entries[0]
        assert je.description == f"Bank Purchase (ID: {pur.id})"
        rent = _acct(db, "Rent Expense")
        bank = _acct(db, "Bank")
        assert _line_tuples(db, je.id) == [
            (rent.id, 95.0, 0.0),
            (bank.id, 0.0, 95.0),
        ]


# ─── 5. post_expense ─────────────────────────────────────────────────────────


class TestPostExpenseCharacterization:
    @pytest.mark.parametrize(
        "category,expense_acct_name",
        [
            ("Rent", "Rent Expense"),
            ("Salary", "Salary Expense"),
            ("Utility", "Utility Expense"),
            ("Advertising", "Advertising Expense"),
            ("Fuel", "Fuel Expense"),
            ("Misc", "Office Expense"),
            ("other supplies", "Office Expense"),
        ],
    )
    def test_expense_category_debit_account(self, session, category, expense_acct_name):
        db, _cid = session
        exp = models.ExpenseRecord(
            date=POST_DATE,
            expense_type="General",
            category=category,
            amount=33.0,
            payment_method="Cash",
            company_id=_cid,
        )
        db.add(exp)
        db.commit()
        app.post_expense(
            db, exp.id, 33.0, POST_DATE, category, payment_method="Cash"
        )
        je = _entries_for(db, "Expense", exp.id)[0]
        debit = _acct(db, expense_acct_name)
        credit = _acct(db, "Cash")
        assert _line_tuples(db, je.id) == [
            (debit.id, 33.0, 0.0),
            (credit.id, 0.0, 33.0),
        ]
        assert je.description == f"{category} Expense (ID: {exp.id})"

    def test_bank_payment_path(self, session):
        db, _cid = session
        exp = models.ExpenseRecord(
            date=POST_DATE,
            expense_type="General",
            category="Office",
            amount=42.0,
            payment_method="Bank",
            company_id=_cid,
        )
        db.add(exp)
        db.commit()
        app.post_expense(
            db, exp.id, 42.0, POST_DATE, "Office", payment_method="Bank"
        )
        je = _entries_for(db, "Expense", exp.id)[0]
        office = _acct(db, "Office Expense")
        bank = _acct(db, "Bank")
        assert _line_tuples(db, je.id) == [
            (office.id, 42.0, 0.0),
            (bank.id, 0.0, 42.0),
        ]


# ─── 6. Entry-point errors (dedup, amount<=0) ────────────────────────────────


class TestPostingEntryPointErrors:
    def test_save_and_post_expense_zero_amount_cc_raises_company_card_error(self, session):
        """_save_and_post_expense_record catches ValueError only — CompanyCardError propagates."""
        db, cid = session
        _cc_card(db, cid)
        db.commit()
        record = models.ExpenseRecord(
            date=POST_DATE,
            expense_type="Expense",
            category="Office",
            description="Zero",
            amount=0.0,
            payment_method="Credit Card",
            company_id=cid,
        )
        with pytest.raises(CompanyCardError) as exc:
            app._save_and_post_expense_record(
                db,
                record,
                category="Office",
                payment_method="Credit Card",
            )
        assert str(exc.value) == CC_AMOUNT_MSG

    def test_post_expense_cc_duplicate_subledger_raises_company_card_error(self, session):
        """post_cc_subledger_charge errors are not wrapped in _sync — CompanyCardError propagates."""
        db, cid = session
        _cc_card(db, cid)
        exp = models.ExpenseRecord(
            date=POST_DATE,
            expense_type="Expense",
            category="Office",
            amount=30.0,
            payment_method="Credit Card",
            company_id=cid,
        )
        db.add(exp)
        db.commit()
        app.post_expense(
            db, exp.id, 30.0, POST_DATE, "Office", payment_method="Credit Card"
        )
        db.commit()
        with pytest.raises(CompanyCardError) as exc:
            app.post_expense(
                db, exp.id, 30.0, POST_DATE, "Office", payment_method="Credit Card"
            )
        assert CC_DEDUP_PREFIX in str(exc.value)
        assert cc_subledger_stmt_ref("Expense", exp.id) in str(exc.value)
