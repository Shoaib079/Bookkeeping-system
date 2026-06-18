"""FASTAPI-P0.5d-S7 + PRODUCTION-HARDENING-01-PH02 — manual bank transaction boundary commit."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event as sa_event, func
from sqlalchemy.orm import sessionmaker

import app
import models
from db import Base
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import audit as audit_svc
from services import commit_modes
from services.commit_modes import CommitMode, POST_BANK_TRANSACTION_FAMILY
from services.write_banking import create_manual_bank_transaction
from tests.helpers.commit_parity import (
    BANKING_TABLES,
    assert_persisted_state_equal,
    audit_row_tuples,
    bank_txn_row_tuples,
    dual_run_parity,
    journal_line_tuples,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 12, 3)
AMOUNT = 350.0
CURRENCY = "TRY"
PERFORMED_BY = "admin"
NOTES = "PH-02 bank boundary pin"


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


@pytest.fixture(autouse=True)
def _reset_commit_modes():
    commit_modes.reset_commit_modes_for_tests()
    yield
    commit_modes.reset_commit_modes_for_tests()


@pytest.fixture(autouse=True)
def _clear_streamlit_state():
    sys.modules["streamlit"].session_state.clear()
    _seed_dev_auth_user()
    yield
    sys.modules["streamlit"].session_state.clear()


def _make_engine_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        app._stamp_company_id_on_new_objects(sess, ctx, instances)

    return engine, Session


def _seed_company_session(Session):
    sess = Session()
    co = models.Company(
        name="PH02 Banking Co",
        slug="ph02_banking_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    sess.add(co)
    sess.flush()
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    seed_chart_of_accounts_for_company(sess, co.id)
    bank = models.BankAccount(
        name="Main Bank",
        currency=CURRENCY,
        company_id=co.id,
        is_active=True,
        balance=5000.0,
        kind="bank",
    )
    cash = models.BankAccount(
        name="Office Cash",
        currency=CURRENCY,
        company_id=co.id,
        is_active=True,
        balance=1000.0,
        kind="bank",
    )
    sess.add_all([bank, cash])
    sess.commit()
    return sess, co.id


def _bank_env(sess, cid):
    bank = (
        sess.query(models.BankAccount)
        .filter_by(company_id=cid, name="Main Bank")
        .one()
    )
    cash = (
        sess.query(models.BankAccount)
        .filter_by(company_id=cid, name="Office Cash")
        .one()
    )
    return {"bank_id": bank.id, "cash_id": cash.id, "bank": bank}


def _manual_deposit(sess, cid, env):
    create_manual_bank_transaction(
        sess,
        company_id=cid,
        performed_by=PERFORMED_BY,
        entry_date=POST_DATE,
        amount=AMOUNT,
        transaction_type="deposit",
        bank_account_id=env["bank_id"],
        currency=CURRENCY,
        notes=NOTES,
    )


def _manual_withdrawal(sess, cid, env):
    create_manual_bank_transaction(
        sess,
        company_id=cid,
        performed_by=PERFORMED_BY,
        entry_date=POST_DATE,
        amount=AMOUNT,
        transaction_type="withdrawal",
        bank_account_id=env["bank_id"],
        currency=CURRENCY,
        notes=NOTES,
    )


def _manual_deposit_boundary(sess, cid, env):
    commit_modes.set_commit_mode_for_tests(
        POST_BANK_TRANSACTION_FAMILY, CommitMode.BOUNDARY
    )
    _manual_deposit(sess, cid, env)


def _manual_withdrawal_boundary(sess, cid, env):
    commit_modes.set_commit_mode_for_tests(
        POST_BANK_TRANSACTION_FAMILY, CommitMode.BOUNDARY
    )
    _manual_withdrawal(sess, cid, env)


class TestManualBankTransactionDefaultInternal:
    def test_deposit_write_service_multiple_internal_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _bank_env(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _manual_deposit(sess, cid, env)
            assert mock_commit.call_count == 3

    def test_withdrawal_write_service_multiple_internal_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _bank_env(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _manual_withdrawal(sess, cid, env)
            assert mock_commit.call_count == 3


class TestManualBankTransactionBoundaryMode:
    def test_deposit_boundary_one_commit(self):
        commit_modes.set_commit_mode_for_tests(
            POST_BANK_TRANSACTION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _bank_env(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _manual_deposit(sess, cid, env)
            assert mock_commit.call_count == 1

    def test_withdrawal_boundary_one_commit(self):
        commit_modes.set_commit_mode_for_tests(
            POST_BANK_TRANSACTION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _bank_env(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _manual_withdrawal(sess, cid, env)
            assert mock_commit.call_count == 1


class TestManualBankTransactionDualRunParity:
    @pytest.mark.parametrize(
        "internal_runner,boundary_runner,txn_type",
        [
            (_manual_deposit, _manual_deposit_boundary, "deposit"),
            (_manual_withdrawal, _manual_withdrawal_boundary, "withdrawal"),
        ],
        ids=["deposit", "withdrawal"],
    )
    def test_internal_vs_boundary_persisted_state_identical(
        self, internal_runner, boundary_runner, txn_type
    ):
        def factory_session_only():
            _, Session = _make_engine_session()
            sess, cid = _seed_company_session(Session)
            return sess

        def run(sess, runner):
            cid = sess.query(models.Company).one().id
            env = _bank_env(sess, cid)
            runner(sess, cid, env)

        left, right = dual_run_parity(
            session_factory=factory_session_only,
            internal_runner=lambda s: run(s, internal_runner),
            boundary_runner=lambda s: run(s, boundary_runner),
            tables=BANKING_TABLES,
            snapshot_kwargs={
                "include_sale_rows": False,
                "include_bank_txn_rows": True,
            },
        )
        assert_persisted_state_equal(left, right)
        assert left["counts"]["journal_entries"] == 1
        assert left["counts"]["audit_log"] == 1
        assert left["counts"]["bank_transactions"] == 1
        assert left["bank_txns"][0][3] == txn_type

    def test_deposit_gl_lines_match(self):
        commit_modes.set_commit_mode_for_tests(
            POST_BANK_TRANSACTION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _bank_env(sess, cid)
        _manual_deposit(sess, cid, env)
        txn = sess.query(models.BankTransaction).one()
        assert (
            sess.query(models.JournalEntry)
            .filter_by(reference_type="BankDeposit", reference_id=txn.id)
            .one()
        )
        lines = [
            (account_id, debit, credit)
            for _je_id, account_id, debit, credit in journal_line_tuples(sess)
        ]
        from services import posting

        bank_gl = posting.get_account_by_name(sess, "Bank", company_id=cid)
        cash_gl = posting.get_account_by_name(sess, "Cash", company_id=cid)
        assert lines == [(bank_gl.id, AMOUNT, 0.0), (cash_gl.id, 0.0, AMOUNT)]


class TestManualBankTransactionBoundaryRollback:
    def test_closed_period_leaves_no_bank_rows(self):
        commit_modes.set_commit_mode_for_tests(
            POST_BANK_TRANSACTION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _bank_env(sess, cid)
        sess.add(
            models.FiscalPeriod(
                name="Closed Dec 2026",
                start_date=POST_DATE,
                end_date=POST_DATE,
                is_closed=True,
                closed_at=POST_DATE,
                company_id=cid,
            )
        )
        sess.commit()
        initial_bank_balance = env["bank"].balance

        with pytest.raises(ValueError):
            _manual_deposit(sess, cid, env)

        assert sess.query(func.count()).select_from(models.BankTransaction).scalar() == 0
        assert (
            sess.query(func.count())
            .select_from(models.JournalEntry)
            .filter_by(reference_type="BankDeposit")
            .scalar()
            == 0
        )
        assert sess.query(func.count()).select_from(models.AuditLog).filter_by(
            entity_type=audit_svc.ENTITY_BANK_TRANSACTION
        ).scalar() == 0
        bank = sess.get(models.BankAccount, env["bank_id"])
        assert bank.balance == pytest.approx(initial_bank_balance)


class TestManualBankTransactionAuditAtomic:
    def test_deposit_audit_row_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(
            POST_BANK_TRANSACTION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _bank_env(sess, cid)
        _manual_deposit(sess, cid, env)
        txn = sess.query(models.BankTransaction).one()
        assert audit_row_tuples(sess) == [
            (
                "Create",
                audit_svc.ENTITY_BANK_TRANSACTION,
                txn.id,
                f"Bank Deposit {AMOUNT:,.2f} {CURRENCY} — Main Bank",
                PERFORMED_BY,
                cid,
            )
        ]

    def test_bank_txn_fingerprint_stable(self):
        commit_modes.set_commit_mode_for_tests(
            POST_BANK_TRANSACTION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _bank_env(sess, cid)
        _manual_deposit(sess, cid, env)
        rows = bank_txn_row_tuples(sess)
        assert len(rows) == 1
        assert rows[0][3] == "deposit"
        assert rows[0][2] == pytest.approx(AMOUNT)
