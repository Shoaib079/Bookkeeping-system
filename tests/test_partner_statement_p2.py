"""PARTNER-STATEMENT-01 P2 — detail lines, running position, Excel export."""
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
    movement_net_position_effect,
    partner_statement_summary_export_rows,
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


class TestDetailRunningPosition:
    def test_last_running_line_reaches_closing_position(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        d_from = datetime.date(2025, 6, 1)
        d_to = datetime.date(2025, 6, 30)
        app.post_partner_movement(
            session, pid, "CapitalContribution", 1000.0,
            datetime.date(2025, 6, 5), bank_account_id=bank_id, created_by_id=1,
        )
        app.post_partner_movement(
            session, pid, "Drawing", 200.0,
            datetime.date(2025, 6, 12), bank_account_id=bank_id, created_by_id=1,
        )
        stmt = _stmt(session, pid, d_from, d_to)
        assert stmt.detail_lines
        assert stmt.detail_lines[-1].type_key == "closing"
        assert stmt.detail_lines[-1].running_position == stmt.closing_position
        activity = [ln for ln in stmt.detail_lines if ln.type_key not in ("opening", "closing")]
        assert activity[-1].running_position == stmt.closing_position


class TestAdvanceOffsetDetail:
    def test_advance_offset_detail_has_zero_net_effect(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        d = datetime.date(2025, 7, 10)
        app.post_partner_movement(
            session, pid, "Advance", 300.0, d, bank_account_id=bank_id, created_by_id=1,
        )
        app.post_partner_movement(session, pid, "AdvanceOffset", 100.0, d, created_by_id=1)
        stmt = _stmt(session, pid, d, d)
        offset_lines = [ln for ln in stmt.detail_lines if ln.type_key == "AdvanceOffset"]
        assert len(offset_lines) == 1
        assert offset_lines[0].net_effect == 0.0
        assert movement_net_position_effect("AdvanceOffset", 100.0) == 0.0
        assert offset_lines[0].section_key == "settlements"


class TestAllocationDetailByPeriodEnd:
    def test_profit_allocation_detail_uses_fiscal_period_end_date(
        self, session, partner_env
    ):
        pid = partner_env["partner"].id
        re_acct = session.get(models.ChartOfAccounts, partner_env["re_id"])
        cur_acct = session.get(models.ChartOfAccounts, partner_env["cur_id"])
        may = _make_period(
            session, "May 2025", datetime.date(2025, 5, 1), datetime.date(2025, 5, 31), closed=True,
        )
        _make_allocation_line(
            session, may.id, pid, 600.0, re_acct=re_acct, cur_acct=cur_acct,
            je_date=datetime.date(2025, 6, 20),
        )
        stmt = _stmt(session, pid, datetime.date(2025, 5, 1), datetime.date(2025, 5, 31))
        profit_lines = [ln for ln in stmt.detail_lines if ln.type_key == "ProfitAllocated"]
        assert len(profit_lines) == 1
        assert profit_lines[0].line_date == datetime.date(2025, 5, 31)
        assert profit_lines[0].net_effect == 600.0


class TestInactivePartnerP2:
    def test_inactive_partner_detail_lines_render(self, session, partner_env):
        partner = partner_env["partner"]
        bank_id = partner_env["bank_id"]
        app.post_partner_movement(
            session, partner.id, "CapitalContribution", 250.0,
            datetime.date(2025, 8, 1), bank_account_id=bank_id, created_by_id=1,
        )
        partner.is_active = False
        session.commit()
        stmt = _stmt(session, partner.id, datetime.date(2025, 8, 1), datetime.date(2025, 8, 31))
        assert stmt.detail_lines
        assert not stmt.partner_is_active


class TestEmptyPeriod:
    def test_empty_period_opening_equals_closing_in_detail(self, session, partner_env):
        pid = partner_env["partner"].id
        stmt = _stmt(session, pid, datetime.date(2025, 9, 1), datetime.date(2025, 9, 30))
        assert stmt.opening_position == stmt.closing_position
        assert stmt.reconciliation_ok
        assert len(stmt.detail_lines) == 2
        assert stmt.detail_lines[0].type_key == "opening"
        assert stmt.detail_lines[1].type_key == "closing"
        assert stmt.detail_lines[0].running_position == stmt.detail_lines[1].running_position


class TestExportTotals:
    def test_export_summary_matches_screen_totals(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        app.post_partner_movement(
            session, pid, "CapitalContribution", 1500.0,
            datetime.date(2025, 10, 5), bank_account_id=bank_id, created_by_id=1,
        )
        app.post_partner_movement(
            session, pid, "Advance", 100.0,
            datetime.date(2025, 10, 8), bank_account_id=bank_id, created_by_id=1,
        )
        stmt = _stmt(session, pid, datetime.date(2025, 10, 1), datetime.date(2025, 10, 31))
        summary = partner_statement_summary_export_rows(stmt)
        amounts = {row["Line"]: row["Amount"] for row in summary}
        assert amounts["Opening position"] == stmt.opening_position
        assert amounts["Capital Contributions"] == stmt.capital_contributions
        assert amounts["Advances Taken"] == stmt.advances_taken
        assert amounts["Closing position"] == stmt.closing_position
        export_df = partner_statement_to_export_df(stmt)
        assert not export_df.empty
        assert "Partner Statement" not in export_df.columns


class TestPostingUnchanged:
    def test_post_partner_movement_unchanged(self):
        src = inspect.getsource(app.post_partner_movement)
        assert "def post_partner_movement" in src
        assert "posting_service.post_partner_movement(" in src

    def test_ui_has_detail_expander_and_export(self):
        src = inspect.getsource(app._render_partner_statement)
        assert "partner.stmt.show_detail_lines" in src
        assert "partner_statement_to_export_df" in src
        assert "_render_partner_statement_exports" in src
        assert "df_to_excel_bytes" in inspect.getsource(app._render_partner_statement_exports)
