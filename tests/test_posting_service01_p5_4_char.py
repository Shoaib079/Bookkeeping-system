"""POSTING-SERVICE-01 PS-P5-4-CHAR — close/reconciliation void pre-extraction characterization.

Pins void_reconciliation, void_eod_close, and void_year_end_close behavior
before PS-P5-4 extraction. No production changes.
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

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

TEST_DATE = datetime.date(2025, 6, 15)
EOD_DATE = datetime.date(2025, 7, 1)
OWNER_ID = 42
VOID_REASON = "PS-P5-4-CHAR void pin"

NOT_FOUND_MSG = "Reconciliation not found."
DRAFT_MSG = "Cannot void a draft reconciliation; delete it instead."
ALREADY_VOIDED_RECON_MSG = "Reconciliation already voided."
YEC_REASON_REQUIRED_MSG = "Void reason is required."


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
            name="P5-4 Char Co",
            slug="p5_4_char_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        yield s, co.id


@pytest.fixture()
def recon_seeded(session):
    db, cid = session
    cashier = models.User(
        username="cashier_p54",
        display_name="Cashier",
        password_hash="x",
        role="cashier",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    manager = models.User(
        username="manager_p54",
        display_name="Manager",
        password_hash="x",
        role="manager",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add_all([cashier, manager])
    db.flush()
    cash_acct = models.ChartOfAccounts(
        account_code="1010",
        account_name="Cash",
        account_type="Asset",
        balance=0.0,
        is_active=True,
    )
    cash_over_short = models.ChartOfAccounts(
        account_code="7010",
        account_name="Cash Over/Short",
        account_type="Expense",
        balance=0.0,
        is_active=True,
    )
    db.add_all([cash_acct, cash_over_short])
    db.commit()
    return {
        "cashier_id": cashier.id,
        "manager_id": manager.id,
        "cash_id": cash_acct.id,
        "company_id": cid,
    }


def _submit_recon(db, seeded, *, actual_cash=0.0, date=TEST_DATE):
    return app.submit_reconciliation(
        db,
        date=date,
        cash_account_id=seeded["cash_id"],
        actual_cash=actual_cash,
        notes="",
        created_by_id=seeded["cashier_id"],
    )


def _draft_recon(db, seeded, *, date=TEST_DATE):
    recon = models.DailyCashReconciliation(
        date=date,
        cash_account_id=seeded["cash_id"],
        expected_cash=0.0,
        actual_cash=0.0,
        difference=0.0,
        variance_type="balanced",
        status="draft",
        created_by_id=seeded["cashier_id"],
        created_at=datetime.datetime.now(),
        company_id=seeded["company_id"],
    )
    db.add(recon)
    db.commit()
    return recon.id


def _close_eod(db, seeded, *, date=EOD_DATE):
    return app.close_day(db, date, seeded["manager_id"], "EOD pin")


def _make_year_end_close(db, cid, *, fiscal_year="2025"):
    yec = models.YearEndClose(
        fiscal_year=fiscal_year,
        start_date=datetime.date(2025, 1, 1),
        end_date=datetime.date(2025, 12, 31),
        status="closed",
        closed_at=datetime.datetime.now(),
        period_count=12,
        allocation_count=1,
        net_income_snapshot=1000.0,
        re_balance_at_close=5000.0,
        created_at=datetime.datetime.now(),
        company_id=cid,
    )
    db.add(yec)
    db.commit()
    return yec


class TestVoidReconciliationGuardStrings:
    def test_not_found_returns_exact_string(self, session, recon_seeded):
        db, _cid = session
        err = app.void_reconciliation(db, 99999, OWNER_ID, VOID_REASON)
        assert err == NOT_FOUND_MSG

    def test_draft_returns_exact_string(self, session, recon_seeded):
        db, _cid = session
        draft_id = _draft_recon(db, recon_seeded)
        err = app.void_reconciliation(db, draft_id, OWNER_ID, VOID_REASON)
        assert err == DRAFT_MSG

    def test_already_voided_returns_exact_string(self, session, recon_seeded):
        db, _cid = session
        recon_id, _ = _submit_recon(db, recon_seeded, actual_cash=0.0)
        assert app.void_reconciliation(db, recon_id, OWNER_ID, "first") == ""
        err = app.void_reconciliation(db, recon_id, OWNER_ID, "second")
        assert err == ALREADY_VOIDED_RECON_MSG


class TestEmptyReasonAsymmetry:
    def test_void_reconciliation_succeeds_with_empty_reason(self, session, recon_seeded):
        db, _cid = session
        recon_id, _ = _submit_recon(db, recon_seeded, actual_cash=0.0)
        assert app.void_reconciliation(db, recon_id, OWNER_ID, "") == ""

    def test_void_eod_close_succeeds_with_empty_reason(self, session, recon_seeded):
        db, _cid = session
        close_id, _ = _close_eod(db, recon_seeded)
        assert app.void_eod_close(db, close_id, recon_seeded["manager_id"], "") == ""

    def test_void_year_end_close_fails_with_empty_reason(self, session):
        db, cid = session
        yec = _make_year_end_close(db, cid)
        err = app.void_year_end_close(db, yec.id, OWNER_ID, "")
        assert err == YEC_REASON_REQUIRED_MSG


class TestCommitCounts:
    def test_void_reconciliation_with_posted_je_posts_three_commits(
        self, session, recon_seeded
    ):
        db, _cid = session
        recon_id, _ = _submit_recon(db, recon_seeded, actual_cash=20.0)
        app.approve_reconciliation(db, recon_id, recon_seeded["manager_id"])

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_reconciliation(db, recon_id, OWNER_ID, VOID_REASON) == ""
            assert mock_commit.call_count == 3

    def test_void_reconciliation_without_je_posts_two_commits(
        self, session, recon_seeded
    ):
        db, _cid = session
        recon_id, _ = _submit_recon(
            db, recon_seeded, actual_cash=0.0, date=TEST_DATE + datetime.timedelta(days=1)
        )

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_reconciliation(db, recon_id, OWNER_ID, VOID_REASON) == ""
            assert mock_commit.call_count == 2

    def test_void_eod_close_posts_two_commits(self, session, recon_seeded):
        db, _cid = session
        close_id, _ = _close_eod(db, recon_seeded)

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_eod_close(db, close_id, OWNER_ID, VOID_REASON) == ""
            assert mock_commit.call_count == 2

    def test_void_year_end_close_posts_two_commits(self, session):
        db, cid = session
        yec = _make_year_end_close(db, cid)

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_year_end_close(db, yec.id, OWNER_ID, VOID_REASON) == ""
            assert mock_commit.call_count == 2


class TestAuditDescriptions:
    def test_void_reconciliation_audit_description(self, session, recon_seeded):
        db, _cid = session
        recon_id, _ = _submit_recon(db, recon_seeded, actual_cash=0.0)
        assert app.void_reconciliation(db, recon_id, OWNER_ID, VOID_REASON) == ""

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="Void",
                entity_type="DailyCashReconciliation",
                entity_id=recon_id,
            )
            .one()
        )
        assert audit.description == f"Voided by user {OWNER_ID}, reason: {VOID_REASON}"
        assert audit.performed_by == app._DEV_USER["username"]

    def test_void_eod_close_audit_description_includes_date(self, session, recon_seeded):
        db, _cid = session
        close_id, _ = _close_eod(db, recon_seeded)
        assert app.void_eod_close(db, close_id, OWNER_ID, VOID_REASON) == ""

        audit = (
            db.query(models.AuditLog)
            .filter_by(action="Void", entity_type="EndOfDayClose", entity_id=close_id)
            .one()
        )
        assert audit.description == (
            f"Day {EOD_DATE} close voided by user {OWNER_ID}: {VOID_REASON}"
        )

    def test_void_year_end_close_audit_description_includes_fiscal_year(self, session):
        db, cid = session
        yec = _make_year_end_close(db, cid, fiscal_year="2025")
        assert app.void_year_end_close(db, yec.id, OWNER_ID, VOID_REASON) == ""

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="VoidYearEndClose",
                entity_type="YearEndClose",
                entity_id=yec.id,
            )
            .one()
        )
        assert audit.description == (
            f"Voided year-end close for 2025 — {VOID_REASON}"
        )
