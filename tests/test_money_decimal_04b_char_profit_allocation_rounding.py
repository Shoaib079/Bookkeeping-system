"""MONEY-DECIMAL-04b-CHAR — profit/loss allocation rounding characterization.

Deep-pins float/Python ``round`` allocation semantics before Decimal kernel changes.
Tests only — no production changes.

Cross-ref: docs/MONEY_DECIMAL_04B_PROFIT_ALLOCATION_CHAR.md
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from db import Base

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

import app  # noqa: F401 — bootstrap import graph

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

from registry.coa_seed import seed_chart_of_accounts_for_company
from services import posting
from services.read_balances import calculate_account_balance

ROOT = Path(__file__).resolve().parents[1]
POSTING_PATH = ROOT / "services" / "posting.py"

COMPANY_ID = 1
ALLOCATOR_ID = 1
VOIDER_ID = 2
VOID_REASON = "MD-04b-CHAR void"
POST_DATE = datetime.date(2025, 6, 15)
PERIOD_START = datetime.date(2025, 6, 1)
PERIOD_END = datetime.date(2025, 6, 30)

SHARE_MISMATCH_MSG = "Partner shares sum to 80.00% — must equal 100%."
NO_PARTNERS_MSG = "No active partners defined."


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        s.add(
            models.Company(
                name="MD-04b CHAR Co",
                slug="md04b_char",
                is_active=True,
                created_at=datetime.datetime.now(),
            )
        )
        s.flush()
        seed_chart_of_accounts_for_company(s, COMPANY_ID)
        s.commit()
        yield s


def _acct_id(session, name: str) -> int:
    acct = posting.get_account_by_name(session, name, company_id=COMPANY_ID)
    assert acct is not None
    return acct.id


def _seed_partners(session, pcts: tuple[float, ...]) -> list[models.Partner]:
    partners = []
    for i, pct in enumerate(pcts, start=1):
        cap = models.ChartOfAccounts(
            account_code=f"351{i}",
            account_name=f"P{i} Capital MD04b",
            account_type="Equity",
            balance=0.0,
            is_active=True,
            company_id=COMPANY_ID,
        )
        cur = models.ChartOfAccounts(
            account_code=f"361{i}",
            account_name=f"P{i} Current MD04b",
            account_type="Equity",
            balance=0.0,
            is_active=True,
            company_id=COMPANY_ID,
        )
        adv = models.ChartOfAccounts(
            account_code=f"151{i}",
            account_name=f"P{i} Advances MD04b",
            account_type="Asset",
            balance=0.0,
            is_active=True,
            company_id=COMPANY_ID,
        )
        session.add_all([cap, cur, adv])
        session.flush()
        p = models.Partner(
            name=f"Partner {i}",
            profit_share_pct=pct,
            capital_account_id=cap.id,
            current_account_id=cur.id,
            advance_account_id=adv.id,
            is_active=True,
            company_id=COMPANY_ID,
            created_at=datetime.datetime.now(),
        )
        session.add(p)
        session.flush()
        partners.append(p)
    session.commit()
    return partners


def _closed_period(
    session,
    *,
    revenue: float = 0.0,
    expense: float = 0.0,
    pcts: tuple[float, ...] = (50.0, 50.0),
) -> models.FiscalPeriod:
    _seed_partners(session, pcts)
    period = models.FiscalPeriod(
        name="Jun 2025",
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        is_closed=False,
        company_id=COMPANY_ID,
    )
    session.add(period)
    session.flush()
    cash_id = _acct_id(session, "Cash")
    inc_id = _acct_id(session, "Sales Revenue")
    exp_id = _acct_id(session, "Rent Expense")
    if revenue:
        posting.create_journal_entry(
            session, POST_DATE, "md04b revenue", "Sale", None,
            [(cash_id, revenue, 0.0), (inc_id, 0.0, revenue)], company_id=COMPANY_ID,
        )
    if expense:
        posting.create_journal_entry(
            session, POST_DATE, "md04b expense", "Expense", None,
            [(exp_id, expense, 0.0), (cash_id, 0.0, expense)], company_id=COMPANY_ID,
        )
    session.commit()
    posting.close_fiscal_period(session, period.id, company_id=COMPANY_ID)
    session.commit()
    return period


def _allocation_lines(session, alloc_id: int) -> list[models.PartnerProfitAllocationLine]:
    return (
        session.query(models.PartnerProfitAllocationLine)
        .filter_by(allocation_id=alloc_id)
        .order_by(models.PartnerProfitAllocationLine.partner_id)
        .all()
    )


def _je_balanced(session, je_id: int) -> bool:
    lines = session.query(models.JournalEntryLine).filter_by(journal_entry_id=je_id).all()
    deb = sum(l.debit or 0 for l in lines)
    cred = sum(l.credit or 0 for l in lines)
    return abs(deb - cred) <= 0.01


def _expected_shares(abs_income: float, pcts: tuple[float, ...]) -> list[float]:
    """Mirror posting.allocate_profit_to_partners share loop (Python round, last absorbs)."""
    running = 0.0
    shares: list[float] = []
    for i, pct in enumerate(pcts):
        if i == len(pcts) - 1:
            share = round(abs_income - running, 2)
        else:
            share = round(abs_income * pct / 100.0, 2)
            running += share
        shares.append(share)
    return shares


# ── Source contract ───────────────────────────────────────────────────────────


class TestAllocationSourceContract:
    @pytest.fixture(scope="class")
    def posting_source(self) -> str:
        return POSTING_PATH.read_text(encoding="utf-8")

    def test_uses_money_to_float_not_builtin_round(self, posting_source: str):
        start = posting_source.index("def allocate_profit_to_partners")
        end = posting_source.index("def void_profit_allocation", start)
        block = posting_source[start:end]
        assert "_allocation_share_float" in block
        assert "return money_to_float(value)" in posting_source
        assert "round(abs_income * p.profit_share_pct / 100.0, 2)" not in block
        assert "round(abs_income - running, 2)" not in block
        assert "quantize_money" not in block

    def test_validate_shares_tolerance_in_source(self, posting_source: str):
        assert "99.99 <= total <= 100.01" in posting_source


# ── 1. Profit allocation ──────────────────────────────────────────────────────


class TestProfitAllocationRounding:
    def test_100_01_split_50_50_matches_md02(self, session):
        period = _closed_period(session, revenue=100.01, expense=0.0, pcts=(50.0, 50.0))
        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        assert err == ""
        amounts = [round(ln.amount, 2) for ln in _allocation_lines(session, alloc_id)]
        assert sorted(amounts) == [50.0, 50.01]
        assert round(sum(amounts), 2) == 100.01

    def test_100_00_uneven_33_33_66_67(self, session):
        period = _closed_period(session, revenue=100.0, expense=0.0, pcts=(33.33, 66.67))
        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        assert err == ""
        lines = _allocation_lines(session, alloc_id)
        expected = _expected_shares(100.0, (33.33, 66.67))
        assert [round(ln.amount, 2) for ln in lines] == expected
        assert round(sum(ln.amount for ln in lines), 2) == 100.0

    def test_100_01_split_three_partners_last_absorbs(self, session):
        pcts = (33.33, 33.33, 33.34)
        period = _closed_period(session, revenue=100.01, expense=0.0, pcts=pcts)
        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        assert err == ""
        amounts = [round(ln.amount, 2) for ln in _allocation_lines(session, alloc_id)]
        assert amounts == _expected_shares(100.01, pcts)
        assert round(sum(amounts), 2) == 100.01

    def test_repeating_decimal_shares_33_33_66_67_on_100_01(self, session):
        """PS-P6-3-CHAR pin: 33.33/66.67 on 100.01 → 33.33 + 66.68."""
        pcts = (33.33, 66.67)
        period = _closed_period(session, revenue=100.01, expense=0.0, pcts=pcts)
        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        assert err == ""
        by_partner = {
            ln.partner_id: round(ln.amount, 2)
            for ln in _allocation_lines(session, alloc_id)
        }
        partners = (
            session.query(models.Partner)
            .filter_by(company_id=COMPANY_ID, is_active=True)
            .order_by(models.Partner.id)
            .all()
        )
        assert by_partner[partners[0].id] == 33.33
        assert by_partner[partners[1].id] == 66.68
        assert round(sum(by_partner.values()), 2) == 100.01


# ── 2. Loss allocation ────────────────────────────────────────────────────────


class TestLossAllocationRounding:
    def test_loss_100_01_split_50_50_negative_lines(self, session):
        period = _closed_period(session, revenue=0.0, expense=100.01, pcts=(50.0, 50.0))
        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        assert err == ""
        amounts = sorted(round(ln.amount, 2) for ln in _allocation_lines(session, alloc_id))
        assert amounts == [-50.01, -50.0]
        assert round(sum(amounts), 2) == -100.01

    def test_loss_je_partner_debits_sum_to_abs_loss(self, session):
        period = _closed_period(session, revenue=0.0, expense=100.01, pcts=(50.0, 50.0))
        alloc_id, _ = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        alloc = session.get(models.PartnerProfitAllocation, alloc_id)
        je = session.get(models.JournalEntry, alloc.journal_entry_id)
        re_id = _acct_id(session, "Retained Earnings")
        re_credit = sum(l.credit or 0 for l in je.lines if l.account_id == re_id)
        partner_debits = sum(l.debit or 0 for l in je.lines if l.account_id != re_id)
        assert round(re_credit, 2) == 100.01
        assert round(partner_debits, 2) == 100.01
        assert _je_balanced(session, je.id)


# ── 3. Journal entry orientation ──────────────────────────────────────────────


class TestAllocationJournalEntryOrientation:
    def test_profit_dr_re_cr_partner_current(self, session):
        period = _closed_period(session, revenue=100.01, expense=0.0, pcts=(50.0, 50.0))
        alloc_id, _ = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        alloc = session.get(models.PartnerProfitAllocation, alloc_id)
        je = session.get(models.JournalEntry, alloc.journal_entry_id)
        re_id = _acct_id(session, "Retained Earnings")
        re_lines = [l for l in je.lines if l.account_id == re_id]
        partner_lines = [l for l in je.lines if l.account_id != re_id]
        assert len(re_lines) == 1
        assert round(re_lines[0].debit or 0, 2) == 100.01
        assert round(re_lines[0].credit or 0, 2) == 0.0
        assert all((l.credit or 0) > 0 and (l.debit or 0) == 0 for l in partner_lines)
        assert round(sum(l.credit or 0 for l in partner_lines), 2) == 100.01
        assert _je_balanced(session, je.id)

    def test_loss_dr_partner_current_cr_re(self, session):
        period = _closed_period(session, revenue=0.0, expense=100.01, pcts=(50.0, 50.0))
        alloc_id, _ = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        alloc = session.get(models.PartnerProfitAllocation, alloc_id)
        je = session.get(models.JournalEntry, alloc.journal_entry_id)
        re_id = _acct_id(session, "Retained Earnings")
        re_lines = [l for l in je.lines if l.account_id == re_id]
        partner_lines = [l for l in je.lines if l.account_id != re_id]
        assert round(re_lines[0].credit or 0, 2) == 100.01
        assert all((l.debit or 0) > 0 and (l.credit or 0) == 0 for l in partner_lines)
        assert _je_balanced(session, je.id)


# ── 4. Void allocation ────────────────────────────────────────────────────────


class TestVoidProfitAllocation:
    def test_void_creates_reversal_and_void_fields(self, session):
        period = _closed_period(session, revenue=100.01, expense=0.0, pcts=(50.0, 50.0))
        alloc_id, _ = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        allocation = session.get(models.PartnerProfitAllocation, alloc_id)
        original_je_id = allocation.journal_entry_id
        n_je = session.query(models.JournalEntry).count()

        err = posting.void_profit_allocation(
            session, alloc_id, VOIDER_ID, VOID_REASON, company_id=COMPANY_ID,
        )
        assert err == ""
        session.refresh(allocation)
        assert allocation.is_void is True
        assert allocation.voided_by_id == VOIDER_ID
        assert allocation.void_reason == VOID_REASON
        assert allocation.voided_at is not None
        assert session.query(models.JournalEntry).count() == n_je + 1
        session.query(models.JournalEntry).filter_by(
            reference_type="Reversal", reference_id=original_je_id,
        ).one()

    def test_void_partner_current_net_zero(self, session):
        period = _closed_period(session, revenue=100.01, expense=0.0, pcts=(50.0, 50.0))
        partners = (
            session.query(models.Partner)
            .filter_by(company_id=COMPANY_ID, is_active=True)
            .order_by(models.Partner.id)
            .all()
        )
        cur_accts = [
            session.get(models.ChartOfAccounts, p.current_account_id) for p in partners
        ]
        alloc_id, _ = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        assert any(
            calculate_account_balance(session, a, company_id=COMPANY_ID) != 0
            for a in cur_accts
        )
        posting.void_profit_allocation(
            session, alloc_id, VOIDER_ID, VOID_REASON, company_id=COMPANY_ID,
        )
        for acct in cur_accts:
            assert calculate_account_balance(session, acct, company_id=COMPANY_ID) == 0.0


# ── 5. Edge cases ─────────────────────────────────────────────────────────────


class TestAllocationEdgeCases:
    def test_001_net_income_two_partners(self, session):
        period = _closed_period(session, revenue=0.01, expense=0.0, pcts=(50.0, 50.0))
        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        assert err == ""
        amounts = [round(ln.amount, 2) for ln in _allocation_lines(session, alloc_id)]
        assert amounts == _expected_shares(0.01, (50.0, 50.0))
        assert round(sum(amounts), 2) == 0.01

    def test_001_net_income_three_partners_last_gets_all(self, session):
        pcts = (33.33, 33.33, 33.34)
        period = _closed_period(session, revenue=0.01, expense=0.0, pcts=pcts)
        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        assert err == ""
        amounts = [round(ln.amount, 2) for ln in _allocation_lines(session, alloc_id)]
        assert amounts == _expected_shares(0.01, pcts)
        assert amounts[-1] == 0.01
        assert amounts[0] == 0.0
        assert amounts[1] == 0.0

    def test_invalid_share_total_exact_message(self, session):
        _seed_partners(session, (50.0, 30.0))
        period = models.FiscalPeriod(
            name="Bad shares",
            start_date=PERIOD_START,
            end_date=PERIOD_END,
            is_closed=True,
            closed_at=datetime.date.today(),
            company_id=COMPANY_ID,
        )
        session.add(period)
        session.flush()
        re_id = _acct_id(session, "Retained Earnings")
        inc_id = _acct_id(session, "Sales Revenue")
        je = posting.create_journal_entry(
            session, POST_DATE, "close pin", "PeriodClose", period.id,
            [(inc_id, 100.0, 0.0), (re_id, 0.0, 100.0)], company_id=COMPANY_ID,
        )
        period.closing_je_id = je.id
        session.commit()

        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        assert alloc_id is None
        assert err == SHARE_MISMATCH_MSG

    def test_no_active_partners_exact_message(self, session):
        _seed_partners(session, (50.0, 50.0))
        for p in session.query(models.Partner).filter_by(company_id=COMPANY_ID).all():
            p.is_active = False
        session.commit()
        period = models.FiscalPeriod(
            name="No partners",
            start_date=PERIOD_START,
            end_date=PERIOD_END,
            is_closed=True,
            closed_at=datetime.date.today(),
            company_id=COMPANY_ID,
        )
        session.add(period)
        session.flush()
        re_id = _acct_id(session, "Retained Earnings")
        inc_id = _acct_id(session, "Sales Revenue")
        je = posting.create_journal_entry(
            session, POST_DATE, "close", "PeriodClose", period.id,
            [(inc_id, 100.0, 0.0), (re_id, 0.0, 100.0)], company_id=COMPANY_ID,
        )
        period.closing_je_id = je.id
        session.commit()

        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, ALLOCATOR_ID, company_id=COMPANY_ID,
        )
        assert alloc_id is None
        assert err == NO_PARTNERS_MSG
