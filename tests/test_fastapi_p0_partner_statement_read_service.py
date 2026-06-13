"""FASTAPI-P0.2-F — Partner statement read service contract tests."""

from __future__ import annotations

import datetime
import sys
from dataclasses import asdict
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

import app as erp_app
from db import Base
import models
from registry.partner_statement import (
    build_partner_statement,
    check_partner_account_breakdown,
    partner_statement_account_breakdown_export_rows,
    partner_statement_closing_breakdown,
    partner_statement_opening_breakdown,
    partner_statement_pdf_payload,
    partner_statement_summary_export_rows,
    partner_statement_to_export_df,
)
from services import read_partner_statement as pstmt

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
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
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        yield s


def _company(db, name: str, slug: str):
    co = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.flush()
    return co


def _make_coa(db, company_id, code, name, acct_type):
    acct = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        balance=0.0,
        is_active=True,
        company_id=company_id,
    )
    db.add(acct)
    db.flush()
    return acct


def _make_partner(db, company_id, name, pct, cap_id, cur_id, adv_id, *, active=True):
    p = models.Partner(
        name=name,
        profit_share_pct=pct,
        capital_account_id=cap_id,
        current_account_id=cur_id,
        advance_account_id=adv_id,
        is_active=active,
        created_at=datetime.datetime.now(),
        company_id=company_id,
    )
    db.add(p)
    db.flush()
    return p


def _make_bank(db, company_id):
    _make_coa(db, company_id, "1100", "Cash", "Asset")
    ba = models.BankAccount(
        name="Cash",
        currency="TRY",
        balance=10000.0,
        is_active=True,
        kind="bank",
        company_id=company_id,
    )
    db.add(ba)
    db.flush()
    return ba


def _make_period(db, company_id, name, start, end, *, closed=False):
    fp = models.FiscalPeriod(
        name=name,
        start_date=start,
        end_date=end,
        is_closed=closed,
        closed_at=datetime.date.today() if closed else None,
        company_id=company_id,
    )
    db.add(fp)
    db.flush()
    return fp


def _make_allocation_line(
    db, company_id, period_id, partner_id, amount, *, re_acct, cur_acct, je_date=None
):
    alloc = models.PartnerProfitAllocation(
        fiscal_period_id=period_id,
        allocated_at=datetime.datetime.now(),
        allocated_by_id=None,
        total_net_income=amount,
        is_void=False,
        created_at=datetime.datetime.now(),
        company_id=company_id,
    )
    db.add(alloc)
    db.flush()
    je_date = je_date or datetime.date.today()
    if amount >= 0:
        lines = [(re_acct.id, amount, 0), (cur_acct.id, 0, amount)]
    else:
        lines = [(re_acct.id, 0, abs(amount)), (cur_acct.id, abs(amount), 0)]
    je = erp_app.create_journal_entry(
        db,
        je_date,
        f"Profit Allocation for period {period_id}",
        "ProfitAllocation",
        alloc.id,
        lines,
    )
    alloc.journal_entry_id = je.id
    db.add(
        models.PartnerProfitAllocationLine(
            allocation_id=alloc.id,
            partner_id=partner_id,
            share_pct=100.0,
            amount=amount,
            company_id=company_id,
        )
    )
    db.commit()
    return alloc


def _set_company(company_id: int):
    sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _counts(db):
    return (
        db.query(models.JournalEntry).count(),
        db.query(models.BankTransaction).count(),
    )


def _legacy_stmt(db, company_id, partner_id, d_from, d_to):
    _set_company(company_id)
    return build_partner_statement(
        db,
        partner_id,
        d_from,
        d_to,
        erp_app.calculate_account_balance_for_period,
        company_id=company_id,
    )


def _stmt_snapshot(stmt):
    """Comparable dict for legacy vs service parity (excludes company_id)."""
    d = asdict(stmt)
    d.pop("company_id", None)
    d["warnings"] = [(w.key, tuple(sorted(w.kwargs.items()))) for w in stmt.warnings]
    d["detail_lines"] = [
        (
            ln.line_date,
            ln.section_key,
            ln.type_key,
            ln.description,
            ln.reference,
            ln.inflow,
            ln.outflow,
            ln.signed_amount,
            ln.net_effect,
            ln.running_position,
        )
        for ln in stmt.detail_lines
    ]
    return d


@pytest.fixture()
def partner_env(db):
    co = _company(db, "Test Co", "test_co")
    _set_company(co.id)
    re_acct = _make_coa(db, co.id, "3100", "Retained Earnings", "Equity")
    cap_acct = _make_coa(db, co.id, "3501", "Bob Capital", "Equity")
    cur_acct = _make_coa(db, co.id, "3601", "Bob Current", "Equity")
    adv_acct = _make_coa(db, co.id, "1501", "Bob Advances", "Asset")
    bank = _make_bank(db, co.id)
    partner = _make_partner(db, co.id, "Bob", 100.0, cap_acct.id, cur_acct.id, adv_acct.id)
    db.commit()
    return {
        "company_id": co.id,
        "partner": partner,
        "bank_id": bank.id,
        "re_id": re_acct.id,
        "cur_id": cur_acct.id,
    }


class TestServiceMatchesLegacy:
    def test_statement_fields_match_legacy(self, db, partner_env):
        pid = partner_env["partner"].id
        cid = partner_env["company_id"]
        bank_id = partner_env["bank_id"]
        d_from = datetime.date(2025, 6, 1)
        d_to = datetime.date(2025, 6, 30)
        erp_app.post_partner_movement(
            db,
            pid,
            "CapitalContribution",
            1000.0,
            datetime.date(2025, 6, 5),
            bank_account_id=bank_id,
            created_by_id=1,
        )
        erp_app.post_partner_movement(
            db,
            pid,
            "Advance",
            150.0,
            datetime.date(2025, 6, 10),
            bank_account_id=bank_id,
            created_by_id=1,
        )
        legacy = _legacy_stmt(db, cid, pid, d_from, d_to)
        service = pstmt.compute_partner_statement(
            db,
            company_id=cid,
            partner_id=pid,
            from_date=d_from,
            to_date=d_to,
        )
        assert service is not None
        assert service.company_id == cid
        assert _stmt_snapshot(legacy) == _stmt_snapshot(service)

    def test_all_partners_summary_matches_legacy(self, db, partner_env):
        cid = partner_env["company_id"]
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        d_from = datetime.date(2025, 6, 1)
        d_to = datetime.date(2025, 6, 30)
        erp_app.post_partner_movement(
            db,
            pid,
            "CapitalContribution",
            500.0,
            datetime.date(2025, 6, 5),
            bank_account_id=bank_id,
            created_by_id=1,
        )
        _set_company(cid)
        legacy = erp_app.compute_all_partners_settlement_summary(
            db, from_date=d_from, to_date=d_to
        )
        service = pstmt.compute_all_partners_settlement_summary(
            db, company_id=cid, from_date=d_from, to_date=d_to
        )
        assert legacy is not None and service is not None
        assert service.company_id == cid
        assert len(legacy.rows) == len(service.rows)
        for lr, sr in zip(legacy.rows, service.rows):
            assert lr.partner_id == sr.partner_id
            assert lr.closing_position == sr.closing_position
        assert legacy.footer.total_closing_position == service.footer.total_closing_position


class TestAccountBreakdownIdentity:
    def test_opening_closing_breakdown_preserved(self, db, partner_env):
        pid = partner_env["partner"].id
        cid = partner_env["company_id"]
        bank_id = partner_env["bank_id"]
        d_from = datetime.date(2025, 6, 1)
        d_to = datetime.date(2025, 6, 30)
        erp_app.post_partner_movement(
            db,
            pid,
            "CapitalContribution",
            800.0,
            datetime.date(2025, 6, 5),
            bank_account_id=bank_id,
            created_by_id=1,
        )
        stmt = pstmt.compute_partner_statement(
            db,
            company_id=cid,
            partner_id=pid,
            from_date=d_from,
            to_date=d_to,
        )
        assert check_partner_account_breakdown(
            stmt.opening_capital,
            stmt.opening_current,
            stmt.opening_advances,
            stmt.opening_position,
        )
        assert check_partner_account_breakdown(
            stmt.closing_capital,
            stmt.closing_current,
            stmt.closing_advances,
            stmt.closing_position,
        )
        opening = partner_statement_opening_breakdown(stmt)
        closing = partner_statement_closing_breakdown(stmt)
        assert opening.net_position == stmt.opening_position
        assert closing.net_position == stmt.closing_position


class TestProfitAllocation:
    def test_profit_allocated_unchanged(self, db, partner_env):
        pid = partner_env["partner"].id
        cid = partner_env["company_id"]
        re_acct = db.get(models.ChartOfAccounts, partner_env["re_id"])
        cur_acct = db.get(models.ChartOfAccounts, partner_env["cur_id"])
        d_from = datetime.date(2025, 7, 1)
        d_to = datetime.date(2025, 7, 31)
        period = _make_period(db, cid, "Jul 2025", d_from, d_to, closed=True)
        _make_allocation_line(
            db, cid, period.id, pid, 200.0, re_acct=re_acct, cur_acct=cur_acct
        )
        legacy = _legacy_stmt(db, cid, pid, d_from, d_to)
        service = pstmt.compute_partner_statement(
            db,
            company_id=cid,
            partner_id=pid,
            from_date=d_from,
            to_date=d_to,
        )
        assert service.profit_allocated == 200.0
        assert service.profit_allocated == legacy.profit_allocated
        detail_types = {ln.type_key for ln in service.detail_lines}
        assert "ProfitAllocated" in detail_types


class TestExportAndPdfPayload:
    def test_export_rows_unchanged(self, db, partner_env):
        pid = partner_env["partner"].id
        cid = partner_env["company_id"]
        bank_id = partner_env["bank_id"]
        d_from = datetime.date(2025, 8, 1)
        d_to = datetime.date(2025, 8, 31)
        erp_app.post_partner_movement(
            db,
            pid,
            "CapitalContribution",
            800.0,
            datetime.date(2025, 8, 1),
            bank_account_id=bank_id,
            created_by_id=1,
        )
        legacy = _legacy_stmt(db, cid, pid, d_from, d_to)
        service = pstmt.compute_partner_statement(
            db,
            company_id=cid,
            partner_id=pid,
            from_date=d_from,
            to_date=d_to,
        )
        assert partner_statement_summary_export_rows(service) == (
            partner_statement_summary_export_rows(legacy)
        )
        assert partner_statement_account_breakdown_export_rows(service) == (
            partner_statement_account_breakdown_export_rows(legacy)
        )
        assert partner_statement_to_export_df(service).equals(
            partner_statement_to_export_df(legacy)
        )

    def test_pdf_payload_unchanged(self, db, partner_env):
        pid = partner_env["partner"].id
        cid = partner_env["company_id"]
        bank_id = partner_env["bank_id"]
        d_from = datetime.date(2025, 8, 1)
        d_to = datetime.date(2025, 8, 31)
        erp_app.post_partner_movement(
            db,
            pid,
            "CapitalContribution",
            300.0,
            datetime.date(2025, 8, 1),
            bank_account_id=bank_id,
            created_by_id=1,
        )
        legacy = _legacy_stmt(db, cid, pid, d_from, d_to)
        service = pstmt.compute_partner_statement(
            db,
            company_id=cid,
            partner_id=pid,
            from_date=d_from,
            to_date=d_to,
        )
        legacy_pdf = partner_statement_pdf_payload(
            legacy,
            company_name="Test Co",
            currency="TRY",
            generated_date=datetime.date(2025, 8, 31),
        )
        service_pdf = partner_statement_pdf_payload(
            service,
            company_name="Test Co",
            currency="TRY",
            generated_date=datetime.date(2025, 8, 31),
        )
        assert service_pdf == legacy_pdf


class TestCompanyIsolation:
    def test_partner_wrong_company_returns_none(self, db, partner_env):
        pid = partner_env["partner"].id
        other = _company(db, "Other Co", "other_co")
        db.commit()
        stmt = pstmt.compute_partner_statement(
            db,
            company_id=other.id,
            partner_id=pid,
            from_date=datetime.date(2025, 1, 1),
            to_date=datetime.date(2025, 12, 31),
        )
        assert stmt is None

    def test_all_partners_scoped_to_company(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta", "beta")
        cap_a = _make_coa(db, co_a.id, "3501", "A Capital", "Equity")
        cur_a = _make_coa(db, co_a.id, "3601", "A Current", "Equity")
        adv_a = _make_coa(db, co_a.id, "1501", "A Advances", "Asset")
        bank_a = _make_bank(db, co_a.id)
        partner_a = _make_partner(
            db, co_a.id, "Alice", 100.0, cap_a.id, cur_a.id, adv_a.id
        )
        cap_b = _make_coa(db, co_b.id, "3502", "B Capital", "Equity")
        cur_b = _make_coa(db, co_b.id, "3602", "B Current", "Equity")
        adv_b = _make_coa(db, co_b.id, "1502", "B Advances", "Asset")
        bank_b = _make_bank(db, co_b.id)
        partner_b = _make_partner(
            db, co_b.id, "Bob", 100.0, cap_b.id, cur_b.id, adv_b.id
        )
        db.commit()
        _set_company(co_a.id)
        erp_app.post_partner_movement(
            db,
            partner_a.id,
            "CapitalContribution",
            1000.0,
            datetime.date(2025, 6, 5),
            bank_account_id=bank_a.id,
            created_by_id=1,
        )
        _set_company(co_b.id)
        erp_app.post_partner_movement(
            db,
            partner_b.id,
            "CapitalContribution",
            5000.0,
            datetime.date(2025, 6, 5),
            bank_account_id=bank_b.id,
            created_by_id=1,
        )
        d_from = datetime.date(2025, 6, 1)
        d_to = datetime.date(2025, 6, 30)
        summary_a = pstmt.compute_all_partners_settlement_summary(
            db, company_id=co_a.id, from_date=d_from, to_date=d_to
        )
        summary_b = pstmt.compute_all_partners_settlement_summary(
            db, company_id=co_b.id, from_date=d_from, to_date=d_to
        )
        assert len(summary_a.rows) == 1
        assert summary_a.rows[0].partner_name == "Alice"
        assert summary_a.rows[0].capital_contributions == 1000.0
        assert len(summary_b.rows) == 1
        assert summary_b.rows[0].partner_name == "Bob"
        assert summary_b.rows[0].capital_contributions == 5000.0


class TestReadOnly:
    def test_compute_creates_no_jes_or_bank_transactions(self, db, partner_env):
        pid = partner_env["partner"].id
        cid = partner_env["company_id"]
        bank_id = partner_env["bank_id"]
        erp_app.post_partner_movement(
            db,
            pid,
            "CapitalContribution",
            100.0,
            datetime.date(2025, 6, 5),
            bank_account_id=bank_id,
            created_by_id=1,
        )
        je_before, bt_before = _counts(db)
        pstmt.compute_partner_statement(
            db,
            company_id=cid,
            partner_id=pid,
            from_date=datetime.date(2025, 6, 1),
            to_date=datetime.date(2025, 6, 30),
        )
        pstmt.compute_all_partners_settlement_summary(
            db,
            company_id=cid,
            from_date=datetime.date(2025, 6, 1),
            to_date=datetime.date(2025, 6, 30),
        )
        je_after, bt_after = _counts(db)
        assert je_after == je_before
        assert bt_after == bt_before
