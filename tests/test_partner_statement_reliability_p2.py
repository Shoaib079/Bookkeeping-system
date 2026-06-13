"""PARTNER-STATEMENT-P2 — reliable balances, line coverage, export structure."""
from __future__ import annotations

import datetime
import inspect
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app
from registry.partner_statement import (
    build_partner_statement,
    check_partner_account_breakdown,
    partner_statement_account_breakdown_export_rows,
    partner_statement_closing_breakdown,
    partner_statement_opening_breakdown,
    partner_statement_preset_range,
    partner_statement_to_export_df,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True


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
            name="Test Co",
            slug="test_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        yield s


def _make_coa(session, code, name, acct_type):
    acct = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        balance=0.0,
        is_active=True,
    )
    session.add(acct)
    session.flush()
    return acct


def _make_partner(session, name, pct, cap_id, cur_id, adv_id, *, active=True):
    p = models.Partner(
        name=name,
        profit_share_pct=pct,
        capital_account_id=cap_id,
        current_account_id=cur_id,
        advance_account_id=adv_id,
        is_active=active,
        created_at=datetime.datetime.now(),
    )
    session.add(p)
    session.flush()
    return p


def _make_bank(session):
    _make_coa(session, "1100", "Cash", "Asset")
    ba = models.BankAccount(
        name="Cash",
        currency="TRY",
        balance=10000.0,
        is_active=True,
        kind="bank",
    )
    session.add(ba)
    session.flush()
    return ba


def _make_period(session, name, start, end, *, closed=False):
    fp = models.FiscalPeriod(
        name=name,
        start_date=start,
        end_date=end,
        is_closed=closed,
        closed_at=datetime.date.today() if closed else None,
    )
    session.add(fp)
    session.flush()
    return fp


def _make_allocation_line(session, period_id, partner_id, amount, *, re_acct, cur_acct, je_date=None):
    alloc = models.PartnerProfitAllocation(
        fiscal_period_id=period_id,
        allocated_at=datetime.datetime.now(),
        allocated_by_id=None,
        total_net_income=amount,
        is_void=False,
        created_at=datetime.datetime.now(),
    )
    session.add(alloc)
    session.flush()
    je_date = je_date or datetime.date.today()
    if amount >= 0:
        lines = [(re_acct.id, amount, 0), (cur_acct.id, 0, amount)]
    else:
        lines = [(re_acct.id, 0, abs(amount)), (cur_acct.id, abs(amount), 0)]
    je = app.create_journal_entry(
        session,
        je_date,
        f"Profit Allocation for period {period_id}",
        "ProfitAllocation",
        alloc.id,
        lines,
    )
    alloc.journal_entry_id = je.id
    session.add(
        models.PartnerProfitAllocationLine(
            allocation_id=alloc.id,
            partner_id=partner_id,
            share_pct=100.0,
            amount=amount,
        )
    )
    session.commit()
    return alloc


@pytest.fixture()
def partner_env(session):
    re_acct = _make_coa(session, "3100", "Retained Earnings", "Equity")
    cap_acct = _make_coa(session, "3501", "Bob Capital", "Equity")
    cur_acct = _make_coa(session, "3601", "Bob Current", "Equity")
    adv_acct = _make_coa(session, "1501", "Bob Advances", "Asset")
    bank = _make_bank(session)
    partner = _make_partner(session, "Bob", 100.0, cap_acct.id, cur_acct.id, adv_acct.id)
    session.commit()
    return {
        "partner": partner,
        "bank_id": bank.id,
        "re_id": re_acct.id,
        "cur_id": cur_acct.id,
    }


def _stmt(session, partner_id, d_from, d_to):
    return build_partner_statement(
        session,
        partner_id,
        d_from,
        d_to,
        app.calculate_account_balance_for_period,
    )


class TestAccountBreakdownIdentity:
    def test_opening_capital_current_advances_match_position(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        d_from = datetime.date(2025, 6, 1)
        d_to = datetime.date(2025, 6, 30)
        app.post_partner_movement(
            session, pid, "CapitalContribution", 1000.0,
            datetime.date(2025, 6, 5), bank_account_id=bank_id, created_by_id=1,
        )
        app.post_partner_movement(
            session, pid, "Advance", 150.0,
            datetime.date(2025, 6, 10), bank_account_id=bank_id, created_by_id=1,
        )
        stmt = _stmt(session, pid, d_from, d_to)
        assert check_partner_account_breakdown(
            stmt.opening_capital, stmt.opening_current, stmt.opening_advances,
            stmt.opening_position,
        )
        assert check_partner_account_breakdown(
            stmt.closing_capital, stmt.closing_current, stmt.closing_advances,
            stmt.closing_position,
        )
        opening = partner_statement_opening_breakdown(stmt)
        closing = partner_statement_closing_breakdown(stmt)
        assert opening.net_position == stmt.opening_position
        assert closing.net_position == stmt.closing_position
        assert closing.capital == stmt.closing_capital
        assert closing.current == stmt.closing_current
        assert closing.advances == stmt.closing_advances


class TestAllLineTypes:
    def test_movement_and_allocation_lines_in_summary_and_detail(
        self, session, partner_env
    ):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        re_acct = session.get(models.ChartOfAccounts, partner_env["re_id"])
        cur_acct = session.get(models.ChartOfAccounts, partner_env["cur_id"])
        d_from = datetime.date(2025, 7, 1)
        d_to = datetime.date(2025, 7, 31)

        for mtype, amt in (
            ("CapitalContribution", 500.0),
            ("Drawing", 50.0),
            ("Salary", 25.0),
            ("Advance", 100.0),
            ("Repayment", 30.0),
            ("AdvanceOffset", 20.0),
        ):
            if mtype == "AdvanceOffset":
                app.post_partner_movement(session, pid, mtype, amt, d_from, created_by_id=1)
            else:
                app.post_partner_movement(
                    session, pid, mtype, amt, d_from,
                    bank_account_id=bank_id, created_by_id=1,
                )

        period = _make_period(
            session, "Jul 2025", d_from, d_to, closed=True,
        )
        _make_allocation_line(
            session, period.id, pid, 200.0, re_acct=re_acct, cur_acct=cur_acct,
        )

        stmt = _stmt(session, pid, d_from, d_to)
        assert stmt.capital_contributions == 500.0
        assert stmt.drawings == 50.0
        assert stmt.salary == 25.0
        assert stmt.advances_taken == 100.0
        assert stmt.repayments == 30.0
        assert stmt.advance_offsets == 20.0
        assert stmt.profit_allocated == 200.0

        detail_types = {ln.type_key for ln in stmt.detail_lines}
        assert "CapitalContribution" in detail_types
        assert "Drawing" in detail_types
        assert "Salary" in detail_types
        assert "Advance" in detail_types
        assert "Repayment" in detail_types
        assert "AdvanceOffset" in detail_types
        assert "ProfitAllocated" in detail_types


class TestExportAccountBreakdown:
    def test_export_includes_account_balance_rows(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        app.post_partner_movement(
            session, pid, "CapitalContribution", 800.0,
            datetime.date(2025, 8, 1), bank_account_id=bank_id, created_by_id=1,
        )
        stmt = _stmt(session, pid, datetime.date(2025, 8, 1), datetime.date(2025, 8, 31))
        breakdown = partner_statement_account_breakdown_export_rows(stmt)
        lines = {row["Line"]: row["Amount"] for row in breakdown}
        assert lines["Capital"] == stmt.closing_capital
        assert lines["Current account"] == stmt.closing_current
        assert lines["Advances"] == stmt.closing_advances
        assert lines["Net partner position"] == stmt.closing_position

        export_df = partner_statement_to_export_df(stmt)
        sections = export_df["Section"].dropna().tolist()
        assert "— Account balances —" in sections
        assert "Opening accounts" in sections
        assert "Closing accounts" in sections


class TestDatePresets:
    def test_preset_ranges_for_statement_filters(self):
        today = datetime.date(2025, 6, 15)
        m_from, m_to = partner_statement_preset_range("month", today)
        assert m_from == datetime.date(2025, 6, 1)
        assert m_to == today
        q_from, q_to = partner_statement_preset_range("quarter", today)
        assert q_from == datetime.date(2025, 4, 1)
        assert q_to == today
        y_from, y_to = partner_statement_preset_range("year", today)
        assert y_from == datetime.date(2025, 1, 1)
        assert y_to == today
        assert partner_statement_preset_range("custom", today) == (None, None)


class TestUIContract:
    def test_statement_has_account_summary_kpi_grid(self):
        render_src = inspect.getsource(app._render_partner_statement)
        assert "partner.stmt.account_summary_title" in render_src
        assert "_partner_stmt_account_kpi_items" in render_src
        assert "render_kpi_grid" in render_src
        kpi_src = inspect.getsource(app._partner_stmt_account_kpi_items)
        assert "partner.stmt.kpi_capital" in kpi_src
        assert "partner.stmt.kpi_current" in kpi_src
        assert "partner.stmt.kpi_advances" in kpi_src
        assert "partner.stmt.kpi_net_position" in kpi_src

    def test_statement_has_date_range_controls(self):
        src = inspect.getsource(app._render_partner_statement)
        assert "partner_stmt_preset" in src
        assert "partner_stmt_from" in src
        assert "partner_stmt_to" in src
        assert "partner_statement_preset_range" in src
