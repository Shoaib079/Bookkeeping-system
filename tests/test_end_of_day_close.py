"""Regression tests for Phase 9D End-of-Day Close.

Uses an isolated in-memory SQLite database — no production data is read or written.

Verification checklist from the implementation brief:
 1. Day can close with no warnings
 2. Day can close with warnings
 3. Duplicate active close is blocked
 4. Owner can void close
 5. After void, same date can be reclosed
 6. Late transaction changes JE count and marks close stale
 7. No transaction posting logic changed  (checked implicitly)
 8. Trial Balance remains balanced         (checked via direct GL assertion)
 9. Balance Sheet remains balanced         (checked via direct GL assertion)
10. Permissions work correctly
"""

import json
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

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


TEST_DATE = datetime.date(2025, 7, 1)


# ─── Fixtures ────────────────────────────────────────────────────────────────

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
    """Seed users and the minimum GL accounts needed by reconciliation + EOD."""
    cashier = models.User(
        username="cashier1", display_name="Alice", password_hash="x",
        role="cashier", is_active=True, created_at=datetime.datetime.now(),
    )
    manager = models.User(
        username="manager1", display_name="Bob", password_hash="x",
        role="manager", is_active=True, created_at=datetime.datetime.now(),
    )
    session.add_all([cashier, manager])
    session.flush()

    cash_acct = models.ChartOfAccounts(
        account_code="1010", account_name="Cash",
        account_type="Asset", balance=0.0, is_active=True,
    )
    cos_acct = models.ChartOfAccounts(
        account_code="7010", account_name="Cash Over/Short",
        account_type="Expense", balance=0.0, is_active=True,
    )
    session.add_all([cash_acct, cos_acct])
    session.commit()

    return {
        "cashier_id": cashier.id,
        "manager_id": manager.id,
        "cash_id":    cash_acct.id,
    }


def _close(session, seeded, date=TEST_DATE, notes="All good today."):
    """Thin wrapper for close_day."""
    return app.close_day(session, date, seeded["manager_id"], notes)


# ─── 1. Close with no warnings ────────────────────────────────────────────────

class TestCloseNoWarnings:
    def test_close_succeeds_and_records_snapshot(self, session, seeded):
        """A clean day closes successfully; snapshot fields are stored."""
        close_id, err = _close(session, seeded)

        assert err == ""
        assert close_id is not None

        eod = session.get(models.EndOfDayClose, close_id)
        assert eod.status == "closed"
        assert eod.is_void is False
        assert eod.date == TEST_DATE
        # No transactions → all totals are zero
        assert eod.total_sales == 0.0
        assert eod.total_expenses == 0.0
        assert eod.net_cash_movement == 0.0

    def test_close_stores_notes(self, session, seeded):
        close_id, _ = _close(session, seeded, notes="Quiet day.")
        eod = session.get(models.EndOfDayClose, close_id)
        assert eod.notes == "Quiet day."

    def test_close_no_warnings_when_recon_complete(self, session, seeded):
        """had_warnings is False when reconciliation is done and no pending drafts."""
        # Balanced reconciliation clears the recon checklist item
        app.submit_reconciliation(
            session, date=TEST_DATE, cash_account_id=seeded["cash_id"],
            actual_cash=0.0, notes="", created_by_id=seeded["cashier_id"],
        )
        close_id, _ = _close(session, seeded)
        eod = session.get(models.EndOfDayClose, close_id)
        assert eod.had_warnings is False
        assert eod.warnings_json is None

    def test_audit_log_entry_created(self, session, seeded):
        """Closing creates an audit log entry."""
        before_count = session.query(models.AuditLog).count()
        _close(session, seeded)
        after_count = session.query(models.AuditLog).count()
        assert after_count > before_count


# ─── 2. Close with warnings ───────────────────────────────────────────────────

class TestCloseWithWarnings:
    def test_close_allowed_with_pending_recon(self, session, seeded):
        """Day can be closed even when cash reconciliation is pending approval."""
        # Submit a shortage reconciliation → leaves status pending_approval
        app.submit_reconciliation(
            session, date=TEST_DATE, cash_account_id=seeded["cash_id"],
            actual_cash=-5.0, notes="", created_by_id=seeded["cashier_id"],
        )
        close_id, err = _close(session, seeded)

        assert err == ""
        eod = session.get(models.EndOfDayClose, close_id)
        assert eod.had_warnings is True
        warnings = json.loads(eod.warnings_json)
        assert any("awaiting manager approval" in w for w in warnings)

    def test_close_allowed_with_no_recon(self, session, seeded):
        """Day can be closed with no reconciliation submitted (warning only)."""
        close_id, err = _close(session, seeded)
        # No reconciliation at all → warning recorded, close still succeeds
        snap = app.calculate_eod_snapshot(session, TEST_DATE)
        # snap["recon_status"] == "none" → should have generated a warning
        # but close has already committed; verify via eod record
        eod = session.get(models.EndOfDayClose, close_id)
        assert err == ""
        # recon_status was 'none' at close time → had_warnings True
        assert eod.had_warnings is True

    def test_warnings_captured_in_json(self, session, seeded):
        """warnings_json stores a parseable list."""
        _close(session, seeded)  # no recon → at least one warning
        eod = session.query(models.EndOfDayClose).filter_by(date=TEST_DATE).first()
        assert eod.had_warnings is True
        parsed = json.loads(eod.warnings_json)
        assert isinstance(parsed, list)
        assert len(parsed) >= 1

    def test_recurring_draft_warning(self, session, seeded):
        """Unposted recurring draft due today appears in warnings."""
        tmpl = models.RecurringExpenseTemplate(
            name="Rent", category="Rent", description="",
            amount=500.0, payment_method="Cash", frequency="monthly",
            start_date=TEST_DATE, next_due_date=TEST_DATE,
        )
        session.add(tmpl)
        session.flush()
        draft = models.RecurringExpenseDraft(
            template_id=tmpl.id, due_date=TEST_DATE, amount=500.0,
            description="", category="Rent", payment_method="Cash",
            status="pending",
        )
        session.add(draft)
        session.commit()

        snap = app.calculate_eod_snapshot(session, TEST_DATE)
        assert any("recurring expense draft" in w.lower() for w in snap["warnings"])

    def test_reconciled_day_no_recon_warning(self, session, seeded):
        """A completed balanced reconciliation removes the recon warning."""
        app.submit_reconciliation(
            session, date=TEST_DATE, cash_account_id=seeded["cash_id"],
            actual_cash=0.0, notes="", created_by_id=seeded["cashier_id"],
        )
        snap = app.calculate_eod_snapshot(session, TEST_DATE)
        assert not any("reconciliation" in w.lower() for w in snap["warnings"])


# ─── 3. Duplicate active close blocked ───────────────────────────────────────

class TestDuplicatePrevention:
    def test_second_close_same_date_blocked(self, session, seeded):
        """A second active close for the same date is refused."""
        _close(session, seeded)
        close_id2, err = _close(session, seeded)

        assert close_id2 is None
        assert "already closed" in err.lower()

    def test_different_dates_both_allowed(self, session, seeded):
        """Closes for different dates are independent."""
        _close(session, seeded, date=TEST_DATE)
        close_id2, err = _close(
            session, seeded, date=TEST_DATE + datetime.timedelta(days=1)
        )
        assert err == ""
        assert close_id2 is not None


# ─── 4. Owner can void close ──────────────────────────────────────────────────

class TestVoid:
    def test_void_marks_record_correctly(self, session, seeded):
        """Voiding sets is_void, status, void_reason, voided_by_id."""
        close_id, _ = _close(session, seeded)
        err = app.void_eod_close(session, close_id, seeded["manager_id"], "Wrong figures")

        assert err == ""
        eod = session.get(models.EndOfDayClose, close_id)
        assert eod.is_void is True
        assert eod.status == "voided"
        assert eod.void_reason == "Wrong figures"
        assert eod.voided_by_id == seeded["manager_id"]

    def test_double_void_returns_error(self, session, seeded):
        """Voiding an already-voided close returns an error."""
        close_id, _ = _close(session, seeded)
        app.void_eod_close(session, close_id, seeded["manager_id"], "first")
        err = app.void_eod_close(session, close_id, seeded["manager_id"], "second")

        assert err != ""
        assert "already been voided" in err.lower()

    def test_void_nonexistent_id_returns_error(self, session, seeded):
        err = app.void_eod_close(session, 99999, seeded["manager_id"], "oops")
        assert err != ""

    def test_void_creates_audit_log(self, session, seeded):
        close_id, _ = _close(session, seeded)
        before = session.query(models.AuditLog).count()
        app.void_eod_close(session, close_id, seeded["manager_id"], "Error")
        after = session.query(models.AuditLog).count()
        assert after > before


# ─── 5. After void, same date can be reclosed ─────────────────────────────────

class TestReclose:
    def test_reclose_after_void_succeeds(self, session, seeded):
        """Voiding releases the date for a new close."""
        close_id1, _ = _close(session, seeded)
        app.void_eod_close(session, close_id1, seeded["manager_id"], "Mistake")

        close_id2, err = _close(session, seeded, notes="Corrected close.")

        assert err == ""
        assert close_id2 is not None
        assert close_id2 != close_id1

    def test_reclose_has_fresh_snapshot(self, session, seeded):
        """Reclose captures a new snapshot independent of the voided one."""
        close_id1, _ = _close(session, seeded, notes="First attempt")
        app.void_eod_close(session, close_id1, seeded["manager_id"], "Wrong")

        close_id2, _ = _close(session, seeded, notes="Corrected")
        eod2 = session.get(models.EndOfDayClose, close_id2)
        assert eod2.notes == "Corrected"

    def test_both_void_and_active_records_coexist(self, session, seeded):
        """Voided record is preserved alongside the new active record."""
        close_id1, _ = _close(session, seeded)
        app.void_eod_close(session, close_id1, seeded["manager_id"], "Mistake")
        close_id2, _ = _close(session, seeded)

        all_closes = (
            session.query(models.EndOfDayClose)
            .filter(models.EndOfDayClose.date == TEST_DATE)
            .all()
        )
        assert len(all_closes) == 2
        statuses = {c.status for c in all_closes}
        assert "voided" in statuses
        assert "closed" in statuses


# ─── 6. Stale detection via JE count ──────────────────────────────────────────

class TestStaleDetection:
    def test_close_not_stale_immediately(self, session, seeded):
        """A freshly closed day with no subsequent JEs is not stale."""
        close_id, _ = _close(session, seeded)
        eod = session.get(models.EndOfDayClose, close_id)
        assert app._eod_is_stale(session, eod) is False

    def test_new_je_marks_close_stale(self, session, seeded):
        """Posting a new journal entry after close makes the day stale."""
        close_id, _ = _close(session, seeded)
        eod = session.get(models.EndOfDayClose, close_id)

        # Post a JE for the same date after close (simulate late transaction)
        je = models.JournalEntry(
            entry_date=TEST_DATE,
            description="Late transaction",
            reference_type="CashSale",
            reference_id=999,
        )
        session.add(je)
        session.commit()

        assert app._eod_is_stale(session, eod) is True

    def test_je_on_different_date_not_stale(self, session, seeded):
        """A JE on a different date does not make this date's close stale."""
        close_id, _ = _close(session, seeded)
        eod = session.get(models.EndOfDayClose, close_id)

        other_date = TEST_DATE + datetime.timedelta(days=1)
        je = models.JournalEntry(
            entry_date=other_date,
            description="Tomorrow's transaction",
            reference_type="CashSale",
            reference_id=999,
        )
        session.add(je)
        session.commit()

        assert app._eod_is_stale(session, eod) is False

    def test_je_count_snapshot_stored_correctly(self, session, seeded):
        """je_count_snapshot reflects JEs that exist at close time."""
        # Post two JEs for the date before closing
        for i in range(2):
            je = models.JournalEntry(
                entry_date=TEST_DATE, description=f"Pre-close JE {i}",
                reference_type="CashSale", reference_id=i,
            )
            session.add(je)
        session.commit()

        close_id, _ = _close(session, seeded)
        eod = session.get(models.EndOfDayClose, close_id)
        assert eod.je_count_snapshot == 2
        assert app._eod_is_stale(session, eod) is False


# ─── 7 & 8 & 9. GL integrity: no EOD entries posted ──────────────────────────

class TestGLIntegrity:
    def test_close_day_posts_no_journal_entries(self, session, seeded):
        """close_day() must not create any journal entries."""
        je_before = session.query(models.JournalEntry).count()
        _close(session, seeded)
        je_after = session.query(models.JournalEntry).count()
        assert je_after == je_before

    def test_void_eod_posts_no_journal_entries(self, session, seeded):
        """void_eod_close() must not create any journal entries."""
        close_id, _ = _close(session, seeded)
        je_before = session.query(models.JournalEntry).count()
        app.void_eod_close(session, close_id, seeded["manager_id"], "test void")
        je_after = session.query(models.JournalEntry).count()
        assert je_after == je_before

    def test_gl_balances_unchanged_after_close_void(self, session, seeded):
        """COA balances are identical before and after EOD close + void cycle."""
        before = {
            a.id: a.balance
            for a in session.query(models.ChartOfAccounts).all()
        }
        close_id, _ = _close(session, seeded)
        app.void_eod_close(session, close_id, seeded["manager_id"], "test")
        after = {
            a.id: a.balance
            for a in session.query(models.ChartOfAccounts).all()
        }
        assert before == after


# ─── 10. Permissions ─────────────────────────────────────────────────────────

class TestPermissions:
    def test_close_day_roles(self):
        assert "owner"   in app._PERMISSIONS["close_day"]
        assert "manager" in app._PERMISSIONS["close_day"]
        assert "cashier" not in app._PERMISSIONS["close_day"]
        assert "partner" not in app._PERMISSIONS["close_day"]

    def test_void_eod_owner_only(self):
        assert app._PERMISSIONS["void_eod"] == {"owner"}

    def test_view_eod_all_roles(self):
        view_roles = app._PERMISSIONS["view_eod"]
        for role in ("owner", "manager", "cashier", "partner"):
            assert role in view_roles, f"{role} should be able to view EOD"

    def test_cashier_cannot_close(self):
        assert "cashier" not in app._PERMISSIONS["close_day"]

    def test_manager_cannot_void(self):
        assert "manager" not in app._PERMISSIONS["void_eod"]


# ─── Snapshot accuracy ────────────────────────────────────────────────────────

class TestSnapshotAccuracy:
    def test_recon_status_captured(self, session, seeded):
        """Reconciliation status at close time is stored in the EOD record."""
        app.submit_reconciliation(
            session, date=TEST_DATE, cash_account_id=seeded["cash_id"],
            actual_cash=-5.0, notes="", created_by_id=seeded["cashier_id"],
        )
        close_id, _ = _close(session, seeded)
        eod = session.get(models.EndOfDayClose, close_id)
        assert eod.recon_status == "pending_approval"

    def test_recon_status_none_when_no_recon(self, session, seeded):
        """recon_status is 'none' when no reconciliation exists."""
        close_id, _ = _close(session, seeded)
        eod = session.get(models.EndOfDayClose, close_id)
        assert eod.recon_status == "none"

    def test_snapshot_stores_correct_totals(self, session, seeded):
        """Sales and expense totals from Sale/ExpenseRecord tables are stored."""
        vendor = models.Vendor(name="Test Vendor", is_active=True)
        session.add(vendor)
        session.flush()

        sale = models.Sale(
            date=TEST_DATE, invoice_number="INV001", customer_name="C1",
            amount=100.0, sale_type="Cash", paid_amount=100.0, balance=0.0,
            status="Paid", is_void=False,
        )
        expense = models.ExpenseRecord(
            date=TEST_DATE, expense_type="Expense",
            amount=30.0, is_void=False,
        )
        session.add_all([sale, expense])
        session.commit()

        snap = app.calculate_eod_snapshot(session, TEST_DATE)
        assert snap["cash_sales"]    == pytest.approx(100.0)
        assert snap["total_sales"]   == pytest.approx(100.0)
        assert snap["total_expenses"] == pytest.approx(30.0)
        assert snap["daily_profit_estimate"] == pytest.approx(70.0)
