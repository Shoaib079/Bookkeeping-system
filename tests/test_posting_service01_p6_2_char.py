"""POSTING-SERVICE-01 PS-P6-2-CHAR — worker movement pre-extraction characterization.

Pins post_worker_movement and void_worker_movement behavior before PS-P6-2
extraction. No production changes.

Worker movement types in app.py: Salary, Advance, Repayment only — there is no
WorkerAdvanceOffset; salary with full advance recovery is the no-bank cash path.
"""
from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event as sa_event, func
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app
from services.money import money_to_float

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 6, 10)
VOID_REASON = "PS-P6-2-CHAR void pin"
VOIDER_ID = 7
FISCAL_YEAR = "2025"
YEC_START = datetime.date(2025, 1, 1)
YEC_END = datetime.date(2025, 12, 31)
CLOSED_MOVEMENT_DATE = datetime.date(2025, 6, 15)
POST_YEC_MSG = (
    f"Year {FISCAL_YEAR} is closed. Cannot post movements dated in that year."
)
VOID_YEC_MSG = (
    f"Year {FISCAL_YEAR} is closed. Void the year-end close before "
    "voiding movements inside it."
)

REF_TYPES = {
    "Salary": "WorkerSalary",
    "Advance": "WorkerAdvance",
    "Repayment": "WorkerRepayment",
}


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
            name="P6-2 Char Co",
            slug="p6_2_char_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        yield s, co.id


def _count(db, model):
    return db.query(func.count()).select_from(model).scalar()


def _make_coa(db, code, name, acct_type, *, currency=None, company_id=None):
    acct = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        balance=0.0,
        is_active=True,
        currency=currency,
        company_id=company_id,
    )
    db.add(acct)
    db.flush()
    return acct


def _worker_env(session):
    db, cid = session
    _make_coa(db, "1010", "Bank", "Asset", currency="TRY", company_id=cid)
    salary_exp = _make_coa(db, "5100", "Salary Expense", "Expense", company_id=cid)
    adv_acct = _make_coa(db, "1250", "Employee Advances", "Asset", company_id=cid)
    worker_id, err = app.create_worker(db, "Ahmet", role="Sales")
    assert err == ""
    bank = models.BankAccount(
        name="Main TRY",
        currency="TRY",
        balance=50000.0,
        is_active=True,
        company_id=cid,
    )
    db.add(bank)
    db.commit()
    gl_bank = app.get_account_by_name(db, "Bank", currency="TRY")
    return {
        "worker_id": worker_id,
        "bank_id": bank.id,
        "bank": bank,
        "salary_exp_id": salary_exp.id,
        "adv_id": adv_acct.id,
        "gl_bank_id": gl_bank.id,
        "company_id": cid,
    }


def _line_tuples(db, journal_entry_id):
    lines = (
        db.query(models.JournalEntryLine)
        .filter_by(journal_entry_id=journal_entry_id)
        .order_by(models.JournalEntryLine.id)
        .all()
    )
    return [(ln.account_id, ln.debit or 0.0, ln.credit or 0.0) for ln in lines]


def _movement_je(db, movement_id, ref_type):
    return (
        db.query(models.JournalEntry)
        .filter_by(reference_type=ref_type, reference_id=movement_id)
        .one()
    )


def _insert_closed_yec(db, company_id):
    yec = models.YearEndClose(
        fiscal_year=FISCAL_YEAR,
        start_date=YEC_START,
        end_date=YEC_END,
        status="closed",
        closed_at=datetime.datetime.now(),
        period_count=12,
        allocation_count=12,
        net_income_snapshot=0.0,
        re_balance_at_close=0.0,
        is_void=False,
        created_at=datetime.datetime.now(),
        company_id=company_id,
    )
    db.add(yec)
    db.commit()


@pytest.fixture()
def worker_env(session):
    return _worker_env(session)


class TestPostWorkerMovementSalary:
    def test_je_bank_balance_and_return(self, session, worker_env):
        db, _ = session
        env = worker_env
        app.post_worker_movement(
            db,
            env["worker_id"],
            "Advance",
            POST_DATE,
            bank_account_id=env["bank_id"],
            amount=2000.0,
        )
        db.refresh(env["bank"])
        balance_before = env["bank"].balance
        gross, deductions, recovery, net_salary, net_paid = (
            10000.0, 1000.0, 2000.0, 9000.0, 7000.0,
        )

        mid, err = app.post_worker_movement(
            db,
            env["worker_id"],
            "Salary",
            POST_DATE,
            bank_account_id=env["bank_id"],
            gross_salary=gross,
            deductions=deductions,
            advance_recovery=recovery,
            pay_period="Jun 2026",
            created_by_id=VOIDER_ID,
        )

        assert err == ""
        assert mid is not None
        movement = db.get(models.WorkerMovement, mid)
        assert movement.movement_type == "Salary"
        assert money_to_float(movement.amount) == net_salary
        assert movement.gross_salary == gross
        assert movement.deductions == deductions
        assert movement.advance_recovery == recovery
        assert movement.net_paid == net_paid
        assert movement.bank_transaction_id is not None

        btxn = db.get(models.BankTransaction, movement.bank_transaction_id)
        assert btxn.type == "withdrawal"
        assert money_to_float(btxn.amount) == net_paid
        db.refresh(env["bank"])
        assert money_to_float(env["bank"].balance) == pytest.approx(money_to_float(balance_before) - net_paid)

        je = _movement_je(db, mid, REF_TYPES["Salary"])
        assert _line_tuples(db, je.id) == [
            (env["salary_exp_id"], net_salary, 0.0),
            (env["adv_id"], 0.0, recovery),
            (env["gl_bank_id"], 0.0, net_paid),
        ]


class TestPostWorkerMovementAdvance:
    def test_je_bank_balance_and_return(self, session, worker_env):
        db, _ = session
        env = worker_env
        amount = 5000.0
        balance_before = env["bank"].balance

        mid, err = app.post_worker_movement(
            db,
            env["worker_id"],
            "Advance",
            POST_DATE,
            bank_account_id=env["bank_id"],
            amount=amount,
            created_by_id=VOIDER_ID,
        )

        assert err == ""
        assert mid is not None
        movement = db.get(models.WorkerMovement, mid)
        assert money_to_float(movement.amount) == amount
        btxn = db.get(models.BankTransaction, movement.bank_transaction_id)
        assert btxn.type == "withdrawal"
        assert money_to_float(btxn.amount) == amount
        db.refresh(env["bank"])
        assert money_to_float(env["bank"].balance) == pytest.approx(money_to_float(balance_before) - amount)

        je = _movement_je(db, mid, REF_TYPES["Advance"])
        assert _line_tuples(db, je.id) == [
            (env["adv_id"], amount, 0.0),
            (env["gl_bank_id"], 0.0, amount),
        ]


class TestPostWorkerMovementSalaryNoBankPath:
    """Full advance recovery — net_paid == 0, no BankTransaction (not a separate type)."""

    def test_je_no_bank_and_return(self, session, worker_env):
        db, _ = session
        env = worker_env
        app.post_worker_movement(
            db,
            env["worker_id"],
            "Advance",
            POST_DATE,
            bank_account_id=env["bank_id"],
            amount=5000.0,
        )
        balance_before = env["bank"].balance
        n_btxn = _count(db, models.BankTransaction)

        mid, err = app.post_worker_movement(
            db,
            env["worker_id"],
            "Salary",
            POST_DATE,
            bank_account_id=env["bank_id"],
            gross_salary=5000.0,
            deductions=0.0,
            advance_recovery=5000.0,
        )

        assert err == ""
        movement = db.get(models.WorkerMovement, mid)
        assert movement.net_paid == 0.0
        assert movement.bank_transaction_id is None
        assert _count(db, models.BankTransaction) == n_btxn
        db.refresh(env["bank"])
        assert money_to_float(env["bank"].balance) == pytest.approx(money_to_float(balance_before))

        je = _movement_je(db, mid, REF_TYPES["Salary"])
        assert _line_tuples(db, je.id) == [
            (env["salary_exp_id"], 5000.0, 0.0),
            (env["adv_id"], 0.0, 5000.0),
        ]


class TestPostWorkerMovementRepayment:
    def test_je_bank_balance_and_return(self, session, worker_env):
        db, _ = session
        env = worker_env
        app.post_worker_movement(
            db,
            env["worker_id"],
            "Advance",
            POST_DATE,
            bank_account_id=env["bank_id"],
            amount=1000.0,
        )
        amount = 400.0
        balance_before = env["bank"].balance

        mid, err = app.post_worker_movement(
            db,
            env["worker_id"],
            "Repayment",
            POST_DATE,
            bank_account_id=env["bank_id"],
            amount=amount,
        )

        assert err == ""
        movement = db.get(models.WorkerMovement, mid)
        btxn = db.get(models.BankTransaction, movement.bank_transaction_id)
        assert btxn.type == "deposit"
        assert money_to_float(btxn.amount) == amount
        db.refresh(env["bank"])
        assert money_to_float(env["bank"].balance) == pytest.approx(money_to_float(balance_before) + amount)

        je = _movement_je(db, mid, REF_TYPES["Repayment"])
        assert _line_tuples(db, je.id) == [
            (env["gl_bank_id"], amount, 0.0),
            (env["adv_id"], 0.0, amount),
        ]


class TestPostWorkerMovementGuards:
    def test_missing_worker_exact_error_no_side_effects(self, session, worker_env):
        db, _ = session
        env = worker_env
        n_mv = _count(db, models.WorkerMovement)
        n_je = _count(db, models.JournalEntry)
        balance_before = env["bank"].balance

        mid, err = app.post_worker_movement(
            db,
            99999,
            "Advance",
            POST_DATE,
            bank_account_id=env["bank_id"],
            amount=1000.0,
        )

        assert mid is None
        assert err == "Worker not found or inactive."
        assert _count(db, models.WorkerMovement) == n_mv
        assert _count(db, models.JournalEntry) == n_je
        db.refresh(env["bank"])
        assert money_to_float(env["bank"].balance) == pytest.approx(money_to_float(balance_before))

    def test_yec_guard_exact_message_no_side_effects(self, session, worker_env):
        db, cid = session
        env = worker_env
        _insert_closed_yec(db, cid)
        n_mv = _count(db, models.WorkerMovement)

        mid, err = app.post_worker_movement(
            db,
            env["worker_id"],
            "Advance",
            CLOSED_MOVEMENT_DATE,
            bank_account_id=env["bank_id"],
            amount=1000.0,
        )

        assert mid is None
        assert err == POST_YEC_MSG
        assert _count(db, models.WorkerMovement) == n_mv


class TestVoidWorkerMovementSuccess:
    def test_void_reverses_gl_bank_and_void_fields(self, session, worker_env):
        db, _ = session
        env = worker_env
        balance_before = env["bank"].balance
        mid, _ = app.post_worker_movement(
            db,
            env["worker_id"],
            "Advance",
            POST_DATE,
            bank_account_id=env["bank_id"],
            amount=800.0,
        )
        movement = db.get(models.WorkerMovement, mid)
        original_je_id = movement.journal_entry_id
        db.refresh(env["bank"])
        assert money_to_float(env["bank"].balance) == pytest.approx(money_to_float(balance_before) - 800.0)
        n_je = _count(db, models.JournalEntry)

        err = app.void_worker_movement(db, mid, VOIDER_ID, VOID_REASON)

        assert err == ""
        db.refresh(movement)
        assert movement.is_void is True
        assert movement.voided_by_id == VOIDER_ID
        assert movement.void_reason == VOID_REASON
        assert movement.voided_at is not None

        btxn = db.get(models.BankTransaction, movement.bank_transaction_id)
        assert btxn.is_void is True
        assert btxn.void_reason == VOID_REASON
        db.refresh(env["bank"])
        assert money_to_float(env["bank"].balance) == pytest.approx(money_to_float(balance_before))

        assert _count(db, models.JournalEntry) == n_je + 1
        reversal = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="Reversal", reference_id=original_je_id)
            .one()
        )
        assert reversal.entry_date == datetime.date.today()


class TestVoidWorkerMovementErrors:
    def test_missing_movement_exact_error_no_commit(self, session, worker_env):
        db, _ = session
        n_audit = _count(db, models.AuditLog)

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.void_worker_movement(db, 99999, VOIDER_ID, VOID_REASON)

        assert err == "Movement not found or already voided."
        assert mock_commit.call_count == 0
        assert _count(db, models.AuditLog) == n_audit

    def test_already_voided_exact_error_no_commit(self, session, worker_env):
        db, _ = session
        env = worker_env
        mid, _ = app.post_worker_movement(
            db,
            env["worker_id"],
            "Advance",
            POST_DATE,
            bank_account_id=env["bank_id"],
            amount=500.0,
        )
        assert app.void_worker_movement(db, mid, VOIDER_ID, VOID_REASON) == ""

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.void_worker_movement(db, mid, VOIDER_ID, "second void")

        assert err == "Movement not found or already voided."
        assert mock_commit.call_count == 0

    def test_empty_reason_exact_error_no_commit(self, session, worker_env):
        db, _ = session
        env = worker_env
        mid, _ = app.post_worker_movement(
            db,
            env["worker_id"],
            "Advance",
            POST_DATE,
            bank_account_id=env["bank_id"],
            amount=500.0,
        )

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.void_worker_movement(db, mid, VOIDER_ID, "   ")

        assert err == "Void reason is required."
        assert mock_commit.call_count == 0


class TestVoidWorkerMovementYecGuard:
    def test_blocks_with_exact_message_no_side_effects(self, session, worker_env):
        db, cid = session
        env = worker_env
        mid, _ = app.post_worker_movement(
            db,
            env["worker_id"],
            "Advance",
            CLOSED_MOVEMENT_DATE,
            bank_account_id=env["bank_id"],
            amount=600.0,
        )
        movement = db.get(models.WorkerMovement, mid)
        balance_after_post = env["bank"].balance
        n_je = _count(db, models.JournalEntry)
        _insert_closed_yec(db, cid)

        err = app.void_worker_movement(db, mid, VOIDER_ID, VOID_REASON)

        assert err == VOID_YEC_MSG
        db.refresh(movement)
        assert movement.is_void is False
        assert _count(db, models.JournalEntry) == n_je
        btxn = db.get(models.BankTransaction, movement.bank_transaction_id)
        assert btxn.is_void is False
        db.refresh(env["bank"])
        assert money_to_float(env["bank"].balance) == pytest.approx(money_to_float(balance_after_post))


class TestWorkerMovementCommitAuditBoundary:
    def test_post_salary_three_commits_and_create_audit(self, session, worker_env):
        db, _ = session
        env = worker_env
        app.post_worker_movement(
            db,
            env["worker_id"],
            "Advance",
            POST_DATE,
            bank_account_id=env["bank_id"],
            amount=2000.0,
        )

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            mid, err = app.post_worker_movement(
                db,
                env["worker_id"],
                "Salary",
                POST_DATE,
                bank_account_id=env["bank_id"],
                gross_salary=10000.0,
                deductions=1000.0,
                advance_recovery=2000.0,
                pay_period="Jun 2026",
            )
            assert err == ""
            assert mock_commit.call_count == 3

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="Create",
                entity_type="WorkerMovement",
                entity_id=mid,
            )
            .one()
        )
        assert audit.description == "Salary: Ahmet — 9,000.00"
        assert audit.performed_by == app._DEV_USER["username"]

    def test_void_salary_three_commits_and_void_audit(self, session, worker_env):
        db, _ = session
        env = worker_env
        app.post_worker_movement(
            db,
            env["worker_id"],
            "Advance",
            POST_DATE,
            bank_account_id=env["bank_id"],
            amount=2000.0,
        )
        mid, _ = app.post_worker_movement(
            db,
            env["worker_id"],
            "Salary",
            POST_DATE,
            bank_account_id=env["bank_id"],
            gross_salary=10000.0,
            deductions=1000.0,
            advance_recovery=2000.0,
        )

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.void_worker_movement(db, mid, VOIDER_ID, VOID_REASON)
            assert err == ""
            assert mock_commit.call_count == 3

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="Void",
                entity_type="WorkerMovement",
                entity_id=mid,
            )
            .one()
        )
        assert audit.description == f"Voided Salary: 9,000.00 — {VOID_REASON}"
        assert audit.performed_by == app._DEV_USER["username"]
