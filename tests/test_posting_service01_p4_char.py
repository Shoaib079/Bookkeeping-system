"""POSTING-SERVICE-01 PS-P4-CHAR — banking family pre-extraction characterization.

Pins post_bank_transaction, post_bank_transfer, and void_bank_transaction
behavior before PS-P4 extraction. No production changes.
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
VOID_REASON = "PS-P4-CHAR void_bank_transaction pin"
BSR_GUARD_MSG = (
    "Statement-linked transactions must be unposted from Bank Reconciliation."
)


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
            name="P4 Char Co",
            slug="p4_char_co",
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


def _bank_account(db, cid, name="Main Bank", *, balance=1000.0):
    ba = models.BankAccount(
        name=name,
        currency="TRY",
        company_id=cid,
        is_active=True,
        balance=balance,
        kind="bank",
    )
    db.add(ba)
    db.flush()
    return ba


def _transfer_pair(db, cid, src_name, dest_name, amount, notes="xfer notes"):
    src = _bank_account(db, cid, name=src_name, balance=500.0)
    dest = _bank_account(db, cid, name=dest_name, balance=200.0)
    src.balance = 400.0
    dest.balance = 300.0
    src_txn = models.BankTransaction(
        account_id=src.id,
        date=POST_DATE,
        amount=amount,
        type="transfer",
        description=notes,
        company_id=cid,
    )
    dest_txn = models.BankTransaction(
        account_id=dest.id,
        date=POST_DATE,
        amount=amount,
        type="transfer",
        description=f"Transfer from {src.name}: {notes}",
        company_id=cid,
    )
    db.add_all([src_txn, dest_txn])
    db.commit()
    return src, dest, src_txn, dest_txn


class TestPostBankTransaction:
    def test_deposit_posts_bank_deposit_je_dr_bank_cr_cash(self, session):
        db, cid = session
        bank = _bank_account(db, cid)
        txn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=150.0,
            type="deposit",
            description="Deposit pin",
            company_id=cid,
        )
        db.add(txn)
        db.commit()

        app.post_bank_transaction(db, txn.id, 150.0, POST_DATE, "deposit")

        entries = _entries_for(db, "BankDeposit", txn.id)
        assert len(entries) == 1
        cash = _acct(db, "Cash")
        bank_gl = _acct(db, "Bank")
        assert _line_tuples(db, entries[0].id) == [
            (bank_gl.id, 150.0, 0.0),
            (cash.id, 0.0, 150.0),
        ]

    def test_withdrawal_posts_bank_withdrawal_je_dr_cash_cr_bank(self, session):
        db, cid = session
        bank = _bank_account(db, cid)
        txn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=75.0,
            type="withdrawal",
            description="Withdrawal pin",
            company_id=cid,
        )
        db.add(txn)
        db.commit()

        app.post_bank_transaction(db, txn.id, 75.0, POST_DATE, "withdrawal")

        entries = _entries_for(db, "BankWithdrawal", txn.id)
        assert len(entries) == 1
        cash = _acct(db, "Cash")
        bank_gl = _acct(db, "Bank")
        assert _line_tuples(db, entries[0].id) == [
            (cash.id, 75.0, 0.0),
            (bank_gl.id, 0.0, 75.0),
        ]

    def test_currency_threads_to_matching_gl_accounts(self, session):
        db, cid = session
        bank = _bank_account(db, cid)
        txn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=60.0,
            type="deposit",
            description="USD deposit",
            company_id=cid,
        )
        db.add(txn)
        db.commit()

        app.post_bank_transaction(
            db, txn.id, 60.0, POST_DATE, "deposit", currency="USD"
        )

        je = _entries_for(db, "BankDeposit", txn.id)[0]
        cash_usd = _acct(db, "Cash", currency="USD")
        bank_usd = _acct(db, "Bank", currency="USD")
        assert _line_tuples(db, je.id) == [
            (bank_usd.id, 60.0, 0.0),
            (cash_usd.id, 0.0, 60.0),
        ]


class TestPostBankTransfer:
    def test_cross_gl_transfer_posts_dr_dest_cr_src(self, session):
        db, cid = session
        src, dest, src_txn, _dest_txn = _transfer_pair(
            db, cid, "Office Cash", "Main Bank", 100.0
        )

        app.post_bank_transfer(
            db, src_txn.id, 100.0, POST_DATE, src.name, dest.name
        )

        entries = _entries_for(db, "BankTransfer", src_txn.id)
        assert len(entries) == 1
        cash_gl = _acct(db, "Cash")
        bank_gl = _acct(db, "Bank")
        assert _line_tuples(db, entries[0].id) == [
            (bank_gl.id, 100.0, 0.0),
            (cash_gl.id, 0.0, 100.0),
        ]

    def test_same_gl_transfer_is_no_op_without_je_or_commit(self, session):
        db, cid = session
        src = _bank_account(db, cid, name="Bank A")
        dest = _bank_account(db, cid, name="Bank B")
        txn = models.BankTransaction(
            account_id=src.id,
            date=POST_DATE,
            amount=50.0,
            type="transfer",
            description="internal",
            company_id=cid,
        )
        db.add(txn)
        db.commit()
        before = db.query(models.JournalEntry).count()

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            app.post_bank_transfer(
                db, txn.id, 50.0, POST_DATE, src.name, dest.name
            )
            assert mock_commit.call_count == 0

        assert db.query(models.JournalEntry).count() == before
        assert _entries_for(db, "BankTransfer", txn.id) == []


class TestVoidBankTransactionWithdrawal:
    def test_void_withdrawal_reverses_balance_and_bank_withdrawal_gl(self, session):
        db, cid = session
        bank = _bank_account(db, cid, balance=900.0)
        txn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=50.0,
            type="withdrawal",
            description="Withdraw to cash",
            company_id=cid,
        )
        db.add(txn)
        bank.balance = 850.0
        db.commit()
        app.post_bank_transaction(db, txn.id, 50.0, POST_DATE, "withdrawal")

        assert app.void_bank_transaction(db, txn.id, VOID_REASON) is True
        db.refresh(bank)
        db.refresh(txn)
        assert txn.is_void is True
        assert bank.balance == pytest.approx(900.0)
        orig = _entries_for(db, "BankWithdrawal", txn.id)[0]
        assert len(_reversals_for(db, orig.id)) == 1


class TestVoidBankTransactionTransferSource:
    def test_void_source_restores_balance_and_cascades_paired_destination(self, session):
        db, cid = session
        src, dest, src_txn, dest_txn = _transfer_pair(
            db, cid, "Office Cash", "Main Bank", 100.0, notes="cascade pin"
        )
        app.post_bank_transfer(
            db, src_txn.id, 100.0, POST_DATE, src.name, dest.name
        )

        assert app.void_bank_transaction(db, src_txn.id, VOID_REASON) is True

        db.refresh(src)
        db.refresh(dest)
        db.refresh(src_txn)
        db.refresh(dest_txn)
        assert src.balance == pytest.approx(500.0)
        assert dest.balance == pytest.approx(200.0)
        assert src_txn.is_void is True
        assert dest_txn.is_void is True
        assert dest_txn.void_reason == (
            f"Paired with voided transfer TXN#{src_txn.id}: {VOID_REASON}"
        )
        orig = _entries_for(db, "BankTransfer", src_txn.id)[0]
        assert len(_reversals_for(db, orig.id)) == 1


class TestVoidBankTransactionTransferDestination:
    def test_void_destination_reverses_balance_only_without_cascade(self, session):
        db, cid = session
        src, dest, src_txn, dest_txn = _transfer_pair(
            db, cid, "Office Cash", "Main Bank", 80.0, notes="dest leg pin"
        )
        app.post_bank_transfer(
            db, src_txn.id, 80.0, POST_DATE, src.name, dest.name
        )

        assert app.void_bank_transaction(db, dest_txn.id, VOID_REASON) is True

        db.refresh(src)
        db.refresh(dest)
        db.refresh(src_txn)
        db.refresh(dest_txn)
        # Destination leg: balance -= amount (no cascade to source).
        assert dest.balance == pytest.approx(220.0)
        assert src.balance == pytest.approx(400.0)
        assert dest_txn.is_void is True
        assert src_txn.is_void is False


class TestVoidBankTransactionGuards:
    def test_capital_contribution_description_returns_false(self, session):
        db, cid = session
        bank = _bank_account(db, cid)
        txn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=1000.0,
            type="deposit",
            description="Capital Contribution #42",
            company_id=cid,
        )
        db.add(txn)
        db.commit()
        balance_before = bank.balance

        assert app.void_bank_transaction(db, txn.id, VOID_REASON) is False
        db.refresh(txn)
        assert txn.is_void is False
        assert bank.balance == balance_before

    def test_owner_drawing_description_returns_false(self, session):
        db, cid = session
        bank = _bank_account(db, cid)
        txn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=500.0,
            type="withdrawal",
            description="Owner Drawing #7",
            company_id=cid,
        )
        db.add(txn)
        db.commit()
        balance_before = bank.balance

        assert app.void_bank_transaction(db, txn.id, VOID_REASON) is False
        db.refresh(txn)
        assert txn.is_void is False
        assert bank.balance == balance_before


class TestVoidBankTransactionCommitAudit:
    def test_void_deposit_posts_three_commits_and_audit_row(self, session):
        db, cid = session
        bank = _bank_account(db, cid, balance=1000.0)
        txn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=200.0,
            type="deposit",
            description="Commit pin deposit",
            company_id=cid,
        )
        db.add(txn)
        bank.balance = 1200.0
        db.commit()
        app.post_bank_transaction(db, txn.id, 200.0, POST_DATE, "deposit")

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_bank_transaction(db, txn.id, VOID_REASON) is True
            assert mock_commit.call_count == 3

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="Void",
                entity_type="BankTransaction",
                entity_id=txn.id,
            )
            .one()
        )
        assert f"Voided Bank Transaction #{txn.id}" in audit.description
        assert VOID_REASON in audit.description
        assert audit.performed_by == app._DEV_USER["username"]

    def test_void_withdrawal_posts_three_commits(self, session):
        db, cid = session
        bank = _bank_account(db, cid, balance=900.0)
        txn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=50.0,
            type="withdrawal",
            description="Commit pin withdrawal",
            company_id=cid,
        )
        db.add(txn)
        bank.balance = 850.0
        db.commit()
        app.post_bank_transaction(db, txn.id, 50.0, POST_DATE, "withdrawal")

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_bank_transaction(db, txn.id, VOID_REASON) is True
            assert mock_commit.call_count == 3

    def test_void_transfer_source_cross_gl_posts_three_commits(self, session):
        db, cid = session
        src, dest, src_txn, _dest_txn = _transfer_pair(
            db, cid, "Office Cash", "Main Bank", 100.0
        )
        app.post_bank_transfer(
            db, src_txn.id, 100.0, POST_DATE, src.name, dest.name
        )

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_bank_transaction(db, src_txn.id, VOID_REASON) is True
            assert mock_commit.call_count == 3
