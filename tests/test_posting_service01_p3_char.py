"""POSTING-SERVICE-01 PS-P3-CHAR — void/reversal pre-extraction characterization.

Pins app.py behavior for reversal primitives and void_* entry points.
No extraction in this phase.
"""
from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app
from reconciliation.company_card import cc_subledger_stmt_ref
from registry.coa_seed import seed_chart_of_accounts_for_company
from registry.service import set_setting

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 6, 10)
VOID_REASON = "PS-P3-CHAR void characterization"
BSR_GUARD_MSG = "Statement-linked transactions must be unposted from Bank Reconciliation."


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
            name="P3 Char Co",
            slug="p3_char_co",
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


def _acct(session, name, currency=None):
    return app.get_account_by_name(session, name, currency=currency)


def _entries_for(session, ref_type, ref_id):
    return (
        session.query(models.JournalEntry)
        .filter_by(reference_type=ref_type, reference_id=ref_id)
        .order_by(models.JournalEntry.id)
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


def _reversals_for(session, original_entry_id):
    return (
        session.query(models.JournalEntry)
        .filter_by(reference_type="Reversal", reference_id=original_entry_id)
        .order_by(models.JournalEntry.id)
        .all()
    )


def _cc_card(session, company_id, *, balance=0.0):
    ba = models.BankAccount(
        name="Company Visa",
        currency="TRY",
        company_id=company_id,
        is_active=True,
        balance=balance,
        kind="credit_card",
    )
    session.add(ba)
    session.flush()
    return ba


def _vendor(session):
    v = models.Vendor(name="Vendor P3", is_active=True)
    session.add(v)
    session.flush()
    return v


def _bank_account(session, company_id, *, balance=1000.0):
    ba = models.BankAccount(
        name="Main Bank",
        currency="TRY",
        company_id=company_id,
        is_active=True,
        balance=balance,
        kind="bank",
    )
    session.add(ba)
    session.flush()
    return ba


# ─── 1. reverse_journal_entries_for ──────────────────────────────────────────


class TestReverseJournalEntriesFor:
    def test_multi_je_reference_creates_one_reversal_per_original(self, session):
        db, _cid = session
        office = _acct(db, "Office Expense")
        cash = _acct(db, "Cash")
        ref_id = 8801

        first = app.create_journal_entry(
            db, POST_DATE, "Expense slice A", "Expense", ref_id,
            [(office.id, 10.0, 0.0), (cash.id, 0.0, 10.0)],
        )
        second = app.create_journal_entry(
            db, POST_DATE, "Expense slice B", "Expense", ref_id,
            [(office.id, 15.0, 0.0), (cash.id, 0.0, 15.0)],
        )

        originals = _entries_for(db, "Expense", ref_id)
        assert len(originals) == 2

        app.reverse_journal_entries_for(db, "Expense", ref_id, VOID_REASON)

        for orig in (first, second):
            revs = _reversals_for(db, orig.id)
            assert len(revs) == 1
            rev = revs[0]
            assert rev.reference_type == "Reversal"
            assert rev.reference_id == orig.id
            assert rev.description == f"VOID: {orig.description} — {VOID_REASON}"
            assert _line_tuples(db, rev.id) == [
                (acct_id, cr, dr)
                for acct_id, dr, cr in _line_tuples(db, orig.id)
            ]

    def test_reversal_lines_swap_debit_and_credit(self, session):
        db, _cid = session
        rent = _acct(db, "Rent Expense")
        bank = _acct(db, "Bank")
        original = app.create_journal_entry(
            db, POST_DATE, "Single expense", "Expense", 8802,
            [(rent.id, 40.0, 0.0), (bank.id, 0.0, 40.0)],
        )
        app.reverse_journal_entries_for(db, "Expense", 8802, VOID_REASON)
        rev = _reversals_for(db, original.id)[0]
        assert _line_tuples(db, rev.id) == [
            (rent.id, 0.0, 40.0),
            (bank.id, 40.0, 0.0),
        ]


# ─── 2. void_expense ─────────────────────────────────────────────────────────


class TestVoidExpense:
    def test_marks_expense_void_and_reverses_gl(self, session):
        db, _cid = session
        exp = models.ExpenseRecord(
            date=POST_DATE,
            expense_type="General",
            category="Office",
            amount=55.0,
            payment_method="Cash",
            company_id=_cid,
        )
        db.add(exp)
        db.commit()
        app.post_expense(db, exp.id, 55.0, POST_DATE, "Office", payment_method="Cash")
        cash = _acct(db, "Cash")
        assert app.calculate_account_balance(db, cash) == pytest.approx(-55.0)

        assert app.void_expense(db, exp.id, VOID_REASON) is True
        db.refresh(exp)
        assert exp.is_void is True
        assert exp.void_reason == VOID_REASON
        assert exp.voided_at == datetime.date.today()
        assert app.calculate_account_balance(db, cash) == pytest.approx(0.0)

        orig = _entries_for(db, "Expense", exp.id)[0]
        assert len(_reversals_for(db, orig.id)) == 1

    def test_void_cc_expense_reverses_subledger_and_card_balance(self, session):
        db, cid = session
        card = _cc_card(db, cid)
        exp = models.ExpenseRecord(
            date=POST_DATE,
            expense_type="Expense",
            category="Office",
            amount=60.0,
            payment_method="Credit Card",
            company_id=cid,
        )
        db.add(exp)
        db.commit()
        app.post_expense(
            db, exp.id, 60.0, POST_DATE, "Office", payment_method="Credit Card"
        )
        db.commit()
        stmt_ref = cc_subledger_stmt_ref("Expense", exp.id)
        btxn = db.query(models.BankTransaction).filter_by(statement_ref=stmt_ref).one()
        assert card.balance == 60.0

        assert app.void_expense(db, exp.id, VOID_REASON) is True
        db.refresh(card)
        db.refresh(btxn)
        assert btxn.is_void is True
        assert btxn.void_reason == VOID_REASON
        assert card.balance == 0.0
        cc_gl = _acct(db, "Credit Card Payable")
        assert app.calculate_account_balance(db, cc_gl) == 0.0


# ─── 3. void_purchase ────────────────────────────────────────────────────────


class TestVoidPurchase:
    def test_void_credit_purchase_reverses_gl_and_voids_linked_payable(self, session):
        db, cid = session
        vendor = _vendor(db)
        pur = models.Purchase(
            date=POST_DATE,
            vendor_id=vendor.id,
            amount=100.0,
            purchase_type="Credit",
            gl_debit="Inventory",
            company_id=cid,
        )
        db.add(pur)
        db.commit()
        app.post_purchase(
            db, pur.id, 100.0, POST_DATE, purchase_type="Credit", gl_debit="Inventory"
        )
        payable = app._create_purchase_payable(db, pur)
        db.commit()

        inv = _acct(db, "Inventory")
        ap = _acct(db, "Accounts Payable")
        assert app.calculate_account_balance(db, inv) == pytest.approx(100.0)
        assert app.calculate_account_balance(db, ap) == pytest.approx(100.0)
        assert len(_entries_for(db, "PayableCreation", payable.id)) == 0

        assert app.void_purchase(db, pur.id, VOID_REASON) is True
        db.refresh(pur)
        db.refresh(payable)
        assert pur.is_void is True
        assert payable.is_void is True
        assert app.calculate_account_balance(db, inv) == pytest.approx(0.0)
        assert app.calculate_account_balance(db, ap) == pytest.approx(0.0)

        orig = _entries_for(db, "Purchase", pur.id)[0]
        assert len(_reversals_for(db, orig.id)) == 1

    def test_void_paid_linked_payable_reverses_payable_payment_gl(self, session):
        db, cid = session
        vendor = _vendor(db)
        pur = models.Purchase(
            date=POST_DATE,
            vendor_id=vendor.id,
            amount=80.0,
            purchase_type="Credit",
            gl_debit="Inventory",
            company_id=cid,
        )
        db.add(pur)
        db.commit()
        app.post_purchase(
            db, pur.id, 80.0, POST_DATE, purchase_type="Credit", gl_debit="Inventory"
        )
        payable = app._create_purchase_payable(db, pur)
        db.commit()
        app._apply_payable_payment_state(payable, 80.0)
        app.post_payable_payment(
            db, payable.id, 80.0, POST_DATE, payment_method="Cash"
        )
        db.commit()
        cash = _acct(db, "Cash")
        assert app.calculate_account_balance(db, cash) == pytest.approx(-80.0)

        assert app.void_purchase(db, pur.id, VOID_REASON) is True
        assert app.calculate_account_balance(db, cash) == pytest.approx(0.0)
        payment_entries = _entries_for(db, "PayablePayment", payable.id)
        assert len(payment_entries) == 1
        assert len(_reversals_for(db, payment_entries[0].id)) == 1


# ─── 4. void_payable ─────────────────────────────────────────────────────────


class TestVoidPayable:
    def test_void_standalone_payable_reverses_payable_creation(self, session):
        db, cid = session
        vendor = _vendor(db)
        payable = models.Payable(
            date=POST_DATE,
            vendor_id=vendor.id,
            amount=120.0,
            paid_amount=0.0,
            balance=120.0,
            due_date=POST_DATE,
            paid=False,
            expense_category="Rent",
            company_id=cid,
        )
        db.add(payable)
        db.commit()
        app.post_payable_creation(
            db, payable.id, 120.0, POST_DATE, expense_category="Rent"
        )
        rent = _acct(db, "Rent Expense")
        ap = _acct(db, "Accounts Payable")
        assert app.calculate_account_balance(db, rent) == pytest.approx(120.0)
        assert app.calculate_account_balance(db, ap) == pytest.approx(120.0)

        assert app.void_payable(db, payable.id, VOID_REASON) is True
        db.refresh(payable)
        assert payable.is_void is True
        assert app.calculate_account_balance(db, rent) == pytest.approx(0.0)
        assert app.calculate_account_balance(db, ap) == pytest.approx(0.0)
        creation = _entries_for(db, "PayableCreation", payable.id)[0]
        assert len(_reversals_for(db, creation.id)) == 1

    def test_void_payable_reverses_payable_payment_when_paid(self, session):
        db, cid = session
        vendor = _vendor(db)
        payable = models.Payable(
            date=POST_DATE,
            vendor_id=vendor.id,
            amount=90.0,
            paid_amount=0.0,
            balance=90.0,
            due_date=POST_DATE,
            paid=False,
            expense_category="Rent",
            company_id=cid,
        )
        db.add(payable)
        db.commit()
        app.post_payable_creation(
            db, payable.id, 90.0, POST_DATE, expense_category="Rent"
        )
        app.post_payable_payment(
            db, payable.id, 90.0, POST_DATE, payment_method="Cash"
        )
        db.commit()

        assert app.void_payable(db, payable.id, VOID_REASON) is True
        creation = _entries_for(db, "PayableCreation", payable.id)[0]
        payment = _entries_for(db, "PayablePayment", payable.id)[0]
        assert len(_reversals_for(db, creation.id)) == 1
        assert len(_reversals_for(db, payment.id)) == 1


# ─── 5. void_bank_transaction ────────────────────────────────────────────────


class TestVoidBankTransaction:
    def test_void_deposit_reverses_balance_and_marks_void(self, session):
        db, cid = session
        bank = _bank_account(db, cid, balance=1000.0)
        txn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=200.0,
            type="deposit",
            description="Test deposit",
            company_id=cid,
        )
        db.add(txn)
        bank.balance = 1200.0
        db.commit()
        app.post_bank_transaction(db, txn.id, 200.0, POST_DATE, "deposit")
        db.commit()

        assert app.void_bank_transaction(db, txn.id, VOID_REASON) is True
        db.refresh(bank)
        db.refresh(txn)
        assert txn.is_void is True
        assert txn.void_reason == VOID_REASON
        assert bank.balance == pytest.approx(1000.0)
        assert len(_reversals_for(db, _entries_for(db, "BankDeposit", txn.id)[0].id)) == 1

    def test_bsr_statement_ref_raises_value_error(self, session):
        db, cid = session
        bank = _bank_account(db, cid)
        txn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=50.0,
            type="withdrawal",
            description="Statement-linked",
            statement_ref="bsr:import-row-42",
            company_id=cid,
        )
        db.add(txn)
        db.commit()
        with pytest.raises(ValueError) as exc:
            app.void_bank_transaction(db, txn.id, VOID_REASON)
        assert str(exc.value) == BSR_GUARD_MSG
        db.refresh(txn)
        assert txn.is_void is False

    def test_card_sale_deposit_returns_false_without_voiding(self, session):
        db, cid = session
        bank = _bank_account(db, cid, balance=500.0)
        txn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=75.0,
            type="deposit",
            description="Card Sale INV-CC-001",
            company_id=cid,
        )
        db.add(txn)
        db.commit()
        balance_before = bank.balance
        assert app.void_bank_transaction(db, txn.id, VOID_REASON) is False
        db.refresh(txn)
        db.refresh(bank)
        assert txn.is_void is False
        assert bank.balance == balance_before


# ─── 6. Void commit / audit boundary ─────────────────────────────────────────


class TestVoidCommitAuditBoundary:
    def test_void_expense_commits_then_log_audit_commits_again(self, session):
        db, cid = session
        exp = models.ExpenseRecord(
            date=POST_DATE,
            expense_type="General",
            category="Office",
            amount=25.0,
            payment_method="Cash",
            company_id=cid,
        )
        db.add(exp)
        db.commit()
        app.post_expense(db, exp.id, 25.0, POST_DATE, "Office", payment_method="Cash")

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_expense(db, exp.id, VOID_REASON) is True
            # Reversal JE commit + void session.commit + log_audit commit
            assert mock_commit.call_count == 3

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="Void",
                entity_type="ExpenseRecord",
                entity_id=exp.id,
            )
            .one()
        )
        assert VOID_REASON in audit.description
        assert audit.performed_by == app._DEV_USER["username"]

    def test_void_purchase_writes_audit_log_after_commit(self, session):
        db, cid = session
        vendor = _vendor(db)
        pur = models.Purchase(
            date=POST_DATE,
            vendor_id=vendor.id,
            amount=50.0,
            purchase_type="Cash",
            gl_debit="Inventory",
            company_id=cid,
        )
        db.add(pur)
        db.commit()
        app.post_purchase(
            db, pur.id, 50.0, POST_DATE, purchase_type="Cash", gl_debit="Inventory"
        )

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_purchase(db, pur.id, VOID_REASON) is True
            # Purchase reversal JE commit + void session.commit + log_audit commit
            assert mock_commit.call_count == 3

        audit = (
            db.query(models.AuditLog)
            .filter_by(action="Void", entity_type="Purchase", entity_id=pur.id)
            .one()
        )
        assert f"Voided Purchase #{pur.id}" in audit.description
