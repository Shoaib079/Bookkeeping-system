"""POSTING-SERVICE-01 PS-P0 — characterization tests for app.py posting/void behavior.

Freezes current GL posting semantics before extraction to services/posting.py.
Tests assert existing behavior only; they must pass without refactoring posting code.
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
from registry.coa_seed import seed_chart_of_accounts_for_company

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 3, 15)
VOID_REASON = "PS-P0 characterization void"


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
            name="Posting Test Co",
            slug="posting_test_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        seed_chart_of_accounts_for_company(s, co.id)
        yield s


def _acct(session, name):
    return app.get_account_by_name(session, name)


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


def _make_sale(session, *, sale_type="Cash", amount=100.0):
    sale = models.Sale(
        date=POST_DATE,
        invoice_number=f"INV-{sale_type}-001",
        customer_name="Test Customer",
        description="Characterization sale",
        amount=amount,
        sale_type=sale_type,
        paid_amount=amount if sale_type != "Credit" else 0.0,
        balance=0.0 if sale_type != "Credit" else amount,
        due_date=POST_DATE + datetime.timedelta(days=30),
        status="Paid" if sale_type != "Credit" else "Outstanding",
    )
    session.add(sale)
    session.flush()
    return sale


def _make_expense(session, *, amount=75.0, category="Office", payment_method="Cash"):
    expense = models.ExpenseRecord(
        date=POST_DATE,
        expense_type="General",
        category=category,
        description="Characterization expense",
        amount=amount,
        payment_method=payment_method,
    )
    session.add(expense)
    session.flush()
    return expense


def _make_vendor(session):
    vendor = models.Vendor(name="Vendor A", is_active=True)
    session.add(vendor)
    session.flush()
    return vendor


def _make_purchase(session, vendor, *, amount=200.0, purchase_type="Credit"):
    purchase = models.Purchase(
        date=POST_DATE,
        vendor_id=vendor.id,
        purchase_number="PO-001",
        amount=amount,
        description="Characterization purchase",
        purchase_type=purchase_type,
        gl_debit="Inventory",
    )
    session.add(purchase)
    session.flush()
    return purchase


def _make_payable(session, vendor, *, amount=150.0):
    payable = models.Payable(
        date=POST_DATE,
        vendor_id=vendor.id,
        amount=amount,
        paid_amount=0.0,
        balance=amount,
        due_date=POST_DATE + datetime.timedelta(days=30),
        paid=False,
        description="Standalone payable",
        expense_category="Rent",
    )
    session.add(payable)
    session.flush()
    return payable


# ─── create_journal_entry core ───────────────────────────────────────────────


class TestCreateJournalEntryCore:
    def test_balanced_entry_persists_metadata_and_lines(self, session):
        cash = _acct(session, "Cash")
        revenue = _acct(session, "Sales Revenue")
        amount = 125.50

        entry = app.create_journal_entry(
            session,
            POST_DATE,
            "PS-P0 balanced characterization",
            "Characterization",
            42,
            [(cash.id, amount, 0.0), (revenue.id, 0.0, amount)],
        )

        assert entry.id is not None
        stored = session.get(models.JournalEntry, entry.id)
        assert stored.description == "PS-P0 balanced characterization"
        assert stored.reference_type == "Characterization"
        assert stored.reference_id == 42
        assert stored.entry_date == POST_DATE
        assert _line_tuples(session, entry.id) == [
            (cash.id, amount, 0.0),
            (revenue.id, 0.0, amount),
        ]

    def test_unbalanced_entry_raises_and_does_not_persist(self, session):
        cash = _acct(session, "Cash")
        revenue = _acct(session, "Sales Revenue")
        before = session.query(models.JournalEntry).count()

        with pytest.raises(ValueError, match="not balanced"):
            app.create_journal_entry(
                session,
                POST_DATE,
                "Unbalanced attempt",
                "Characterization",
                99,
                [(cash.id, 100.0, 0.0), (revenue.id, 0.0, 90.0)],
            )

        assert session.query(models.JournalEntry).count() == before

    def test_closed_period_blocks_posting(self, session):
        cash = _acct(session, "Cash")
        revenue = _acct(session, "Sales Revenue")
        period = models.FiscalPeriod(
            name="Mar 2026",
            start_date=datetime.date(2026, 3, 1),
            end_date=datetime.date(2026, 3, 31),
            is_closed=True,
            closed_at=datetime.date.today(),
        )
        session.add(period)
        session.commit()

        with pytest.raises(ValueError, match="closed"):
            app.create_journal_entry(
                session,
                POST_DATE,
                "Blocked by period",
                "Sale",
                None,
                [(cash.id, 50.0, 0.0), (revenue.id, 0.0, 50.0)],
            )


class TestBalanceCacheSemantics:
    def test_create_journal_entry_does_not_update_coa_balance_cache(self, session):
        cash = _acct(session, "Cash")
        revenue = _acct(session, "Sales Revenue")
        cached_before = cash.balance or 0.0

        app.create_journal_entry(
            session,
            POST_DATE,
            "Cache characterization",
            "Characterization",
            1,
            [(cash.id, 80.0, 0.0), (revenue.id, 0.0, 80.0)],
        )

        session.refresh(cash)
        assert cash.balance == cached_before
        assert app.calculate_account_balance(session, cash) == pytest.approx(80.0)

    def test_sync_account_balances_refreshes_cache_from_lines(self, session):
        cash = _acct(session, "Cash")
        revenue = _acct(session, "Sales Revenue")

        app.create_journal_entry(
            session,
            POST_DATE,
            "Sync characterization",
            "Characterization",
            2,
            [(cash.id, 60.0, 0.0), (revenue.id, 0.0, 60.0)],
        )
        session.refresh(cash)
        assert (cash.balance or 0.0) == pytest.approx(0.0)

        app.sync_account_balances(session)
        session.refresh(cash)
        assert cash.balance == pytest.approx(60.0)


# ─── post_* wrappers ───────────────────────────────────────────────────────────


class TestSalePostingVariants:
    def test_post_cash_sale(self, session):
        sale = _make_sale(session, sale_type="Cash", amount=250.0)
        session.commit()

        app.post_cash_sale(session, sale.id, 250.0, POST_DATE)

        entries = _entries_for(session, "CashSale", sale.id)
        assert len(entries) == 1
        je = entries[0]
        assert je.description == f"Cash Sale (ID: {sale.id})"
        cash = _acct(session, "Cash")
        revenue = _acct(session, "Sales Revenue")
        assert _line_tuples(session, je.id) == [
            (cash.id, 250.0, 0.0),
            (revenue.id, 0.0, 250.0),
        ]

    def test_post_card_sale_default_settlement_off(self, session):
        sale = _make_sale(session, sale_type="Card", amount=180.0)
        session.commit()

        app.post_card_sale(session, sale.id, 180.0, POST_DATE)

        entries = _entries_for(session, "CardSale", sale.id)
        assert len(entries) == 1
        je = entries[0]
        assert je.description == f"Card Sale (ID: {sale.id})"
        bank = _acct(session, "Bank")
        revenue = _acct(session, "Sales Revenue")
        assert _line_tuples(session, je.id) == [
            (bank.id, 180.0, 0.0),
            (revenue.id, 0.0, 180.0),
        ]

    def test_post_credit_sale(self, session):
        sale = _make_sale(session, sale_type="Credit", amount=320.0)
        session.commit()

        app.post_credit_sale(session, sale.id, 320.0, POST_DATE)

        entries = _entries_for(session, "CreditSale", sale.id)
        assert len(entries) == 1
        je = entries[0]
        assert je.description == f"Credit Sale (ID: {sale.id})"
        ar = _acct(session, "Accounts Receivable")
        revenue = _acct(session, "Sales Revenue")
        assert _line_tuples(session, je.id) == [
            (ar.id, 320.0, 0.0),
            (revenue.id, 0.0, 320.0),
        ]


class TestExpenseAndPurchasePosting:
    def test_post_expense_cash(self, session):
        expense = _make_expense(session, amount=75.0, category="Office")
        session.commit()

        app.post_expense(
            session, expense.id, 75.0, POST_DATE, "Office", payment_method="Cash"
        )

        entries = _entries_for(session, "Expense", expense.id)
        assert len(entries) == 1
        je = entries[0]
        assert je.description == f"Office Expense (ID: {expense.id})"
        office = _acct(session, "Office Expense")
        cash = _acct(session, "Cash")
        assert _line_tuples(session, je.id) == [
            (office.id, 75.0, 0.0),
            (cash.id, 0.0, 75.0),
        ]

    def test_post_credit_purchase(self, session):
        vendor = _make_vendor(session)
        purchase = _make_purchase(session, vendor, amount=200.0, purchase_type="Credit")
        session.commit()

        app.post_purchase(
            session,
            purchase.id,
            200.0,
            POST_DATE,
            purchase_type="Credit",
            gl_debit="Inventory",
        )

        entries = _entries_for(session, "Purchase", purchase.id)
        assert len(entries) == 1
        je = entries[0]
        assert je.description == f"Credit Purchase (ID: {purchase.id})"
        inventory = _acct(session, "Inventory")
        ap = _acct(session, "Accounts Payable")
        assert _line_tuples(session, je.id) == [
            (inventory.id, 200.0, 0.0),
            (ap.id, 0.0, 200.0),
        ]

    def test_post_payable_creation_and_payment(self, session):
        vendor = _make_vendor(session)
        payable = _make_payable(session, vendor, amount=150.0)
        session.commit()

        app.post_payable_creation(
            session, payable.id, 150.0, POST_DATE, expense_category="Rent"
        )
        creation_entries = _entries_for(session, "PayableCreation", payable.id)
        assert len(creation_entries) == 1
        creation = creation_entries[0]
        assert creation.description == (
            f"Payable Created (ID: {payable.id}) — Rent"
        )
        rent = _acct(session, "Rent Expense")
        ap = _acct(session, "Accounts Payable")
        assert _line_tuples(session, creation.id) == [
            (rent.id, 150.0, 0.0),
            (ap.id, 0.0, 150.0),
        ]

        app.post_payable_payment(
            session, payable.id, 150.0, POST_DATE, payment_method="Cash"
        )
        payment_entries = _entries_for(session, "PayablePayment", payable.id)
        assert len(payment_entries) == 1
        payment = payment_entries[0]
        assert payment.description == f"Payable Payment (ID: {payable.id})"
        cash = _acct(session, "Cash")
        assert _line_tuples(session, payment.id) == [
            (ap.id, 150.0, 0.0),
            (cash.id, 0.0, 150.0),
        ]


# ─── reversal / void ─────────────────────────────────────────────────────────


class TestReversalAndVoid:
    def test_create_reversing_journal_entry_swaps_debits_and_credits(self, session):
        cash = _acct(session, "Cash")
        revenue = _acct(session, "Sales Revenue")
        original = app.create_journal_entry(
            session,
            POST_DATE,
            "Original for reversal",
            "CashSale",
            501,
            [(cash.id, 90.0, 0.0), (revenue.id, 0.0, 90.0)],
        )

        reversal = app.create_reversing_journal_entry(
            session, original, "manual reversal test"
        )

        assert reversal is not None
        assert reversal.reference_type == "Reversal"
        assert reversal.reference_id == original.id
        assert reversal.description == (
            f"VOID: {original.description} — manual reversal test"
        )
        assert _line_tuples(session, reversal.id) == [
            (cash.id, 0.0, 90.0),
            (revenue.id, 90.0, 0.0),
        ]

    def test_void_sale_reverses_gl_and_marks_sale_void(self, session):
        sale = _make_sale(session, sale_type="Cash", amount=110.0)
        session.commit()
        app.post_cash_sale(session, sale.id, 110.0, POST_DATE)

        original_entries = _entries_for(session, "CashSale", sale.id)
        assert len(original_entries) == 1
        original_id = original_entries[0].id

        cash = _acct(session, "Cash")
        assert app.calculate_account_balance(session, cash) == pytest.approx(110.0)

        assert app.void_sale(session, sale.id, VOID_REASON) is True

        session.refresh(sale)
        assert sale.is_void is True
        assert sale.void_reason == VOID_REASON
        assert sale.status == "Void"

        reversals = (
            session.query(models.JournalEntry)
            .filter_by(reference_type="Reversal", reference_id=original_id)
            .all()
        )
        assert len(reversals) == 1
        assert app.calculate_account_balance(session, cash) == pytest.approx(0.0)

        # Original entry remains; reversal offsets it.
        assert session.get(models.JournalEntry, original_id) is not None
