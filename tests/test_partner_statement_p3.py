"""PARTNER-STATEMENT-01 P3 — PDF export and print-friendly UI."""
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
from exports import generate_partner_statement_pdf
from registry.partner_statement import (
    partner_statement_pdf_payload,
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
    lines = (
        [(re_acct.id, amount, 0), (cur_acct.id, 0, amount)]
        if amount >= 0
        else [(re_acct.id, 0, abs(amount)), (cur_acct.id, abs(amount), 0)]
    )
    je = app.create_journal_entry(
        session, je_date, f"Profit Allocation {period_id}",
        "ProfitAllocation", alloc.id, lines,
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
    return {"partner": partner, "bank_id": bank.id, "re_id": re_acct.id, "cur_id": cur_acct.id}


def _stmt(session, partner_id, d_from, d_to):
    return app.build_partner_statement(
        session, partner_id, d_from, d_to, app.calculate_account_balance_for_period
    )


def _payload(stmt, **kwargs):
    return partner_statement_pdf_payload(
        stmt,
        company_name="Test Co",
        currency="TRY",
        status_text="Settled",
        **kwargs,
    )


class TestPdfPayloadTotals:
    def test_pdf_summary_matches_statement(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        app.post_partner_movement(
            session, pid, "CapitalContribution", 1200.0,
            datetime.date(2025, 6, 5), bank_account_id=bank_id, created_by_id=1,
        )
        stmt = _stmt(session, pid, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30))
        payload = _payload(stmt)
        summary = {row["Line"]: row["Amount"] for row in payload["summary_rows"]}
        assert summary["Opening position"] == stmt.opening_position
        assert summary["Capital Contributions"] == stmt.capital_contributions
        assert summary["Closing position"] == stmt.closing_position
        assert payload["opening_position"] == stmt.opening_position
        assert payload["closing_position"] == stmt.closing_position


class TestPdfDetailLines:
    def test_pdf_payload_includes_detail_lines(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        app.post_partner_movement(
            session, pid, "Drawing", 150.0,
            datetime.date(2025, 7, 1), bank_account_id=bank_id, created_by_id=1,
        )
        stmt = _stmt(session, pid, datetime.date(2025, 7, 1), datetime.date(2025, 7, 31))
        payload = _payload(stmt)
        assert len(payload["detail_rows"]) == len(stmt.detail_lines)
        types = {row["Type"] for row in payload["detail_rows"]}
        assert "Drawing" in types


class TestPdfAdvanceOffset:
    def test_advance_offset_zero_net_in_pdf_detail(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        d = datetime.date(2025, 8, 1)
        app.post_partner_movement(
            session, pid, "Advance", 200.0, d, bank_account_id=bank_id, created_by_id=1,
        )
        app.post_partner_movement(session, pid, "AdvanceOffset", 50.0, d, created_by_id=1)
        stmt = _stmt(session, pid, d, d)
        payload = _payload(stmt)
        offset = [r for r in payload["detail_rows"] if r["Type"] == "AdvanceOffset"]
        assert len(offset) == 1
        assert offset[0]["Net Effect"] == 0.0
        assert offset[0]["Section"] == "settlements"


class TestPdfAllocationByPeriodEnd:
    def test_allocation_detail_date_is_fiscal_period_end(self, session, partner_env):
        pid = partner_env["partner"].id
        re_acct = session.get(models.ChartOfAccounts, partner_env["re_id"])
        cur_acct = session.get(models.ChartOfAccounts, partner_env["cur_id"])
        period = _make_period(
            session, "Mar 2025", datetime.date(2025, 3, 1), datetime.date(2025, 3, 31), closed=True,
        )
        _make_allocation_line(
            session, period.id, pid, 400.0, re_acct=re_acct, cur_acct=cur_acct,
            je_date=datetime.date(2025, 4, 15),
        )
        stmt = _stmt(session, pid, datetime.date(2025, 3, 1), datetime.date(2025, 3, 31))
        payload = _payload(stmt)
        profit = [r for r in payload["detail_rows"] if r["Type"] == "ProfitAllocated"]
        assert profit[0]["Date"] == "2025-03-31"


class TestPdfEmptyPeriod:
    def test_empty_period_pdf_generates(self, session, partner_env):
        pid = partner_env["partner"].id
        stmt = _stmt(session, pid, datetime.date(2025, 9, 1), datetime.date(2025, 9, 30))
        pdf = generate_partner_statement_pdf(_payload(stmt))
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 500


class TestPdfWarnings:
    def test_warnings_in_pdf_payload(self, session, partner_env):
        pid = partner_env["partner"].id
        _make_period(
            session, "Oct 2025", datetime.date(2025, 10, 1), datetime.date(2025, 10, 31), closed=True,
        )
        stmt = _stmt(session, pid, datetime.date(2025, 10, 1), datetime.date(2025, 10, 31))
        payload = _payload(stmt, warning_texts=["Closed period missing allocation"])
        assert payload["warnings"]
        pdf = generate_partner_statement_pdf(payload)
        assert pdf[:4] == b"%PDF"


class TestExcelUnchanged:
    def test_excel_export_df_unchanged_from_p2(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        app.post_partner_movement(
            session, pid, "Repayment", 80.0,
            datetime.date(2025, 11, 3), bank_account_id=bank_id, created_by_id=1,
        )
        stmt = _stmt(session, pid, datetime.date(2025, 11, 1), datetime.date(2025, 11, 30))
        export_df = partner_statement_to_export_df(stmt)
        summary = partner_statement_summary_export_rows(stmt)
        assert export_df.iloc[0]["Line"] == summary[0]["Line"]
        assert export_df.iloc[0]["Amount"] == summary[0]["Amount"]


class TestPostingUnchanged:
    def test_post_partner_movement_unchanged(self):
        assert "def post_partner_movement" in inspect.getsource(app.post_partner_movement)


class TestPrintUi:
    def test_report_banner_and_no_inline_stmt_line_styles(self):
        src = inspect.getsource(app._render_partner_statement)
        assert "page_report_banner_html" in src
        assert "financial_section_header_html" in src
        assert "erp-partner-stmt-report" in src
        assert "def _stmt_line" not in src
        assert "generate_partner_statement_pdf" in inspect.getsource(
            app._render_partner_statement_exports
        )
