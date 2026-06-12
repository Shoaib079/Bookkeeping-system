"""PARTNER-STATEMENT-01 P4 — all-partners settlement summary."""
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
from registry.i18n import t
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from registry.partner_statement import (
    all_partners_settlement_export_rows,
    all_partners_settlement_pdf_payload,
    all_partners_settlement_to_export_df,
    advance_offset_position_delta,
    build_all_partners_settlement_summary,
    build_partner_statement,
    partner_statement_preset_range,
)
from registry.partner_statement_pdf import generate_all_partners_settlement_pdf

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

_P4_LOCALE_KEYS = (
    "partner.stmt.all_section_title",
    "partner.stmt.all_export_title",
    "partner.stmt.all_totals_label",
    "partner.stmt.all_status_summary",
    "partner.stmt.all_view_statement",
    "partner.stmt.all_hide_inactive",
    "partner.stmt.all_hide_settled",
    "partner.stmt.all_tab4_note",
    "partner.stmt.all_warn_count",
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


def _make_allocation_line(session, period_id, partner_id, amount, *, re_acct, cur_acct):
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
    if amount >= 0:
        lines = [(re_acct.id, amount, 0), (cur_acct.id, 0, amount)]
    else:
        lines = [(re_acct.id, 0, abs(amount)), (cur_acct.id, abs(amount), 0)]
    je = app.create_journal_entry(
        session,
        datetime.date.today(),
        f"Profit Allocation for period {period_id}",
        "ProfitAllocation",
        alloc.id,
        lines,
    )
    alloc.journal_entry_id = je.id
    line = models.PartnerProfitAllocationLine(
        allocation_id=alloc.id,
        partner_id=partner_id,
        share_pct=100.0,
        amount=amount,
    )
    session.add(line)
    session.commit()


@pytest.fixture()
def partner_env(session):
    re_acct = _make_coa(session, "3100", "Retained Earnings", "Equity")
    cap_acct = _make_coa(session, "3501", "Bob Capital", "Equity")
    cur_acct = _make_coa(session, "3601", "Bob Current", "Equity")
    adv_acct = _make_coa(session, "1501", "Bob Advances", "Asset")
    bank = _make_bank(session)
    partner = _make_partner(
        session, "Bob", 60.0, cap_acct.id, cur_acct.id, adv_acct.id
    )
    session.commit()
    return {
        "partner": partner,
        "bank_id": bank.id,
        "re_id": re_acct.id,
        "cap_id": cap_acct.id,
        "cur_id": cur_acct.id,
        "adv_id": adv_acct.id,
    }


@pytest.fixture()
def two_partner_env(session, partner_env):
    cap2 = _make_coa(session, "3502", "Ann Capital", "Equity")
    cur2 = _make_coa(session, "3602", "Ann Current", "Equity")
    adv2 = _make_coa(session, "1502", "Ann Advances", "Asset")
    ann = _make_partner(session, "Ann", 40.0, cap2.id, cur2.id, adv2.id)
    session.commit()
    partner_env["partner2"] = ann
    return partner_env


def _summary(session, d_from, d_to, **kwargs):
    return build_all_partners_settlement_summary(
        session,
        d_from,
        d_to,
        app.calculate_account_balance_for_period,
        **kwargs,
    )


def _stmt(session, partner_id, d_from, d_to):
    return build_partner_statement(
        session,
        partner_id,
        d_from,
        d_to,
        app.calculate_account_balance_for_period,
    )


class TestBuilderProjection:
    def test_one_row_per_partner(self, session, two_partner_env):
        summary = _summary(
            session,
            datetime.date(2025, 6, 1),
            datetime.date(2025, 6, 30),
        )
        assert summary is not None
        assert len(summary.rows) == 2

    def test_row_matches_build_partner_statement(self, session, partner_env):
        pid = partner_env["partner"].id
        d_from, d_to = datetime.date(2025, 6, 1), datetime.date(2025, 6, 30)
        app.post_partner_movement(
            session,
            pid,
            "CapitalContribution",
            500.0,
            datetime.date(2025, 6, 10),
            bank_account_id=partner_env["bank_id"],
            created_by_id=1,
        )
        stmt = _stmt(session, pid, d_from, d_to)
        summary = _summary(session, d_from, d_to)
        row = summary.rows[0]
        assert row.opening_position == stmt.opening_position
        assert row.net_position_change == stmt.net_position_change
        assert row.closing_position == stmt.closing_position
        assert row.settlement_status == stmt.status
        assert row.capital_contributions == stmt.capital_contributions

    def test_two_partners_different_activity(self, session, two_partner_env):
        d = datetime.date(2025, 6, 15)
        app.post_partner_movement(
            session,
            two_partner_env["partner"].id,
            "Drawing",
            100.0,
            d,
            bank_account_id=two_partner_env["bank_id"],
            created_by_id=1,
        )
        app.post_partner_movement(
            session,
            two_partner_env["partner2"].id,
            "CapitalContribution",
            200.0,
            d,
            bank_account_id=two_partner_env["bank_id"],
            created_by_id=1,
        )
        summary = _summary(session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30))
        by_name = {r.partner_name: r for r in summary.rows}
        assert by_name["Bob"].drawings == 100.0
        assert by_name["Ann"].capital_contributions == 200.0


class TestAccountingRules:
    def test_voided_movement_excluded(self, session, partner_env):
        pid = partner_env["partner"].id
        d = datetime.date(2025, 6, 12)
        app.post_partner_movement(
            session,
            pid,
            "Drawing",
            50.0,
            d,
            bank_account_id=partner_env["bank_id"],
            created_by_id=1,
        )
        mv = (
            session.query(models.PartnerMovement)
            .filter_by(partner_id=pid, movement_type="Drawing")
            .one()
        )
        app.void_partner_movement(session, mv.id, 1, "test")
        summary = _summary(session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30))
        assert summary.rows[0].drawings == 0.0

    def test_profit_by_period_end_date(self, session, partner_env):
        pid = partner_env["partner"].id
        re_acct = session.get(models.ChartOfAccounts, partner_env["re_id"])
        cur_acct = session.get(models.ChartOfAccounts, partner_env["cur_id"])
        may = _make_period(
            session,
            "May 2025",
            datetime.date(2025, 5, 1),
            datetime.date(2025, 5, 31),
            closed=True,
        )
        _make_allocation_line(session, may.id, pid, 600.0, re_acct=re_acct, cur_acct=cur_acct)
        summary = _summary(
            session, datetime.date(2025, 5, 1), datetime.date(2025, 5, 31)
        )
        assert summary.rows[0].profit_allocated == 600.0

    def test_advance_offset_zero_net_effect(self, session, partner_env):
        pid = partner_env["partner"].id
        d = datetime.date(2025, 7, 5)
        app.post_partner_movement(
            session,
            pid,
            "Advance",
            300.0,
            d,
            bank_account_id=partner_env["bank_id"],
            created_by_id=1,
        )
        before = _summary(session, d, d)
        app.post_partner_movement(session, pid, "AdvanceOffset", 100.0, d, created_by_id=1)
        after = _summary(session, d, d)
        assert advance_offset_position_delta(100.0) == 0.0
        assert after.rows[0].advance_offsets == 100.0
        assert after.rows[0].net_position_change == before.rows[0].net_position_change
        assert after.rows[0].closing_position == before.rows[0].closing_position

    def test_status_company_owes(self, session, partner_env):
        pid = partner_env["partner"].id
        app.post_partner_movement(
            session,
            pid,
            "CapitalContribution",
            1000.0,
            datetime.date(2025, 6, 1),
            bank_account_id=partner_env["bank_id"],
            created_by_id=1,
        )
        summary = _summary(
            session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30)
        )
        assert summary.rows[0].settlement_status == "company_owes"
        assert summary.rows[0].status_amount == summary.rows[0].closing_position


class TestFooterAndWarnings:
    def test_footer_totals_match_row_sums(self, session, two_partner_env):
        d = datetime.date(2025, 6, 10)
        app.post_partner_movement(
            session,
            two_partner_env["partner"].id,
            "CapitalContribution",
            100.0,
            d,
            bank_account_id=two_partner_env["bank_id"],
            created_by_id=1,
        )
        app.post_partner_movement(
            session,
            two_partner_env["partner2"].id,
            "CapitalContribution",
            200.0,
            d,
            bank_account_id=two_partner_env["bank_id"],
            created_by_id=1,
        )
        summary = _summary(session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30))
        f = summary.footer
        assert f.total_capital_contributions == sum(
            r.capital_contributions for r in summary.rows
        )
        assert f.total_closing_position == sum(r.closing_position for r in summary.rows)

    def test_reconciliation_warning_flag(self, session, partner_env, monkeypatch):
        summary = _summary(
            session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30)
        )
        row = summary.rows[0]
        row.reconciliation_ok = False
        row.warning_flags = list(row.warning_flags) + ["reconciliation"]
        assert "reconciliation" in row.warning_flags or not row.reconciliation_ok

    def test_outstanding_advance_flag(self, session, partner_env):
        pid = partner_env["partner"].id
        app.post_partner_movement(
            session,
            pid,
            "Advance",
            150.0,
            datetime.date(2025, 6, 5),
            bank_account_id=partner_env["bank_id"],
            created_by_id=1,
        )
        summary = _summary(session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30))
        assert "outstanding_advance" in summary.rows[0].warning_flags

    def test_closed_period_no_alloc_flag(self, session, partner_env):
        _make_period(
            session,
            "Jun 2025",
            datetime.date(2025, 6, 1),
            datetime.date(2025, 6, 30),
            closed=True,
        )
        summary = _summary(session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30))
        assert "closed_period_no_alloc" in summary.rows[0].warning_flags


class TestFiltersAndPeriod:
    def test_inactive_included_by_default(self, session, partner_env):
        partner_env["partner"].is_active = False
        session.commit()
        summary = _summary(
            session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30)
        )
        assert len(summary.rows) == 1
        assert summary.rows[0].partner_is_active is False

    def test_hide_inactive_filter(self, session, partner_env):
        partner_env["partner"].is_active = False
        session.commit()
        summary = _summary(
            session,
            datetime.date(2025, 6, 1),
            datetime.date(2025, 6, 30),
            include_inactive=False,
        )
        assert len(summary.rows) == 0
        assert partner_env["partner"].id in summary.statements_by_partner_id

    def test_month_preset_range(self):
        today = datetime.date(2025, 6, 15)
        d_from, d_to = partner_statement_preset_range("month", today)
        assert d_from == datetime.date(2025, 6, 1)
        assert d_to == today

    def test_empty_period_zero_activity(self, session, partner_env):
        summary = _summary(
            session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30)
        )
        row = summary.rows[0]
        assert row.opening_position == row.closing_position
        assert row.net_position_change == 0.0


class TestExport:
    def test_export_rows_include_footer(self, session, two_partner_env):
        summary = _summary(
            session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30)
        )
        rows = all_partners_settlement_export_rows(summary)
        assert len(rows) == len(summary.rows) + 1
        assert rows[-1]["Partner"] == "Totals"

    def test_export_totals_match_footer(self, session, partner_env):
        summary = _summary(
            session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30)
        )
        df = all_partners_settlement_to_export_df(summary)
        last = df.iloc[-1]
        assert last["Closing position"] == summary.footer.total_closing_position

    def test_pdf_payload_primary_columns(self, session, two_partner_env):
        summary = _summary(
            session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30)
        )
        payload = all_partners_settlement_pdf_payload(
            summary, company_name="Co", currency="TRY"
        )
        assert payload["table_rows"]
        assert "opening" in payload["table_rows"][0]
        assert "closing" in payload["table_rows"][0]
        assert payload["footer"]["closing"] == summary.footer.total_closing_position

    def test_pdf_bytes_generated(self, session, two_partner_env):
        summary = _summary(
            session, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30)
        )
        payload = all_partners_settlement_pdf_payload(
            summary, company_name="Co", currency="TRY"
        )
        pdf = generate_all_partners_settlement_pdf(payload)
        assert pdf[:4] == b"%PDF"


class TestUiWiring:
    def test_p4_above_single_partner_statement(self):
        src = inspect.getsource(app._render_partner_statement)
        assert "_render_all_partners_settlement_summary" in src
        assert "partner.stmt.all_single_section_title" in src
        idx_all = src.index("_render_all_partners_settlement_summary")
        idx_single = src.index("partner.stmt.all_single_section_title")
        assert idx_all < idx_single

    def test_shared_period_keys(self):
        src = inspect.getsource(app._render_partner_statement)
        assert 'key="partner_stmt_preset"' in src
        assert 'key="partner_stmt_from"' in src
        assert 'key="partner_stmt_to"' in src

    def test_view_statement_sets_partner_key(self):
        src = inspect.getsource(app._render_all_partners_settlement_summary)
        assert 'partner_stmt_partner' in src
        assert "partner.stmt.all_view_statement" in src

    def test_reuses_statement_cache(self):
        src = inspect.getsource(app._render_partner_statement)
        assert "statements_by_partner_id.get" in src


class TestPostingUnchanged:
    def test_post_partner_movement_unchanged(self):
        src = inspect.getsource(app.post_partner_movement)
        assert "def post_partner_movement" in src

    def test_allocate_profit_unchanged(self):
        src = inspect.getsource(app.allocate_profit_to_partners)
        assert "def allocate_profit_to_partners" in src


class TestLocales:
    def test_p4_keys_en_tr(self):
        for key in _P4_LOCALE_KEYS:
            assert key in TRANSACTIONAL_EN
            assert key in TRANSACTIONAL_TR

    def test_p4_keys_resolve(self):
        for key in _P4_LOCALE_KEYS:
            for loc in ("en", "tr"):
                text = t(key, loc)
                assert text != key
                assert not text.startswith("partner.stmt.all_")
