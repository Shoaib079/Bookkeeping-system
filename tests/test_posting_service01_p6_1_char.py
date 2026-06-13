"""POSTING-SERVICE-01 PS-P6-1-CHAR — partner movement pre-extraction characterization.

Pins post_partner_movement and void_partner_movement behavior before PS-P6-1
extraction. No production changes.
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

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 6, 10)
AMOUNT = 500.0
VOID_REASON = "PS-P6-1-CHAR void pin"
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
    "CapitalContribution": "PartnerCapital",
    "Drawing": "PartnerDrawing",
    "Salary": "PartnerSalary",
    "Advance": "PartnerAdvance",
    "Repayment": "PartnerRepayment",
    "AdvanceOffset": "PartnerAdvanceOffset",
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
            name="P6-1 Char Co",
            slug="p6_1_char_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        yield s, co.id


def _count(db, model):
    return db.query(func.count()).select_from(model).scalar()


def _make_coa(db, code, name, acct_type, *, currency=None):
    acct = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        balance=0.0,
        is_active=True,
        currency=currency,
    )
    db.add(acct)
    db.flush()
    return acct


def _partner_env(session):
    db, cid = session
    _make_coa(db, "1100", "Cash", "Asset", currency="TRY")
    partner_id, err = app.create_partner(db, "Alice", 100.0)
    assert err == ""
    partner = db.get(models.Partner, partner_id)
    bank = models.BankAccount(
        name="Cash",
        currency="TRY",
        balance=10000.0,
        is_active=True,
        kind="bank",
        company_id=cid,
    )
    db.add(bank)
    db.commit()
    gl_cash = app.get_account_by_name(db, "Cash", currency="TRY")
    return {
        "partner_id": partner_id,
        "partner": partner,
        "bank_id": bank.id,
        "bank": bank,
        "cap_id": partner.capital_account_id,
        "cur_id": partner.current_account_id,
        "adv_id": partner.advance_account_id,
        "gl_cash_id": gl_cash.id,
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


def _post(db, env, movement_type, *, amount=AMOUNT, date=POST_DATE, bank=True):
    kwargs = dict(
        partner_id=env["partner_id"],
        movement_type=movement_type,
        amount=amount,
        date=date,
        created_by_id=VOIDER_ID,
    )
    if movement_type != "AdvanceOffset":
        kwargs["bank_account_id"] = env["bank_id"]
    return app.post_partner_movement(db, **kwargs)


@pytest.fixture()
def partner_env(session):
    return _partner_env(session)


class TestPostPartnerMovementCapitalContribution:
    def test_je_bank_movement_and_return(self, session, partner_env):
        db, _ = session
        env = partner_env
        balance_before = env["bank"].balance

        mid, err = _post(db, env, "CapitalContribution")

        assert err == ""
        assert mid is not None
        movement = db.get(models.PartnerMovement, mid)
        assert movement.movement_type == "CapitalContribution"
        assert movement.amount == AMOUNT
        assert movement.is_void is False
        assert movement.bank_transaction_id is not None

        btxn = db.get(models.BankTransaction, movement.bank_transaction_id)
        assert btxn.type == "deposit"
        assert btxn.amount == AMOUNT
        assert btxn.is_void is False
        db.refresh(env["bank"])
        assert env["bank"].balance == balance_before + AMOUNT

        je = _movement_je(db, mid, REF_TYPES["CapitalContribution"])
        assert je.entry_date == POST_DATE
        assert _line_tuples(db, je.id) == [
            (env["gl_cash_id"], AMOUNT, 0.0),
            (env["cap_id"], 0.0, AMOUNT),
        ]


class TestPostPartnerMovementDrawing:
    def test_je_bank_balance_and_return(self, session, partner_env):
        db, _ = session
        env = partner_env
        balance_before = env["bank"].balance

        mid, err = _post(db, env, "Drawing")

        assert err == ""
        assert mid is not None
        movement = db.get(models.PartnerMovement, mid)
        btxn = db.get(models.BankTransaction, movement.bank_transaction_id)
        assert btxn.type == "withdrawal"
        db.refresh(env["bank"])
        assert env["bank"].balance == balance_before - AMOUNT

        je = _movement_je(db, mid, REF_TYPES["Drawing"])
        assert _line_tuples(db, je.id) == [
            (env["cur_id"], AMOUNT, 0.0),
            (env["gl_cash_id"], 0.0, AMOUNT),
        ]


class TestPostPartnerMovementSalary:
    def test_je_bank_side_effects_and_return(self, session, partner_env):
        db, _ = session
        env = partner_env
        balance_before = env["bank"].balance

        mid, err = _post(db, env, "Salary")

        assert err == ""
        assert mid is not None
        movement = db.get(models.PartnerMovement, mid)
        assert movement.bank_transaction_id is not None
        btxn = db.get(models.BankTransaction, movement.bank_transaction_id)
        assert btxn.type == "withdrawal"
        db.refresh(env["bank"])
        assert env["bank"].balance == balance_before - AMOUNT

        je = _movement_je(db, mid, REF_TYPES["Salary"])
        assert _line_tuples(db, je.id) == [
            (env["cur_id"], AMOUNT, 0.0),
            (env["gl_cash_id"], 0.0, AMOUNT),
        ]


class TestPostPartnerMovementAdvance:
    def test_je_bank_balance_and_return(self, session, partner_env):
        db, _ = session
        env = partner_env
        balance_before = env["bank"].balance

        mid, err = _post(db, env, "Advance")

        assert err == ""
        assert mid is not None
        movement = db.get(models.PartnerMovement, mid)
        btxn = db.get(models.BankTransaction, movement.bank_transaction_id)
        assert btxn.type == "withdrawal"
        db.refresh(env["bank"])
        assert env["bank"].balance == balance_before - AMOUNT

        je = _movement_je(db, mid, REF_TYPES["Advance"])
        assert _line_tuples(db, je.id) == [
            (env["adv_id"], AMOUNT, 0.0),
            (env["gl_cash_id"], 0.0, AMOUNT),
        ]


class TestPostPartnerMovementAdvanceOffset:
    def test_je_no_bank_and_return(self, session, partner_env):
        db, _ = session
        env = partner_env
        _post(db, env, "Advance", amount=1000.0)
        balance_before = env["bank"].balance
        n_btxn = _count(db, models.BankTransaction)

        mid, err = _post(db, env, "AdvanceOffset", amount=200.0)

        assert err == ""
        assert mid is not None
        movement = db.get(models.PartnerMovement, mid)
        assert movement.bank_transaction_id is None
        assert _count(db, models.BankTransaction) == n_btxn
        db.refresh(env["bank"])
        assert env["bank"].balance == balance_before

        je = _movement_je(db, mid, REF_TYPES["AdvanceOffset"])
        assert _line_tuples(db, je.id) == [
            (env["cur_id"], 200.0, 0.0),
            (env["adv_id"], 0.0, 200.0),
        ]


class TestPostPartnerMovementGuards:
    def test_missing_partner_exact_error_no_side_effects(self, session, partner_env):
        db, _ = session
        env = partner_env
        n_mv = _count(db, models.PartnerMovement)
        n_je = _count(db, models.JournalEntry)
        n_btxn = _count(db, models.BankTransaction)
        balance_before = env["bank"].balance

        mid, err = app.post_partner_movement(
            db,
            partner_id=99999,
            movement_type="Drawing",
            amount=AMOUNT,
            date=POST_DATE,
            bank_account_id=env["bank_id"],
        )

        assert mid is None
        assert err == "Partner not found or inactive."
        assert _count(db, models.PartnerMovement) == n_mv
        assert _count(db, models.JournalEntry) == n_je
        assert _count(db, models.BankTransaction) == n_btxn
        db.refresh(env["bank"])
        assert env["bank"].balance == balance_before

    def test_yec_guard_exact_message_no_side_effects(self, session, partner_env):
        db, cid = session
        env = partner_env
        _insert_closed_yec(db, cid)
        n_mv = _count(db, models.PartnerMovement)
        n_je = _count(db, models.JournalEntry)
        balance_before = env["bank"].balance

        mid, err = app.post_partner_movement(
            db,
            partner_id=env["partner_id"],
            movement_type="Drawing",
            amount=AMOUNT,
            date=CLOSED_MOVEMENT_DATE,
            bank_account_id=env["bank_id"],
        )

        assert mid is None
        assert err == POST_YEC_MSG
        assert _count(db, models.PartnerMovement) == n_mv
        assert _count(db, models.JournalEntry) == n_je
        db.refresh(env["bank"])
        assert env["bank"].balance == balance_before


class TestVoidPartnerMovementSuccess:
    def test_void_reverses_gl_bank_and_void_fields(self, session, partner_env):
        db, _ = session
        env = partner_env
        balance_before = env["bank"].balance
        mid, _ = _post(db, env, "Drawing")
        movement = db.get(models.PartnerMovement, mid)
        original_je_id = movement.journal_entry_id
        db.refresh(env["bank"])
        assert env["bank"].balance == balance_before - AMOUNT
        n_je = _count(db, models.JournalEntry)

        err = app.void_partner_movement(db, mid, VOIDER_ID, VOID_REASON)

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
        assert env["bank"].balance == balance_before

        assert _count(db, models.JournalEntry) == n_je + 1
        reversal = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="Reversal", reference_id=original_je_id)
            .one()
        )
        assert reversal.entry_date == datetime.date.today()


class TestVoidPartnerMovementErrors:
    def test_missing_movement_exact_error_no_commit(self, session, partner_env):
        db, _ = session
        n_audit = _count(db, models.AuditLog)

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.void_partner_movement(db, 99999, VOIDER_ID, VOID_REASON)

        assert err == "Movement not found or already voided."
        assert mock_commit.call_count == 0
        assert _count(db, models.AuditLog) == n_audit

    def test_already_voided_exact_error_no_commit(self, session, partner_env):
        db, _ = session
        env = partner_env
        mid, _ = _post(db, env, "Drawing")
        assert app.void_partner_movement(db, mid, VOIDER_ID, VOID_REASON) == ""
        n_audit = _count(db, models.AuditLog)

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.void_partner_movement(db, mid, VOIDER_ID, "second void")

        assert err == "Movement not found or already voided."
        assert mock_commit.call_count == 0
        assert _count(db, models.AuditLog) == n_audit

    def test_empty_reason_exact_error_no_commit(self, session, partner_env):
        db, _ = session
        env = partner_env
        mid, _ = _post(db, env, "Drawing")

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.void_partner_movement(db, mid, VOIDER_ID, "   ")

        assert err == "Void reason is required."
        assert mock_commit.call_count == 0


class TestVoidPartnerMovementYecGuard:
    def test_blocks_with_exact_message_no_side_effects(self, session, partner_env):
        db, cid = session
        env = partner_env
        mid, _ = _post(db, env, "Drawing", date=CLOSED_MOVEMENT_DATE)
        movement = db.get(models.PartnerMovement, mid)
        btxn_id = movement.bank_transaction_id
        balance_after_post = env["bank"].balance
        n_je = _count(db, models.JournalEntry)
        _insert_closed_yec(db, cid)

        err = app.void_partner_movement(db, mid, VOIDER_ID, VOID_REASON)

        assert err == VOID_YEC_MSG
        db.refresh(movement)
        assert movement.is_void is False
        assert _count(db, models.JournalEntry) == n_je
        btxn = db.get(models.BankTransaction, btxn_id)
        assert btxn.is_void is False
        db.refresh(env["bank"])
        assert env["bank"].balance == balance_after_post


class TestPartnerMovementCommitAuditBoundary:
    def test_post_drawing_three_commits_and_create_audit(self, session, partner_env):
        db, _ = session
        env = partner_env

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            mid, err = _post(db, env, "Drawing")
            assert err == ""
            assert mock_commit.call_count == 3

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="Create",
                entity_type="PartnerMovement",
                entity_id=mid,
            )
            .one()
        )
        assert audit.description == f"Drawing: Alice — {AMOUNT:,.2f}"
        assert audit.performed_by == app._DEV_USER["username"]

    def test_void_drawing_three_commits_and_void_audit(self, session, partner_env):
        db, _ = session
        env = partner_env
        mid, _ = _post(db, env, "Drawing")

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.void_partner_movement(db, mid, VOIDER_ID, VOID_REASON)
            assert err == ""
            assert mock_commit.call_count == 3

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="Void",
                entity_type="PartnerMovement",
                entity_id=mid,
            )
            .one()
        )
        assert audit.description == f"Voided Drawing: {AMOUNT:,.2f} — {VOID_REASON}"
        assert audit.performed_by == app._DEV_USER["username"]
