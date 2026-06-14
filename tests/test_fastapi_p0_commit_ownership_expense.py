"""FASTAPI-P0.5d-S2 — boundary commit for post_expense / Add Transaction expense save."""

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
from registry.service import set_setting
from services import audit as audit_svc
from services import commit_modes, posting
from services.commit_modes import CommitMode, POST_EXPENSE_FAMILY
from services.unit_of_work import boundary_commit_scope
from tests.helpers.commit_parity import (
    EXPENSE_TABLES,
    assert_persisted_state_equal,
    audit_row_tuples,
    bank_txn_row_tuples,
    dual_run_parity,
    expense_row_tuples,
    journal_line_tuples,
    persisted_state_snapshot,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 8, 10)
AMOUNT = 120.0
CATEGORY = "Office"
AUDIT_DESC = f"{CATEGORY} expense · {AMOUNT:,.2f} TRY"
PERFORMED_BY = "expense_parity_tester"


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


def _seed_company_session(Session, *, cc_card: bool = False):
    sess = Session()
    co = models.Company(
        name="P05d Expense Co",
        slug="p05d_expense_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    sess.add(co)
    sess.flush()
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    seed_chart_of_accounts_for_company(sess, co.id)
    sess.add(
        models.BankAccount(
            name="Main Bank",
            currency="TRY",
            company_id=co.id,
            is_active=True,
            balance=5000.0,
            kind="bank",
        )
    )
    if cc_card:
        set_setting(sess, "banking.company_card_enabled", True, company_id=co.id)
        sess.add(
            models.BankAccount(
                name="Company Visa",
                currency="TRY",
                company_id=co.id,
                is_active=True,
                balance=0.0,
                kind="credit_card",
            )
        )
    sess.commit()
    return sess, co.id


def _expense_draft(cid: int, *, payment_method: str = "Cash") -> models.ExpenseRecord:
    return models.ExpenseRecord(
        date=POST_DATE,
        expense_type=CATEGORY,
        category=CATEGORY,
        description="P05d expense boundary pin",
        amount=AMOUNT,
        payment_method=payment_method,
        gross_salary=AMOUNT,
        deductions=0.0,
        net_salary=AMOUNT,
        currency="TRY",
        fx_rate=1.0,
        native_amount=AMOUNT,
        company_id=cid,
    )


def _log_expense_audit(sess, record_id: int, cid: int):
    audit_svc.record_audit(
        sess,
        action=audit_svc.ACTION_CREATE,
        entity_type=audit_svc.ENTITY_EXPENSE_RECORD,
        entity_id=record_id,
        description=AUDIT_DESC,
        performed_by=PERFORMED_BY,
        company_id=cid,
    )


def _cash_expense_internal(sess, cid):
    record = _expense_draft(cid, payment_method="Cash")
    ok, err = app._save_and_post_expense_record(
        sess, record, category=CATEGORY, payment_method="Cash"
    )
    assert ok, err
    _log_expense_audit(sess, record.id, cid)
    return record


def _cash_expense_boundary(sess, cid):
    record = _expense_draft(cid, payment_method="Cash")
    with boundary_commit_scope(sess, POST_EXPENSE_FAMILY):
        ok, err = app._save_and_post_expense_record(
            sess, record, category=CATEGORY, payment_method="Cash"
        )
        assert ok, err
        _log_expense_audit(sess, record.id, cid)
    return record


def _bank_expense_internal(sess, cid):
    record = _expense_draft(cid, payment_method="Bank")
    ok, err = app._save_and_post_expense_record(
        sess, record, category=CATEGORY, payment_method="Bank"
    )
    assert ok, err
    bank_accounts = sess.query(models.BankAccount).filter_by(company_id=cid).all()
    app._record_named_bank_movement(
        sess,
        bank_accounts,
        "Main Bank",
        amount=AMOUNT,
        date=POST_DATE,
        description=f"Expense EXP#{record.id} — {CATEGORY}",
        txn_type="withdrawal",
    )
    sess.commit()
    _log_expense_audit(sess, record.id, cid)
    return record


def _bank_expense_boundary(sess, cid):
    record = _expense_draft(cid, payment_method="Bank")
    bank_accounts = sess.query(models.BankAccount).filter_by(company_id=cid).all()
    with boundary_commit_scope(sess, POST_EXPENSE_FAMILY):
        ok, err = app._save_and_post_expense_record(
            sess, record, category=CATEGORY, payment_method="Bank"
        )
        assert ok, err
        app._record_named_bank_movement(
            sess,
            bank_accounts,
            "Main Bank",
            amount=AMOUNT,
            date=POST_DATE,
            description=f"Expense EXP#{record.id} — {CATEGORY}",
            txn_type="withdrawal",
        )
        _log_expense_audit(sess, record.id, cid)
    return record


def _cc_expense_internal(sess, cid):
    record = _expense_draft(cid, payment_method="Credit Card")
    ok, err = app._save_and_post_expense_record(
        sess,
        record,
        category=CATEGORY,
        payment_method="Credit Card",
    )
    assert ok, err
    _log_expense_audit(sess, record.id, cid)
    return record


def _cc_expense_boundary(sess, cid):
    record = _expense_draft(cid, payment_method="Credit Card")
    with boundary_commit_scope(sess, POST_EXPENSE_FAMILY):
        ok, err = app._save_and_post_expense_record(
            sess,
            record,
            category=CATEGORY,
            payment_method="Credit Card",
        )
        assert ok, err
        _log_expense_audit(sess, record.id, cid)
    return record


def _expense_snapshot(sess):
    return persisted_state_snapshot(
        sess,
        tables=EXPENSE_TABLES,
        include_sale_rows=False,
        include_expense_rows=True,
        include_bank_txn_rows=True,
    )


class TestPostExpenseDefaultInternal:
    def test_post_expense_still_one_internal_commit(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        record = _expense_draft(cid)
        sess.add(record)
        sess.commit()
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            posting.post_expense(
                sess, record.id, AMOUNT, POST_DATE, CATEGORY,
                payment_method="Cash", company_id=cid,
            )
            assert mock_commit.call_count == 1

    def test_save_and_post_expense_internal_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        record = _expense_draft(cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            ok, err = app._save_and_post_expense_record(
                sess, record, category=CATEGORY, payment_method="Cash"
            )
            assert ok, err
            assert mock_commit.call_count >= 1


class TestPostExpenseBoundaryMode:
    def test_boundary_flow_has_one_boundary_commit_cash(self):
        commit_modes.set_commit_mode_for_tests(POST_EXPENSE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _cash_expense_boundary(sess, cid)
            assert mock_commit.call_count == 1

    def test_kernel_and_audit_flush_inside_boundary_scope(self):
        commit_modes.set_commit_mode_for_tests(POST_EXPENSE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        record = _expense_draft(cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            with patch.object(sess, "flush", wraps=sess.flush) as mock_flush:
                with boundary_commit_scope(sess, POST_EXPENSE_FAMILY):
                    ok, err = app._save_and_post_expense_record(
                        sess, record, category=CATEGORY, payment_method="Cash"
                    )
                    assert ok, err
                    _log_expense_audit(sess, record.id, cid)
                assert mock_commit.call_count == 1
                assert mock_flush.call_count >= 2


class TestPostExpenseDualRunParity:
    @pytest.mark.parametrize(
        "internal_runner,boundary_runner",
        [
            (_cash_expense_internal, _cash_expense_boundary),
            (_bank_expense_internal, _bank_expense_boundary),
            (_cc_expense_internal, _cc_expense_boundary),
        ],
        ids=["cash", "bank", "company_cc"],
    )
    def test_internal_vs_boundary_persisted_state_identical(
        self, internal_runner, boundary_runner
    ):
        cc_card = internal_runner is _cc_expense_internal

        def factory():
            _, Session = _make_engine_session()
            sess, _cid = _seed_company_session(Session, cc_card=cc_card)
            return sess

        def run_internal(sess):
            commit_modes.reset_commit_modes_for_tests()
            cid = sess.query(models.Company).one().id
            internal_runner(sess, cid)

        def run_boundary(sess):
            commit_modes.set_commit_mode_for_tests(
                POST_EXPENSE_FAMILY, CommitMode.BOUNDARY
            )
            cid = sess.query(models.Company).one().id
            boundary_runner(sess, cid)

        left, right = dual_run_parity(
            session_factory=factory,
            internal_runner=run_internal,
            boundary_runner=run_boundary,
            tables=EXPENSE_TABLES,
            snapshot_kwargs={
                "include_sale_rows": False,
                "include_expense_rows": True,
                "include_bank_txn_rows": True,
            },
        )
        assert_persisted_state_equal(left, right)
        assert left["counts"]["journal_entries"] == 1
        assert left["counts"]["audit_log"] == 1
        assert left["counts"]["expense_records"] == 1
        assert len(left["journal_lines"]) == 2
        assert len(left["audit_rows"]) == 1

    def test_gl_line_tuples_cash_expense(self):
        commit_modes.set_commit_mode_for_tests(POST_EXPENSE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        _cash_expense_boundary(sess, cid)
        office = posting.get_account_by_name(sess, "Office Expense", company_id=cid)
        cash = posting.get_account_by_name(sess, "Cash", company_id=cid)
        je = sess.query(models.JournalEntry).filter_by(reference_type="Expense").one()
        lines = [
            (ln.account_id, ln.debit or 0.0, ln.credit or 0.0)
            for ln in sess.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .order_by(models.JournalEntryLine.id)
            .all()
        ]
        assert lines == [(office.id, AMOUNT, 0.0), (cash.id, 0.0, AMOUNT)]
        assert je.description == f"{CATEGORY} Expense (ID: {je.reference_id})"
        assert je.entry_date == POST_DATE

    def test_bank_subledger_rows_match_internal(self):
        commit_modes.set_commit_mode_for_tests(POST_EXPENSE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        record = _bank_expense_boundary(sess, cid)
        snap = _expense_snapshot(sess)
        assert snap["counts"]["bank_transactions"] == 1
        assert snap["bank_txns"][0][3] == "withdrawal"
        assert f"EXP#{record.id}" in snap["bank_txns"][0][4]

    def test_cc_subledger_rows_match_internal(self):
        commit_modes.set_commit_mode_for_tests(POST_EXPENSE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session, cc_card=True)
        record = _cc_expense_boundary(sess, cid)
        snap = _expense_snapshot(sess)
        assert snap["counts"]["bank_transactions"] == 1
        assert snap["bank_txns"][0][3] == "withdrawal"
        assert snap["bank_txns"][0][7] == f"ccc:Expense:{record.id}"
        assert expense_row_tuples(sess)[0][8] is not None


class TestPostExpenseBoundaryRollback:
    def test_guard_failure_rolls_back_expense_je_and_audit(self):
        commit_modes.set_commit_mode_for_tests(POST_EXPENSE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        period = models.FiscalPeriod(
            name="Closed Aug 2026",
            start_date=POST_DATE,
            end_date=POST_DATE,
            is_closed=True,
            closed_at=POST_DATE,
            company_id=cid,
        )
        sess.add(period)
        sess.commit()

        record = _expense_draft(cid)
        with pytest.raises(ValueError):
            with boundary_commit_scope(sess, POST_EXPENSE_FAMILY):
                app._save_and_post_expense_record(
                    sess, record, category=CATEGORY, payment_method="Cash"
                )
                _log_expense_audit(sess, record.id, cid)

        assert sess.query(func.count()).select_from(models.JournalEntry).scalar() == 0
        assert sess.query(func.count()).select_from(models.AuditLog).scalar() == 0
        assert sess.query(func.count()).select_from(models.ExpenseRecord).scalar() == 0

    def test_mode_flag_reverts_to_internal(self):
        commit_modes.set_commit_mode_for_tests(POST_EXPENSE_FAMILY, CommitMode.BOUNDARY)
        assert commit_modes.is_boundary_mode(POST_EXPENSE_FAMILY)
        commit_modes.reset_commit_modes_for_tests()
        assert not commit_modes.is_boundary_mode(POST_EXPENSE_FAMILY)


class TestPostExpenseAuditAtomic:
    def test_audit_row_content_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(POST_EXPENSE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        record = _cash_expense_boundary(sess, cid)
        assert audit_row_tuples(sess) == [
            (
                audit_svc.ACTION_CREATE,
                audit_svc.ENTITY_EXPENSE_RECORD,
                record.id,
                AUDIT_DESC,
                PERFORMED_BY,
                cid,
            )
        ]

    def test_app_post_expense_shim_atomic_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(POST_EXPENSE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        record = _expense_draft(cid)
        sess.add(record)
        sess.commit()
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            app.post_expense(
                sess, record.id, AMOUNT, POST_DATE, CATEGORY, payment_method="Cash"
            )
            assert mock_commit.call_count == 1
        assert journal_line_tuples(sess)
