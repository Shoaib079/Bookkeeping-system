"""POSTING-SERVICE-01 PS-P6-3-CHAR — profit allocation pre-extraction characterization.

Pins allocate_profit_to_partners, void_profit_allocation, and
_allocate_all_pending behavior before PS-P6-3 extraction. No production changes.
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

# Allocation JEs post on today(); closed periods use the prior calendar year.
PAST_YEAR = datetime.date.today().year - 1
ALLOCATOR_ID = 7
VOIDER_ID = 8
VOID_REASON = "PS-P6-3-CHAR void pin"
FISCAL_YEAR = "2025"
YEC_START = datetime.date(2025, 1, 1)
YEC_END = datetime.date(2025, 12, 31)
VOID_ALLOCATION_MSG = (
    f"Year {FISCAL_YEAR} is closed. Void the year-end close before "
    "voiding allocations inside it."
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
            name="P6-3 Char Co",
            slug="p6_3_char_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        yield s, co.id


def _count(db, model):
    return db.query(func.count()).select_from(model).scalar()


def _make_coa(db, code, name, acct_type):
    acct = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        balance=0.0,
        is_active=True,
    )
    db.add(acct)
    db.flush()
    return acct


def _make_partner(db, name, pct, cap_id, cur_id, adv_id, *, active=True):
    p = models.Partner(
        name=name,
        profit_share_pct=pct,
        capital_account_id=cap_id,
        current_account_id=cur_id,
        advance_account_id=adv_id,
        is_active=active,
        created_at=datetime.datetime.now(),
    )
    db.add(p)
    db.flush()
    return p


def _line_tuples(db, journal_entry_id):
    lines = (
        db.query(models.JournalEntryLine)
        .filter_by(journal_entry_id=journal_entry_id)
        .order_by(models.JournalEntryLine.id)
        .all()
    )
    return [(ln.account_id, ln.debit or 0.0, ln.credit or 0.0) for ln in lines]


def _closed_period(db, name, start, end, closing_lines, *, closed=True):
    period = models.FiscalPeriod(
        name=name,
        start_date=start,
        end_date=end,
        is_closed=closed,
        closed_at=datetime.date.today() if closed else None,
    )
    db.add(period)
    db.flush()
    if closing_lines:
        closing_je = app.create_journal_entry(
            db,
            end,
            f"Period Close: {name}",
            "PeriodClose",
            period.id,
            closing_lines,
        )
        period.closing_je_id = closing_je.id
        db.commit()
    return period


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
def alloc_env(session):
    db, _ = session
    re_acct = _make_coa(db, "3100", "Retained Earnings", "Equity")
    inc_acct = _make_coa(db, "4000", "Revenue", "Income")
    exp_acct = _make_coa(db, "5000", "Expenses", "Expense")
    cap1 = _make_coa(db, "3501", "Alice Capital", "Equity")
    cur1 = _make_coa(db, "3601", "Alice Current", "Equity")
    adv1 = _make_coa(db, "1501", "Alice Advances", "Asset")
    cap2 = _make_coa(db, "3502", "Bob Capital", "Equity")
    cur2 = _make_coa(db, "3602", "Bob Current", "Equity")
    adv2 = _make_coa(db, "1502", "Bob Advances", "Asset")
    db.commit()
    p1 = _make_partner(db, "Alice", 50.0, cap1.id, cur1.id, adv1.id)
    p2 = _make_partner(db, "Bob", 50.0, cap2.id, cur2.id, adv2.id)
    db.commit()
    return {
        "re_id": re_acct.id,
        "inc_id": inc_acct.id,
        "exp_id": exp_acct.id,
        "p1_id": p1.id,
        "p1_cur": cur1.id,
        "p2_id": p2.id,
        "p2_cur": cur2.id,
    }


class TestAllocateProfitSuccessProfit:
    def test_creates_allocation_je_lines_and_return(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        period = _closed_period(
            db,
            f"Jan {PAST_YEAR}",
            datetime.date(PAST_YEAR, 1, 1),
            datetime.date(PAST_YEAR, 1, 31),
            [(env["inc_id"], 1000.0, 0), (env["re_id"], 0, 1000.0)],
        )

        alloc_id, err = app.allocate_profit_to_partners(
            db, period.id, ALLOCATOR_ID, notes=" Q1 pin "
        )

        assert err == ""
        assert isinstance(alloc_id, int)
        allocation = db.get(models.PartnerProfitAllocation, alloc_id)
        assert allocation.fiscal_period_id == period.id
        assert allocation.total_net_income == 1000.0
        assert allocation.allocated_by_id == ALLOCATOR_ID
        assert allocation.notes == "Q1 pin"
        assert allocation.is_void is False

        lines = (
            db.query(models.PartnerProfitAllocationLine)
            .filter_by(allocation_id=alloc_id)
            .order_by(models.PartnerProfitAllocationLine.partner_id)
            .all()
        )
        assert len(lines) == 2
        assert lines[0].share_pct == 50.0
        assert lines[0].amount == 500.0
        assert lines[1].share_pct == 50.0
        assert lines[1].amount == 500.0

        je = (
            db.query(models.JournalEntry)
            .filter_by(reference_type="ProfitAllocation", reference_id=alloc_id)
            .one()
        )
        assert je.entry_date == datetime.date.today()
        assert _line_tuples(db, je.id) == [
            (env["re_id"], 1000.0, 0.0),
            (env["p1_cur"], 0.0, 500.0),
            (env["p2_cur"], 0.0, 500.0),
        ]


class TestAllocateProfitSuccessLoss:
    def test_loss_line_orientation(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        period = _closed_period(
            db,
            f"Feb {PAST_YEAR}",
            datetime.date(PAST_YEAR, 2, 1),
            datetime.date(PAST_YEAR, 2, 28),
            [(env["re_id"], 800.0, 0), (env["exp_id"], 0, 800.0)],
        )

        alloc_id, err = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)

        assert err == ""
        allocation = db.get(models.PartnerProfitAllocation, alloc_id)
        assert allocation.total_net_income == -800.0

        lines = (
            db.query(models.PartnerProfitAllocationLine)
            .filter_by(allocation_id=alloc_id)
            .order_by(models.PartnerProfitAllocationLine.partner_id)
            .all()
        )
        assert lines[0].amount == -400.0
        assert lines[1].amount == -400.0

        je = db.get(models.JournalEntry, allocation.journal_entry_id)
        assert _line_tuples(db, je.id) == [
            (env["re_id"], 0.0, 800.0),
            (env["p1_cur"], 400.0, 0.0),
            (env["p2_cur"], 400.0, 0.0),
        ]


class TestAllocateProfitRoundingRemainder:
    def test_last_partner_absorbs_remainder(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        bob = db.get(models.Partner, env["p2_id"])
        bob.profit_share_pct = 66.67
        alice = db.get(models.Partner, env["p1_id"])
        alice.profit_share_pct = 33.33
        db.commit()

        period = _closed_period(
            db,
            f"Mar {PAST_YEAR}",
            datetime.date(PAST_YEAR, 3, 1),
            datetime.date(PAST_YEAR, 3, 31),
            [(env["inc_id"], 100.01, 0), (env["re_id"], 0, 100.01)],
        )

        alloc_id, err = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)
        assert err == ""

        line_map = {
            ln.partner_id: ln.amount
            for ln in db.query(models.PartnerProfitAllocationLine)
            .filter_by(allocation_id=alloc_id)
            .all()
        }
        assert line_map[env["p1_id"]] == 33.33
        assert line_map[env["p2_id"]] == 66.68
        assert round(sum(line_map.values()), 2) == 100.01


class TestAllocateProfitGuards:
    def test_fiscal_period_not_found(self, session, alloc_env):
        db, _ = session
        n_alloc = _count(db, models.PartnerProfitAllocation)

        alloc_id, err = app.allocate_profit_to_partners(db, 99999, ALLOCATOR_ID)

        assert alloc_id is None
        assert err == "Fiscal period not found."
        assert _count(db, models.PartnerProfitAllocation) == n_alloc

    def test_period_not_closed(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        period = _closed_period(
            db,
            "Open",
            datetime.date(2026, 4, 1),
            datetime.date(2026, 4, 30),
            [(env["inc_id"], 100.0, 0), (env["re_id"], 0, 100.0)],
            closed=False,
        )
        n_alloc = _count(db, models.PartnerProfitAllocation)

        alloc_id, err = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)

        assert alloc_id is None
        assert err == "Period must be closed before allocating profit."
        assert _count(db, models.PartnerProfitAllocation) == n_alloc

    def test_no_closing_je(self, session, alloc_env):
        db, _ = session
        period = models.FiscalPeriod(
            name="No JE",
            start_date=datetime.date(2026, 5, 1),
            end_date=datetime.date(2026, 5, 31),
            is_closed=True,
            closed_at=datetime.date.today(),
        )
        db.add(period)
        db.commit()

        alloc_id, err = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)

        assert alloc_id is None
        assert err == "Period has no closing JE. Close the period first."

    def test_already_allocated(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        period = _closed_period(
            db,
            f"Apr {PAST_YEAR}",
            datetime.date(PAST_YEAR, 4, 1),
            datetime.date(PAST_YEAR, 4, 30),
            [(env["inc_id"], 500.0, 0), (env["re_id"], 0, 500.0)],
        )
        first_id, err1 = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)
        assert err1 == ""

        alloc_id, err2 = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)

        assert alloc_id is None
        assert err2 == f"Period 'Apr {PAST_YEAR}' already has an active allocation (#{first_id})."

    def test_zero_net_income(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        # Closing JE with no RE line → _get_period_net_income_from_je returns 0.0
        period = _closed_period(
            db,
            "Zero NI",
            datetime.date(PAST_YEAR, 5, 1),
            datetime.date(PAST_YEAR, 5, 31),
            [(env["inc_id"], 1000.0, 0), (env["exp_id"], 0, 1000.0)],
        )
        n_alloc = _count(db, models.PartnerProfitAllocation)

        alloc_id, err = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)

        assert alloc_id is None
        assert err == "Net income for 'Zero NI' is zero — nothing to allocate."
        assert _count(db, models.PartnerProfitAllocation) == n_alloc

    def test_no_active_partners(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        for pid in (env["p1_id"], env["p2_id"]):
            db.get(models.Partner, pid).is_active = False
        db.commit()
        period = _closed_period(
            db,
            "Jul 2026",
            datetime.date(2026, 7, 1),
            datetime.date(2026, 7, 31),
            [(env["inc_id"], 100.0, 0), (env["re_id"], 0, 100.0)],
        )

        alloc_id, err = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)

        assert alloc_id is None
        assert err == "No active partners defined."

    def test_guard_failure_posts_zero_commits(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        period = _closed_period(
            db,
            "Guard Commit",
            datetime.date(2026, 4, 1),
            datetime.date(2026, 4, 30),
            [(env["inc_id"], 100.0, 0), (env["re_id"], 0, 100.0)],
            closed=False,
        )

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            alloc_id, err = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)

        assert alloc_id is None
        assert err == "Period must be closed before allocating profit."
        assert mock_commit.call_count == 0

    def test_share_mismatch(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        db.get(models.Partner, env["p2_id"]).profit_share_pct = 30.0
        db.commit()
        period = _closed_period(
            db,
            "Aug 2026",
            datetime.date(2026, 8, 1),
            datetime.date(2026, 8, 31),
            [(env["inc_id"], 100.0, 0), (env["re_id"], 0, 100.0)],
        )

        alloc_id, err = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)

        assert alloc_id is None
        assert err == "Partner shares sum to 80.00% — must equal 100%."


class TestAllocateProfitCommitAudit:
    def test_success_posts_three_commits_and_audit(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        period = _closed_period(
            db,
            f"Sep {PAST_YEAR}",
            datetime.date(PAST_YEAR, 9, 1),
            datetime.date(PAST_YEAR, 9, 30),
            [(env["inc_id"], 250.0, 0), (env["re_id"], 0, 250.0)],
        )

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            alloc_id, err = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)
            assert err == ""
            assert mock_commit.call_count == 3

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="ProfitAllocation",
                entity_type="PartnerProfitAllocation",
                entity_id=alloc_id,
            )
            .one()
        )
        assert audit.description == f"Allocated Sep {PAST_YEAR}: net 250.00 → 2 partners"
        assert audit.performed_by == app._DEV_USER["username"]


class TestVoidProfitAllocationSuccess:
    def test_reverses_je_and_void_fields(self, session, alloc_env):
        db, cid = session
        env = alloc_env
        period = _closed_period(
            db,
            f"Oct {PAST_YEAR}",
            datetime.date(PAST_YEAR, 10, 1),
            datetime.date(PAST_YEAR, 10, 31),
            [(env["inc_id"], 300.0, 0), (env["re_id"], 0, 300.0)],
        )
        alloc_id, _ = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)
        allocation = db.get(models.PartnerProfitAllocation, alloc_id)
        original_je_id = allocation.journal_entry_id
        n_je = _count(db, models.JournalEntry)

        err = app.void_profit_allocation(db, alloc_id, VOIDER_ID, VOID_REASON)

        assert err == ""
        db.refresh(allocation)
        assert allocation.is_void is True
        assert allocation.voided_by_id == VOIDER_ID
        assert allocation.void_reason == VOID_REASON
        assert allocation.voided_at is not None
        assert _count(db, models.JournalEntry) == n_je + 1
        (
            db.query(models.JournalEntry)
            .filter_by(reference_type="Reversal", reference_id=original_je_id)
            .one()
        )


class TestVoidProfitAllocationErrors:
    def test_missing_allocation_no_commit(self, session, alloc_env):
        db, _ = session
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.void_profit_allocation(db, 99999, VOIDER_ID, VOID_REASON)
        assert err == "Allocation not found or already voided."
        assert mock_commit.call_count == 0

    def test_already_voided_no_commit(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        period = _closed_period(
            db,
            f"Nov {PAST_YEAR}",
            datetime.date(PAST_YEAR, 11, 1),
            datetime.date(PAST_YEAR, 11, 30),
            [(env["inc_id"], 100.0, 0), (env["re_id"], 0, 100.0)],
        )
        alloc_id, _ = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)
        assert app.void_profit_allocation(db, alloc_id, VOIDER_ID, VOID_REASON) == ""

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.void_profit_allocation(db, alloc_id, VOIDER_ID, "again")
        assert err == "Allocation not found or already voided."
        assert mock_commit.call_count == 0

    def test_empty_reason_no_commit(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        period = _closed_period(
            db,
            f"Dec {PAST_YEAR}",
            datetime.date(PAST_YEAR, 12, 1),
            datetime.date(PAST_YEAR, 12, 31),
            [(env["inc_id"], 100.0, 0), (env["re_id"], 0, 100.0)],
        )
        alloc_id, _ = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.void_profit_allocation(db, alloc_id, VOIDER_ID, "  ")
        assert err == "Void reason is required."
        assert mock_commit.call_count == 0


class TestVoidProfitAllocationYecGuard:
    def test_blocks_with_period_span_message_no_reversal(self, session, alloc_env):
        db, cid = session
        env = alloc_env
        period = _closed_period(
            db,
            "Jan 2025",
            datetime.date(2025, 1, 1),
            datetime.date(2025, 1, 31),
            [(env["inc_id"], 400.0, 0), (env["re_id"], 0, 400.0)],
        )
        alloc_id, _ = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)
        allocation = db.get(models.PartnerProfitAllocation, alloc_id)
        n_je = _count(db, models.JournalEntry)
        _insert_closed_yec(db, cid)

        err = app.void_profit_allocation(db, alloc_id, VOIDER_ID, VOID_REASON)

        assert err == VOID_ALLOCATION_MSG
        db.refresh(allocation)
        assert allocation.is_void is False
        assert _count(db, models.JournalEntry) == n_je


class TestVoidProfitAllocationCommitAudit:
    def test_void_posts_three_commits_and_audit(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        period = _closed_period(
            db,
            "Allocate Audit",
            datetime.date(PAST_YEAR, 2, 1),
            datetime.date(PAST_YEAR, 2, 28),
            [(env["inc_id"], 150.0, 0), (env["re_id"], 0, 150.0)],
        )
        alloc_id, _ = app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            err = app.void_profit_allocation(db, alloc_id, VOIDER_ID, VOID_REASON)
            assert err == ""
            assert mock_commit.call_count == 3

        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action="Void",
                entity_type="PartnerProfitAllocation",
                entity_id=alloc_id,
            )
            .one()
        )
        assert (
            audit.description
            == f"Voided profit allocation for period #{period.id} — {VOID_REASON}"
        )
        assert audit.performed_by == app._DEV_USER["username"]


class TestAllocateAllPending:
    def test_allocates_closed_unallocated_periods_in_order(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        p1 = _closed_period(
            db,
            "Period B",
            datetime.date(PAST_YEAR, 2, 1),
            datetime.date(PAST_YEAR, 2, 28),
            [(env["inc_id"], 100.0, 0), (env["re_id"], 0, 100.0)],
        )
        p2 = _closed_period(
            db,
            "Period A",
            datetime.date(PAST_YEAR, 1, 1),
            datetime.date(PAST_YEAR, 1, 31),
            [(env["inc_id"], 200.0, 0), (env["re_id"], 0, 200.0)],
        )
        app.allocate_profit_to_partners(db, p1.id, ALLOCATOR_ID)

        results = app._allocate_all_pending(db, ALLOCATOR_ID)

        assert results == [("Period A", results[0][1], "")]
        assert results[0][1] is not None
        assert db.get(models.PartnerProfitAllocation, results[0][1]).total_net_income == 200.0

    def test_skips_already_allocated_periods(self, session, alloc_env):
        db, _ = session
        env = alloc_env
        period = _closed_period(
            db,
            "Only One",
            datetime.date(PAST_YEAR, 3, 1),
            datetime.date(PAST_YEAR, 3, 31),
            [(env["inc_id"], 50.0, 0), (env["re_id"], 0, 50.0)],
        )
        app.allocate_profit_to_partners(db, period.id, ALLOCATOR_ID)

        assert app._allocate_all_pending(db, ALLOCATOR_ID) == []
