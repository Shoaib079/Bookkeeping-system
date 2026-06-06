"""Regression tests for Phase 9C Cash Reconciliation.

Uses an isolated in-memory SQLite database — no production data is read or written.
app.py is imported with Streamlit mocked out so tests run in a plain pytest process.
"""

import sys
import datetime
from unittest.mock import MagicMock
from sqlalchemy import event as _sa_event

# ── Streamlit mock — real dict for session_state so cq() works ───────────────
if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock
else:
    _st_mock = sys.modules["streamlit"]
    if not isinstance(getattr(_st_mock, "session_state", None), dict):
        _st_mock.session_state = {}

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app

# Force development mode so _current_user() returns _DEV_USER (owner role)
# without touching st.session_state.
app.DEVELOPMENT_MODE = True

TEST_DATE = datetime.date(2025, 6, 15)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def session():
    """Isolated in-memory SQLite session; discarded after each test.

    Phase 14C: creates a Company, sets active_company_id, and registers the
    before_flush stamp event so all objects created in tests get company_id.
    """
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @_sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        co = models.Company(
            name="Test Co", slug="test_co", is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        yield s


@pytest.fixture()
def seeded(session):
    """Add two users and the minimum GL accounts needed by the reconciliation
    workflow, then return a dict of their IDs."""
    cashier = models.User(
        username="cashier1",
        display_name="Alice",
        password_hash="x",
        role="cashier",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    manager = models.User(
        username="manager1",
        display_name="Bob",
        password_hash="x",
        role="manager",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    session.add_all([cashier, manager])
    session.flush()

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
    session.add_all([cash_acct, cash_over_short])
    session.commit()

    return {
        "cashier_id": cashier.id,
        "manager_id": manager.id,
        "cash_id": cash_acct.id,
    }


# ─── Helper ──────────────────────────────────────────────────────────────────

def _submit(session, seeded, actual_cash=0.0, date=TEST_DATE):
    """Thin wrapper for submit_reconciliation with sane defaults."""
    return app.submit_reconciliation(
        session,
        date=date,
        cash_account_id=seeded["cash_id"],
        actual_cash=actual_cash,
        notes="",
        created_by_id=seeded["cashier_id"],
    )


# ─── Balanced reconciliation ─────────────────────────────────────────────────

class TestBalanced:
    def test_auto_reconciled_no_je(self, session, seeded):
        """Zero variance auto-reconciles immediately; no journal entry is created."""
        # No transactions in DB → expected cash = 0.0; feed actual = 0.0
        recon_id, err = _submit(session, seeded, actual_cash=0.0)

        assert err == ""
        recon = session.get(models.DailyCashReconciliation, recon_id)
        assert recon.status == "reconciled"
        assert recon.variance_type == "balanced"
        assert recon.difference == 0.0
        assert recon.journal_entry_id is None


# ─── Shortage approval ────────────────────────────────────────────────────────

class TestShortage:
    def test_pending_on_shortage(self, session, seeded):
        """Actual < expected sets status to pending_approval."""
        recon_id, err = _submit(session, seeded, actual_cash=-10.0)

        assert err == ""
        recon = session.get(models.DailyCashReconciliation, recon_id)
        assert recon.status == "pending_approval"
        assert recon.variance_type == "shortage"
        assert recon.difference == pytest.approx(-10.0)

    def test_approval_posts_shortage_je(self, session, seeded):
        """Approving a shortage posts Dr Cash Over/Short / Cr Cash."""
        recon_id, _ = _submit(session, seeded, actual_cash=-10.0)
        err = app.approve_reconciliation(session, recon_id, seeded["manager_id"])

        assert err == ""
        recon = session.get(models.DailyCashReconciliation, recon_id)
        assert recon.status == "reconciled"
        assert recon.journal_entry_id is not None

        je = session.get(models.JournalEntry, recon.journal_entry_id)
        lines = {line.account_id: line for line in je.lines}

        cos_id = (
            session.query(models.ChartOfAccounts)
            .filter_by(account_name="Cash Over/Short")
            .one()
            .id
        )
        # Dr Cash Over/Short for the missing amount
        assert lines[cos_id].debit == pytest.approx(10.0)
        assert lines[cos_id].credit == 0.0
        # Cr Cash
        assert lines[seeded["cash_id"]].credit == pytest.approx(10.0)
        assert lines[seeded["cash_id"]].debit == 0.0


# ─── Overage approval ────────────────────────────────────────────────────────

class TestOverage:
    def test_approval_posts_overage_je(self, session, seeded):
        """Approving an overage posts Dr Cash / Cr Cash Over/Short."""
        recon_id, _ = _submit(session, seeded, actual_cash=10.0)
        err = app.approve_reconciliation(session, recon_id, seeded["manager_id"])

        assert err == ""
        recon = session.get(models.DailyCashReconciliation, recon_id)
        assert recon.status == "reconciled"

        je = session.get(models.JournalEntry, recon.journal_entry_id)
        lines = {line.account_id: line for line in je.lines}

        cos_id = (
            session.query(models.ChartOfAccounts)
            .filter_by(account_name="Cash Over/Short")
            .one()
            .id
        )
        # Dr Cash for the extra amount found
        assert lines[seeded["cash_id"]].debit == pytest.approx(10.0)
        assert lines[seeded["cash_id"]].credit == 0.0
        # Cr Cash Over/Short
        assert lines[cos_id].credit == pytest.approx(10.0)
        assert lines[cos_id].debit == 0.0


# ─── Rejection ───────────────────────────────────────────────────────────────

class TestRejection:
    def test_rejection_stores_reason_and_actor(self, session, seeded):
        """Rejected reconciliation records the reason and the rejecting manager."""
        recon_id, _ = _submit(session, seeded, actual_cash=-5.0)
        err = app.reject_reconciliation(
            session, recon_id, seeded["manager_id"], reason="Recount needed"
        )

        assert err == ""
        recon = session.get(models.DailyCashReconciliation, recon_id)
        assert recon.status == "rejected"
        assert recon.rejection_reason == "Recount needed"
        assert recon.rejected_by_id == seeded["manager_id"]

    def test_cannot_approve_after_rejection(self, session, seeded):
        """approve_reconciliation returns an error when status is rejected."""
        recon_id, _ = _submit(session, seeded, actual_cash=-5.0)
        app.reject_reconciliation(session, recon_id, seeded["manager_id"], "Wrong")
        err = app.approve_reconciliation(session, recon_id, seeded["manager_id"])

        assert err != ""
        assert "rejected" in err.lower() or "pending" in err.lower()


# ─── Void with reversal JE ────────────────────────────────────────────────────

class TestVoid:
    def test_void_creates_reversal_je(self, session, seeded):
        """Voiding a reconciliation that has a variance JE generates a reversal."""
        recon_id, _ = _submit(session, seeded, actual_cash=20.0)
        app.approve_reconciliation(session, recon_id, seeded["manager_id"])

        recon = session.get(models.DailyCashReconciliation, recon_id)
        original_je_id = recon.journal_entry_id
        assert original_je_id is not None

        err = app.void_reconciliation(
            session,
            reconciliation_id=recon_id,
            owner_id=999,  # arbitrary owner ID; function trusts the caller
            reason="Entered wrong figures",
        )
        assert err == ""

        session.refresh(recon)
        assert recon.is_void is True
        assert recon.void_reason == "Entered wrong figures"
        assert recon.reversed_je_id is not None

        reversal = session.get(models.JournalEntry, recon.reversed_je_id)
        assert reversal is not None
        assert reversal.reference_type == "Reversal"
        assert reversal.reference_id == original_je_id

    def test_void_balanced_reconciliation_no_reversal_je(self, session, seeded):
        """Voiding a balanced reconciliation (no JE) leaves reversed_je_id as None."""
        recon_id, _ = _submit(session, seeded, actual_cash=0.0)

        err = app.void_reconciliation(
            session, reconciliation_id=recon_id, owner_id=999, reason="Oops"
        )
        assert err == ""
        recon = session.get(models.DailyCashReconciliation, recon_id)
        assert recon.is_void is True
        assert recon.reversed_je_id is None

    def test_double_void_returns_error(self, session, seeded):
        """Attempting to void an already-voided reconciliation returns an error."""
        recon_id, _ = _submit(session, seeded, actual_cash=0.0)
        app.void_reconciliation(session, recon_id, 999, "first")
        err = app.void_reconciliation(session, recon_id, 999, "second")

        assert err != ""
        assert "already voided" in err.lower()


# ─── Duplicate prevention ────────────────────────────────────────────────────

class TestDuplicatePrevention:
    def test_second_submission_same_date_account_blocked(self, session, seeded):
        """A non-rejected reconciliation already exists → second submit is refused."""
        _submit(session, seeded, actual_cash=0.0)
        recon_id2, err = _submit(session, seeded, actual_cash=5.0)

        assert recon_id2 is None
        assert "already exists" in err

    def test_after_rejection_new_submission_allowed(self, session, seeded):
        """Once the first submission is rejected the cashier may submit a new one."""
        recon_id1, _ = _submit(session, seeded, actual_cash=-5.0)
        app.reject_reconciliation(session, recon_id1, seeded["manager_id"], "Wrong")

        recon_id2, err = _submit(session, seeded, actual_cash=0.0)

        assert err == ""
        assert recon_id2 is not None
        assert recon_id2 != recon_id1

    def test_voided_record_not_counted_as_duplicate(self, session, seeded):
        """A voided reconciliation does not block a fresh submission."""
        recon_id1, _ = _submit(session, seeded, actual_cash=0.0)
        app.void_reconciliation(session, recon_id1, 999, "mistake")

        recon_id2, err = _submit(session, seeded, actual_cash=0.0)

        assert err == ""
        assert recon_id2 is not None
        assert recon_id2 != recon_id1


# ─── Closed fiscal period block ───────────────────────────────────────────────

class TestClosedPeriod:
    def test_submit_blocked_for_closed_period(self, session, seeded):
        """submit_reconciliation returns an error for a date in a closed period."""
        fp = models.FiscalPeriod(
            name="May 2025",
            start_date=datetime.date(2025, 5, 1),
            end_date=datetime.date(2025, 5, 31),
            is_closed=True,
            closed_at=datetime.date(2025, 6, 1),
        )
        session.add(fp)
        session.commit()

        recon_id, err = _submit(
            session, seeded, actual_cash=0.0, date=datetime.date(2025, 5, 15)
        )

        assert recon_id is None
        assert "closed" in err.lower()

    def test_submit_allowed_for_open_period(self, session, seeded):
        """A fiscal period that is not closed does not block submission."""
        fp = models.FiscalPeriod(
            name="June 2025",
            start_date=datetime.date(2025, 6, 1),
            end_date=datetime.date(2025, 6, 30),
            is_closed=False,
        )
        session.add(fp)
        session.commit()

        recon_id, err = _submit(session, seeded, actual_cash=0.0)

        assert err == ""
        assert recon_id is not None


# ─── Permissions ─────────────────────────────────────────────────────────────

class TestPermissions:
    """Verify _PERMISSIONS contains the correct role sets for each 9C action."""

    def test_cashier_can_create_submit_view(self):
        for action in ("create_reconciliation", "submit_reconciliation", "view_reconciliation"):
            assert "cashier" in app._PERMISSIONS[action], action

    def test_cashier_cannot_approve_reject_or_void(self):
        for action in ("approve_reconciliation", "reject_reconciliation", "void_reconciliation"):
            assert "cashier" not in app._PERMISSIONS[action], action

    def test_manager_can_approve_and_reject(self):
        assert "manager" in app._PERMISSIONS["approve_reconciliation"]
        assert "manager" in app._PERMISSIONS["reject_reconciliation"]

    def test_manager_cannot_void(self):
        assert "manager" not in app._PERMISSIONS["void_reconciliation"]

    def test_only_owner_can_void(self):
        assert app._PERMISSIONS["void_reconciliation"] == {"owner"}

    def test_partner_can_only_view(self):
        assert "partner" in app._PERMISSIONS["view_reconciliation"]
        for action in (
            "create_reconciliation",
            "submit_reconciliation",
            "approve_reconciliation",
            "reject_reconciliation",
            "void_reconciliation",
        ):
            assert "partner" not in app._PERMISSIONS[action], action
