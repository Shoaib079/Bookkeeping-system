"""POSTING-SERVICE-01 PS-P5-CHAR — self-contained PS-P5 pre-extraction characterization.

Pins post_receivable_payment, compute_sale_balance_status, void_inventory_transaction,
simple equity posters, and void_equity_movement before PS-P5 extraction.
No production changes.
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
from registry.coa_seed import seed_chart_of_accounts_for_company

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 6, 10)
VOID_REASON = "PS-P5-CHAR void pin"


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
            name="P5 Char Co",
            slug="p5_char_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        seed_chart_of_accounts_for_company(s, co.id)
        s.commit()
        yield s, co.id


def _acct(db, name, currency=None):
    return app.get_account_by_name(db, name, currency=currency)


def _entries_for(db, ref_type, ref_id):
    return (
        db.query(models.JournalEntry)
        .filter_by(reference_type=ref_type, reference_id=ref_id)
        .order_by(models.JournalEntry.id)
        .all()
    )


def _line_tuples(db, journal_entry_id):
    lines = (
        db.query(models.JournalEntryLine)
        .filter_by(journal_entry_id=journal_entry_id)
        .order_by(models.JournalEntryLine.id)
        .all()
    )
    return [(ln.account_id, ln.debit or 0.0, ln.credit or 0.0) for ln in lines]


def _reversals_for(db, original_entry_id):
    return (
        db.query(models.JournalEntry)
        .filter_by(reference_type="Reversal", reference_id=original_entry_id)
        .order_by(models.JournalEntry.id)
        .all()
    )


def _make_credit_sale(db, cid, *, amount=100.0, fx_rate=1.0):
    sale = models.Sale(
        date=POST_DATE,
        invoice_number="INV-P5-CHAR",
        customer_name="Credit Customer",
        description="PS-P5-CHAR credit sale",
        amount=amount,
        sale_type="Credit",
        paid_amount=0.0,
        balance=amount,
        due_date=POST_DATE + datetime.timedelta(days=30),
        status="Open",
        fx_rate=fx_rate,
        company_id=cid,
    )
    db.add(sale)
    db.commit()
    return sale


def _bank_account(db, cid, *, balance=1000.0):
    ba = models.BankAccount(
        name="Equity Bank",
        currency="TRY",
        company_id=cid,
        is_active=True,
        balance=balance,
        kind="bank",
    )
    db.add(ba)
    db.flush()
    return ba


class TestComputeSaleBalanceStatus:
    def test_paid_status_when_balance_zero(self):
        balance, status = app.compute_sale_balance_status(
            100.0, 100.0, POST_DATE + datetime.timedelta(days=30)
        )
        assert balance == pytest.approx(0.0)
        assert status == "Paid"

    def test_partial_status_when_some_paid_and_balance_remains(self):
        balance, status = app.compute_sale_balance_status(
            100.0, 40.0, POST_DATE + datetime.timedelta(days=30)
        )
        assert balance == pytest.approx(60.0)
        assert status == "Partial"

    def test_open_status_when_unpaid(self):
        balance, status = app.compute_sale_balance_status(
            100.0, 0.0, POST_DATE + datetime.timedelta(days=30)
        )
        assert balance == pytest.approx(100.0)
        assert status == "Open"

    def test_overdue_status_when_due_date_past_and_balance_remains(self):
        past_due = datetime.date.today() - datetime.timedelta(days=1)
        balance, status = app.compute_sale_balance_status(100.0, 25.0, past_due)
        assert balance == pytest.approx(75.0)
        assert status == "Overdue"


class TestPostReceivablePayment:
    def test_normal_payment_reduces_balance_and_posts_receivable_payment_je(self, session):
        db, cid = session
        sale = _make_credit_sale(db, cid, amount=100.0)
        app.post_credit_sale(db, sale.id, 100.0, POST_DATE)

        assert app.post_receivable_payment(
            db, sale.id, 40.0, POST_DATE, payment_method="Cash"
        ) is None

        db.refresh(sale)
        assert sale.paid_amount == pytest.approx(40.0)
        assert sale.balance == pytest.approx(60.0)
        assert sale.status == "Partial"

        entries = _entries_for(db, "ReceivablePayment", sale.id)
        assert len(entries) == 1
        cash = _acct(db, "Cash")
        ar = _acct(db, "Accounts Receivable")
        assert _line_tuples(db, entries[0].id) == [
            (cash.id, 40.0, 0.0),
            (ar.id, 0.0, 40.0),
        ]

    def test_full_payment_sets_paid_status(self, session):
        db, cid = session
        sale = _make_credit_sale(db, cid, amount=80.0)
        app.post_credit_sale(db, sale.id, 80.0, POST_DATE)

        assert app.post_receivable_payment(db, sale.id, 80.0, POST_DATE) is None

        db.refresh(sale)
        assert sale.paid_amount == pytest.approx(80.0)
        assert sale.balance == pytest.approx(0.0)
        assert sale.status == "Paid"

    def test_fx_gain_line_when_payment_rate_exceeds_booked_rate(self, session):
        db, cid = session
        sale = _make_credit_sale(db, cid, amount=100.0, fx_rate=1.2)
        app.post_credit_sale(db, sale.id, 100.0, POST_DATE)

        assert app.post_receivable_payment(
            db, sale.id, 50.0, POST_DATE, payment_fx_rate=1.5
        ) is None

        je = _entries_for(db, "ReceivablePayment", sale.id)[0]
        cash = _acct(db, "Cash")
        ar = _acct(db, "Accounts Receivable")
        fx_gain = _acct(db, "FX Gain")
        assert _line_tuples(db, je.id) == [
            (cash.id, 75.0, 0.0),
            (ar.id, 0.0, 60.0),
            (fx_gain.id, 0.0, 15.0),
        ]

    def test_fx_loss_line_when_payment_rate_below_booked_rate(self, session):
        db, cid = session
        sale = _make_credit_sale(db, cid, amount=100.0, fx_rate=1.5)
        app.post_credit_sale(db, sale.id, 100.0, POST_DATE)

        assert app.post_receivable_payment(
            db, sale.id, 50.0, POST_DATE, payment_fx_rate=1.2
        ) is None

        je = _entries_for(db, "ReceivablePayment", sale.id)[0]
        cash = _acct(db, "Cash")
        ar = _acct(db, "Accounts Receivable")
        fx_loss = _acct(db, "FX Loss")
        assert _line_tuples(db, je.id) == [
            (cash.id, 60.0, 0.0),
            (ar.id, 0.0, 75.0),
            (fx_loss.id, 15.0, 0.0),
        ]

    def test_posts_two_commits_kernel_plus_sale_mutation(self, session):
        db, cid = session
        sale = _make_credit_sale(db, cid, amount=50.0)
        app.post_credit_sale(db, sale.id, 50.0, POST_DATE)

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.post_receivable_payment(db, sale.id, 25.0, POST_DATE) is None
            assert mock_commit.call_count == 2

    def test_error_not_credit_sale_returns_string_without_mutation(self, session):
        db, cid = session
        cash_sale = models.Sale(
            date=POST_DATE,
            invoice_number="CASH-1",
            customer_name="Cash Customer",
            description="cash",
            amount=50.0,
            sale_type="Cash",
            paid_amount=50.0,
            balance=0.0,
            due_date=POST_DATE,
            status="Paid",
            company_id=cid,
        )
        db.add(cash_sale)
        db.commit()

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.post_receivable_payment(db, cash_sale.id, 10.0, POST_DATE)
            assert err == "Sale not found or is not a credit sale."
            assert mock_commit.call_count == 0

    def test_error_voided_sale_returns_string(self, session):
        db, cid = session
        sale = _make_credit_sale(db, cid)
        sale.is_void = True
        db.commit()

        err = app.post_receivable_payment(db, sale.id, 10.0, POST_DATE)
        assert err == "Cannot record payment on a voided sale."

    def test_error_already_fully_paid_returns_string(self, session):
        db, cid = session
        sale = _make_credit_sale(db, cid)
        sale.paid_amount = 100.0
        sale.balance = 0.0
        sale.status = "Paid"
        db.commit()

        err = app.post_receivable_payment(db, sale.id, 10.0, POST_DATE)
        assert err == "This invoice is already fully paid."

    def test_error_zero_payment_returns_string(self, session):
        db, cid = session
        sale = _make_credit_sale(db, cid)

        err = app.post_receivable_payment(db, sale.id, 0.0, POST_DATE)
        assert err == "Payment amount must be greater than zero."

    def test_error_exceeds_balance_returns_string(self, session):
        db, cid = session
        sale = _make_credit_sale(db, cid, amount=100.0)

        err = app.post_receivable_payment(db, sale.id, 150.0, POST_DATE)
        assert err == "Payment amount exceeds the remaining balance."
        db.refresh(sale)
        assert sale.paid_amount == pytest.approx(0.0)
        assert sale.balance == pytest.approx(100.0)


class TestVoidInventoryTransaction:
    def test_void_reverses_product_quantity(self, session):
        db, cid = session
        product = models.Product(name="Widget", quantity=15.0, company_id=cid)
        db.add(product)
        db.flush()
        txn = models.InventoryTransaction(
            product_id=product.id,
            date=POST_DATE,
            change=5.0,
            company_id=cid,
        )
        db.add(txn)
        db.commit()

        assert app.void_inventory_transaction(db, txn.id, VOID_REASON) is True

        db.refresh(product)
        assert product.quantity == pytest.approx(10.0)

    def test_void_sets_is_void_flags(self, session):
        db, cid = session
        product = models.Product(name="Gadget", quantity=8.0, company_id=cid)
        db.add(product)
        db.flush()
        txn = models.InventoryTransaction(
            product_id=product.id,
            date=POST_DATE,
            change=-2.0,
            company_id=cid,
        )
        db.add(txn)
        db.commit()

        assert app.void_inventory_transaction(db, txn.id, VOID_REASON) is True

        db.refresh(txn)
        assert txn.is_void is True
        assert txn.void_reason == VOID_REASON
        assert txn.voided_at == datetime.date.today()

    def test_void_posts_two_commits_and_audit_row(self, session):
        db, cid = session
        product = models.Product(name="Bolt", quantity=12.0, company_id=cid)
        db.add(product)
        db.flush()
        txn = models.InventoryTransaction(
            product_id=product.id,
            date=POST_DATE,
            change=2.0,
            company_id=cid,
        )
        db.add(txn)
        db.commit()

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_inventory_transaction(db, txn.id, VOID_REASON) is True
            assert mock_commit.call_count == 2

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="Void",
                entity_type="InventoryTransaction",
                entity_id=txn.id,
            )
            .one()
        )
        assert f"Voided inventory adjustment #{txn.id}" in audit.description
        assert VOID_REASON in audit.description
        assert audit.performed_by == app._DEV_USER["username"]


class TestSimpleEquityPosters:
    def test_post_capital_contribution_dr_bank_cr_owner_capital(self, session):
        db, cid = session
        bank = _bank_account(db, cid)
        btxn_id = 42

        app.post_capital_contribution(
            db, btxn_id, 500.0, POST_DATE, "Bank", notes="seed round"
        )

        entries = _entries_for(db, "CapitalContribution", btxn_id)
        assert len(entries) == 1
        bank_gl = _acct(db, "Bank")
        cap_gl = _acct(db, "Owner Capital")
        assert _line_tuples(db, entries[0].id) == [
            (bank_gl.id, 500.0, 0.0),
            (cap_gl.id, 0.0, 500.0),
        ]

    def test_post_owner_drawing_dr_owner_drawings_cr_cash(self, session):
        db, cid = session
        btxn_id = 7

        app.post_owner_drawing(db, btxn_id, 200.0, POST_DATE, "Cash")

        entries = _entries_for(db, "OwnerDrawing", btxn_id)
        assert len(entries) == 1
        draw_gl = _acct(db, "Owner Drawings")
        cash_gl = _acct(db, "Cash")
        assert _line_tuples(db, entries[0].id) == [
            (draw_gl.id, 200.0, 0.0),
            (cash_gl.id, 0.0, 200.0),
        ]

    def test_post_salary_dr_salary_expense_cr_cash(self, session):
        db, cid = session
        salary_id = 99

        app.post_salary(db, salary_id, 1500.0, POST_DATE)

        entries = _entries_for(db, "Salary", salary_id)
        assert len(entries) == 1
        salary_gl = _acct(db, "Salary Expense")
        cash_gl = _acct(db, "Cash")
        assert _line_tuples(db, entries[0].id) == [
            (salary_gl.id, 1500.0, 0.0),
            (cash_gl.id, 0.0, 1500.0),
        ]


class TestVoidEquityMovement:
    def test_void_reverses_gl_and_bank_balance_for_deposit(self, session):
        db, cid = session
        bank = _bank_account(db, cid, balance=1100.0)
        btxn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=100.0,
            type="deposit",
            description="Capital Contribution #1",
            company_id=cid,
        )
        db.add(btxn)
        db.commit()
        app.post_capital_contribution(db, btxn.id, 100.0, POST_DATE, "Bank")

        app.void_equity_movement(db, "CapitalContribution", btxn.id, VOID_REASON)

        db.refresh(bank)
        assert bank.balance == pytest.approx(1000.0)
        orig = _entries_for(db, "CapitalContribution", btxn.id)[0]
        assert len(_reversals_for(db, orig.id)) == 1

    def test_void_marks_linked_bank_transaction_void(self, session):
        db, cid = session
        bank = _bank_account(db, cid, balance=900.0)
        btxn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=50.0,
            type="withdrawal",
            description="Owner Drawing #3",
            company_id=cid,
        )
        db.add(btxn)
        db.commit()
        app.post_owner_drawing(db, btxn.id, 50.0, POST_DATE, "Bank")

        app.void_equity_movement(db, "OwnerDrawing", btxn.id, VOID_REASON)

        db.refresh(btxn)
        assert btxn.is_void is True
        assert btxn.void_reason == VOID_REASON

    def test_void_posts_three_commits_and_audit_row(self, session):
        db, cid = session
        bank = _bank_account(db, cid, balance=1050.0)
        btxn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=50.0,
            type="deposit",
            description="Capital Contribution #9",
            company_id=cid,
        )
        db.add(btxn)
        db.commit()
        app.post_capital_contribution(db, btxn.id, 50.0, POST_DATE, "Bank")

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            app.void_equity_movement(db, "CapitalContribution", btxn.id, VOID_REASON)
            assert mock_commit.call_count == 3

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="Void",
                entity_type="EquityMovement",
                entity_id=btxn.id,
            )
            .one()
        )
        assert f"Voided CapitalContribution #{btxn.id}" in audit.description
        assert VOID_REASON in audit.description
        assert audit.performed_by == app._DEV_USER["username"]
