"""FASTAPI-P2.9 — period close / profit allocation / allocation void write endpoints."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from api.bearer_auth import BEARER_MISSING_DETAIL
from api.dependencies import DEV_HEADERS_ENV, get_db
from api.errors import MEMBERSHIP_DENIED_MARKER
from api.main import create_app
from db import Base
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import audit as audit_svc
from services import commit_modes, posting
from services import tokens as token_service
from services.commit_modes import (
    CommitMode,
    PERIOD_CLOSE_FAMILY,
    PROFIT_ALLOCATION_FAMILY,
    VOID_CASCADE_FAMILY,
)
from tests.fastapi_p1_jwt import TEST_JWT_SECRET, api_headers, password_hash_for_tests

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

PAST_YEAR = datetime.date.today().year - 1
P_START = datetime.date(PAST_YEAR, 1, 1)
P_END = datetime.date(PAST_YEAR, 1, 31)
MID = datetime.date(PAST_YEAR, 1, 15)
Y_START = datetime.date(PAST_YEAR, 1, 1)
Y_END = datetime.date(PAST_YEAR, 12, 31)
CURRENCY = "TRY"
WRITE_CLOSING_ENV = "ERP_API_WRITE_CLOSING"

PERIOD_NOT_FOUND_OR_CLOSED_MSG = "Period not found or already closed."
FISCAL_PERIOD_NOT_FOUND_MSG = "Fiscal period not found."
ALLOCATION_NOT_FOUND_OR_VOIDED_MSG = "Allocation not found or already voided."
VOID_REASON_REQUIRED_MSG = "Void reason is required."
NO_ACTIVITY_MSG = "No income or expense activity in this period. Nothing to close."


# ── Fixtures (mirror test_fastapi_p2_void_write.py) ──────────────────────────


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, TEST_JWT_SECRET)
    monkeypatch.delenv(DEV_HEADERS_ENV, raising=False)


@pytest.fixture(autouse=True)
def _write_closing_enabled(monkeypatch):
    monkeypatch.setenv(WRITE_CLOSING_ENV, "1")


@pytest.fixture(autouse=True)
def _reset_commit_modes():
    commit_modes.reset_commit_modes_for_tests()
    yield
    commit_modes.reset_commit_modes_for_tests()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


@pytest.fixture()
def api_client(db):
    app = create_app()

    def _override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def tenant(db):
    owner = models.User(
        username="owner_p29",
        display_name="Owner P29",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    outsider = models.User(
        username="outsider_p29",
        display_name="Outsider P29",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_a = models.Company(
        name="Co A P29", slug="co_a_p29", is_active=True, created_at=datetime.datetime.now()
    )
    co_b = models.Company(
        name="Co B P29", slug="co_b_p29", is_active=True, created_at=datetime.datetime.now()
    )
    db.add_all([owner, outsider, co_a, co_b])
    db.flush()
    db.add_all(
        [
            models.CompanyUser(
                company_id=co_a.id, user_id=owner.id, role="owner",
                is_active=True, created_at=datetime.datetime.now(),
            ),
            models.CompanyUser(
                company_id=co_b.id, user_id=outsider.id, role="owner",
                is_active=True, created_at=datetime.datetime.now(),
            ),
        ]
    )
    seed_chart_of_accounts_for_company(db, co_a.id)
    seed_chart_of_accounts_for_company(db, co_b.id)
    db.commit()
    return {
        "owner": owner,
        "outsider": outsider,
        "company_id": co_a.id,
        "other_company_id": co_b.id,
    }


# ── Seeding helpers ──────────────────────────────────────────────────────────


def _acct_id(db, cid, name):
    acct = posting.get_account_by_name(db, name, company_id=cid)
    assert acct is not None, f"Seeded account {name!r} missing"
    return acct.id


def _open_period(db, cid, *, revenue=1000.0, expense=600.0, name="Jan"):
    period = models.FiscalPeriod(
        name=f"{name} {PAST_YEAR}",
        start_date=P_START,
        end_date=P_END,
        is_closed=False,
        company_id=cid,
    )
    db.add(period)
    db.flush()
    cash_id = _acct_id(db, cid, "Cash")
    inc_id = _acct_id(db, cid, "Sales Revenue")
    exp_id = _acct_id(db, cid, "Rent Expense")
    if revenue:
        posting.create_journal_entry(
            db, MID, "Sale pin", "Sale", None,
            [(cash_id, revenue, 0.0), (inc_id, 0.0, revenue)], company_id=cid,
        )
    if expense:
        posting.create_journal_entry(
            db, MID, "Expense pin", "Expense", None,
            [(exp_id, expense, 0.0), (cash_id, 0.0, expense)], company_id=cid,
        )
    db.commit()
    return period


def _close(db, cid, period_id):
    posting.close_fiscal_period(db, period_id, company_id=cid)


def _seed_partners(db, cid, pcts):
    partners = []
    for i, pct in enumerate(pcts, start=1):
        cap = models.ChartOfAccounts(
            account_code=f"350{i}", account_name=f"P{i} Capital {cid}",
            account_type="Equity", balance=0.0, is_active=True, company_id=cid,
        )
        cur = models.ChartOfAccounts(
            account_code=f"360{i}", account_name=f"P{i} Current {cid}",
            account_type="Equity", balance=0.0, is_active=True, company_id=cid,
        )
        adv = models.ChartOfAccounts(
            account_code=f"150{i}", account_name=f"P{i} Advances {cid}",
            account_type="Asset", balance=0.0, is_active=True, company_id=cid,
        )
        db.add_all([cap, cur, adv])
        db.flush()
        p = models.Partner(
            name=f"Partner {i}", profit_share_pct=pct,
            capital_account_id=cap.id, current_account_id=cur.id,
            advance_account_id=adv.id, is_active=True, company_id=cid,
            created_at=datetime.datetime.now(),
        )
        db.add(p)
        db.flush()
        partners.append(p)
    db.commit()
    return partners


def _closed_period_with_partners(db, cid, *, revenue=1000.0, expense=600.0, pcts=(50.0, 50.0)):
    _seed_partners(db, cid, pcts)
    period = _open_period(db, cid, revenue=revenue, expense=expense)
    _close(db, cid, period.id)
    return period


# ── Request helpers ──────────────────────────────────────────────────────────


def _post_close(client, user, cid, period_id):
    return client.post(
        f"/api/v1/periods/{period_id}/close", headers=api_headers(user, company_id=cid)
    )


def _post_allocate(client, user, cid, period_id, **overrides):
    body = {"period_id": period_id}
    body.update(overrides)
    return client.post(
        "/api/v1/profit-allocations", json=body, headers=api_headers(user, company_id=cid)
    )


def _post_void(client, user, cid, allocation_id, reason="API void test"):
    return client.post(
        f"/api/v1/profit-allocations/{allocation_id}/void",
        json={"reason": reason},
        headers=api_headers(user, company_id=cid),
    )


def _je_balanced(db) -> bool:
    lines = db.query(models.JournalEntryLine).all()
    deb = round(sum(l.debit or 0 for l in lines), 2)
    cred = round(sum(l.credit or 0 for l in lines), 2)
    return abs(deb - cred) < 0.02


# ── Feature flag ─────────────────────────────────────────────────────────────


class TestFeatureFlag:
    def test_close_disabled_returns_404(self, api_client, tenant, db, monkeypatch):
        monkeypatch.delenv(WRITE_CLOSING_ENV, raising=False)
        period = _open_period(db, tenant["company_id"])
        resp = _post_close(api_client, tenant["owner"], tenant["company_id"], period.id)
        assert resp.status_code == 404

    def test_allocate_disabled_returns_404(self, api_client, tenant, db, monkeypatch):
        monkeypatch.delenv(WRITE_CLOSING_ENV, raising=False)
        resp = _post_allocate(api_client, tenant["owner"], tenant["company_id"], 1)
        assert resp.status_code == 404

    def test_void_disabled_returns_404(self, api_client, tenant, db, monkeypatch):
        monkeypatch.delenv(WRITE_CLOSING_ENV, raising=False)
        resp = _post_void(api_client, tenant["owner"], tenant["company_id"], 1)
        assert resp.status_code == 404


# ── Auth ─────────────────────────────────────────────────────────────────────


class TestAuth:
    def test_missing_bearer_rejected(self, api_client, tenant, db):
        period = _open_period(db, tenant["company_id"])
        resp = api_client.post(
            f"/api/v1/periods/{period.id}/close",
            headers={"X-Company-Id": str(tenant["company_id"])},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_non_member_rejected(self, api_client, tenant, db):
        period = _open_period(db, tenant["company_id"])
        resp = _post_close(api_client, tenant["outsider"], tenant["company_id"], period.id)
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]


# ── Period close ─────────────────────────────────────────────────────────────


class TestPeriodClose:
    def test_close_matches_current_behavior(self, api_client, tenant, db):
        cid = tenant["company_id"]
        period = _open_period(db, cid, revenue=1000.0, expense=600.0)
        resp = _post_close(api_client, tenant["owner"], cid, period.id)
        assert resp.status_code == 200
        body = resp.json()
        assert body["period_id"] == period.id
        assert body["status"] == "ok"
        assert body["journal_entry_id"] is not None

        db.refresh(period)
        assert period.is_closed is True
        assert period.closing_je_id == body["journal_entry_id"]

        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "PeriodClose"
        re_id = _acct_id(db, cid, "Retained Earnings")
        re_lines = [l for l in je.lines if l.account_id == re_id]
        assert len(re_lines) == 1
        assert round((re_lines[0].credit or 0) - (re_lines[0].debit or 0), 2) == 400.0
        assert _je_balanced(db)

    def test_close_writes_audit(self, api_client, tenant, db):
        cid = tenant["company_id"]
        period = _open_period(db, cid)
        _post_close(api_client, tenant["owner"], cid, period.id)
        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action=audit_svc.ACTION_PERIOD_CLOSE,
                entity_type=audit_svc.ENTITY_FISCAL_PERIOD,
                entity_id=period.id,
            )
            .one()
        )
        assert audit.description.startswith(f"Closed period '{period.name}'")
        assert "Net income: $400.00" in audit.description

    def test_reclose_rejected(self, api_client, tenant, db):
        cid = tenant["company_id"]
        period = _open_period(db, cid)
        _close(db, cid, period.id)
        resp = _post_close(api_client, tenant["owner"], cid, period.id)
        assert resp.status_code == 400
        assert resp.json()["detail"] == PERIOD_NOT_FOUND_OR_CLOSED_MSG

    def test_close_no_activity_rejected(self, api_client, tenant, db):
        cid = tenant["company_id"]
        period = models.FiscalPeriod(
            name=f"Empty {PAST_YEAR}", start_date=P_START, end_date=P_END,
            is_closed=False, company_id=cid,
        )
        db.add(period)
        db.commit()
        resp = _post_close(api_client, tenant["owner"], cid, period.id)
        assert resp.status_code == 400
        assert resp.json()["detail"] == NO_ACTIVITY_MSG


# ── Profit allocation ────────────────────────────────────────────────────────


class TestProfitAllocation:
    def test_allocation_matches_current_behavior(self, api_client, tenant, db):
        cid = tenant["company_id"]
        period = _closed_period_with_partners(db, cid, revenue=1000.0, expense=600.0)
        resp = _post_allocate(api_client, tenant["owner"], cid, period.id)
        assert resp.status_code == 200
        body = resp.json()
        assert body["allocation_id"] is not None
        assert body["journal_entry_id"] is not None
        assert body["status"] == "ok"

        alloc = db.get(models.PartnerProfitAllocation, body["allocation_id"])
        assert round(alloc.total_net_income, 2) == 400.0
        je = db.get(models.JournalEntry, body["journal_entry_id"])
        assert je.reference_type == "ProfitAllocation"
        re_id = _acct_id(db, cid, "Retained Earnings")
        re_lines = [l for l in je.lines if l.account_id == re_id]
        assert round(re_lines[0].debit or 0, 2) == 400.0  # profit → Dr RE
        cur_credits = round(
            sum(l.credit or 0 for l in je.lines if l.account_id != re_id), 2
        )
        assert cur_credits == 400.0
        assert _je_balanced(db)

    def test_retained_earnings_and_partner_current_posting(self, api_client, tenant, db):
        cid = tenant["company_id"]
        period = _closed_period_with_partners(db, cid, revenue=1000.0, expense=600.0)
        resp = _post_allocate(api_client, tenant["owner"], cid, period.id)
        alloc_id = resp.json()["allocation_id"]
        lines = (
            db.query(models.PartnerProfitAllocationLine)
            .filter_by(allocation_id=alloc_id)
            .all()
        )
        assert len(lines) == 2
        assert round(sum(l.amount for l in lines), 2) == 400.0
        assert all(round(l.amount, 2) == 200.0 for l in lines)  # 50/50

    def test_loss_allocation_behavior(self, api_client, tenant, db):
        cid = tenant["company_id"]
        period = _closed_period_with_partners(db, cid, revenue=600.0, expense=1000.0)
        resp = _post_allocate(api_client, tenant["owner"], cid, period.id)
        assert resp.status_code == 200
        body = resp.json()
        alloc = db.get(models.PartnerProfitAllocation, body["allocation_id"])
        assert round(alloc.total_net_income, 2) == -400.0
        je = db.get(models.JournalEntry, body["journal_entry_id"])
        re_id = _acct_id(db, cid, "Retained Earnings")
        re_lines = [l for l in je.lines if l.account_id == re_id]
        assert round(re_lines[0].credit or 0, 2) == 400.0  # loss → Cr RE
        cur_debits = round(
            sum(l.debit or 0 for l in je.lines if l.account_id != re_id), 2
        )
        assert cur_debits == 400.0
        lines = (
            db.query(models.PartnerProfitAllocationLine)
            .filter_by(allocation_id=body["allocation_id"])
            .all()
        )
        assert all(round(l.amount, 2) == -200.0 for l in lines)  # negative on loss
        assert _je_balanced(db)

    def test_rounding_remainder_absorbed(self, api_client, tenant, db):
        cid = tenant["company_id"]
        # net income 100.01 across 50/50 → last partner absorbs the odd cent.
        period = _closed_period_with_partners(
            db, cid, revenue=100.01, expense=0.0, pcts=(50.0, 50.0)
        )
        resp = _post_allocate(api_client, tenant["owner"], cid, period.id)
        assert resp.status_code == 200
        alloc_id = resp.json()["allocation_id"]
        lines = (
            db.query(models.PartnerProfitAllocationLine)
            .filter_by(allocation_id=alloc_id)
            .order_by(models.PartnerProfitAllocationLine.id)
            .all()
        )
        amounts = sorted(round(l.amount, 2) for l in lines)
        assert round(sum(amounts), 2) == 100.01  # remainder absorbed exactly
        assert amounts == [50.0, 50.01]
        assert _je_balanced(db)

    def test_allocate_writes_audit(self, api_client, tenant, db):
        cid = tenant["company_id"]
        period = _closed_period_with_partners(db, cid)
        resp = _post_allocate(api_client, tenant["owner"], cid, period.id)
        alloc_id = resp.json()["allocation_id"]
        alloc = db.get(models.PartnerProfitAllocation, alloc_id)
        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action=audit_svc.ACTION_PROFIT_ALLOCATION,
                entity_type=audit_svc.ENTITY_PARTNER_PROFIT_ALLOCATION,
                entity_id=alloc_id,
            )
            .one()
        )
        assert audit.description == (
            f"Allocated {period.name}: net {alloc.total_net_income:,.2f} → 2 partners"
        )

    def test_allocate_period_not_closed_rejected(self, api_client, tenant, db):
        cid = tenant["company_id"]
        _seed_partners(db, cid, (50.0, 50.0))
        period = _open_period(db, cid)  # not closed
        resp = _post_allocate(api_client, tenant["owner"], cid, period.id)
        assert resp.status_code == 400
        assert "must be closed" in resp.json()["detail"].lower()

    def test_allocate_duplicate_rejected(self, api_client, tenant, db):
        cid = tenant["company_id"]
        period = _closed_period_with_partners(db, cid)
        first = _post_allocate(api_client, tenant["owner"], cid, period.id)
        assert first.status_code == 200
        first_id = first.json()["allocation_id"]
        # Root cause lock: the kernel duplicate guard filters on company_id, but the
        # API session has no before_flush stamp — the allocation must carry company_id.
        assert db.get(models.PartnerProfitAllocation, first_id).company_id == cid
        second = _post_allocate(api_client, tenant["owner"], cid, period.id)
        assert second.status_code == 400
        assert second.json()["detail"] == (
            f"Period '{period.name}' already has an active allocation (#{first_id})."
        )

    def test_company_id_in_body_rejected(self, api_client, tenant, db):
        cid = tenant["company_id"]
        period = _closed_period_with_partners(db, cid)
        resp = _post_allocate(
            api_client, tenant["owner"], cid, period.id,
            company_id=tenant["other_company_id"],
        )
        assert resp.status_code == 422


# ── Allocation void ──────────────────────────────────────────────────────────


class TestAllocationVoid:
    def _allocate(self, api_client, tenant, db, cid):
        period = _closed_period_with_partners(db, cid)
        resp = _post_allocate(api_client, tenant["owner"], cid, period.id)
        return period, resp.json()["allocation_id"], resp.json()["journal_entry_id"]

    def test_void_creates_reversal_je(self, api_client, tenant, db):
        cid = tenant["company_id"]
        _period, alloc_id, orig_je_id = self._allocate(api_client, tenant, db, cid)
        resp = _post_void(api_client, tenant["owner"], cid, alloc_id)
        assert resp.status_code == 200
        body = resp.json()
        assert body["allocation_id"] == alloc_id
        assert body["journal_entry_id"] is not None
        assert body["status"] == "ok"

        alloc = db.get(models.PartnerProfitAllocation, alloc_id)
        assert alloc.is_void is True
        reversal = db.get(models.JournalEntry, body["journal_entry_id"])
        assert reversal.reference_type == "Reversal"
        assert reversal.reference_id == orig_je_id
        assert _je_balanced(db)

    def test_void_writes_audit(self, api_client, tenant, db):
        cid = tenant["company_id"]
        period, alloc_id, _ = self._allocate(api_client, tenant, db, cid)
        _post_void(api_client, tenant["owner"], cid, alloc_id, reason="bad numbers")
        audit = (
            db.query(models.AuditLog)
            .filter_by(
                action=audit_svc.ACTION_VOID,
                entity_type=audit_svc.ENTITY_PARTNER_PROFIT_ALLOCATION,
                entity_id=alloc_id,
            )
            .one()
        )
        assert audit.description == (
            f"Voided profit allocation for period #{period.id} — bad numbers"
        )

    def test_void_already_voided_rejected(self, api_client, tenant, db):
        cid = tenant["company_id"]
        _period, alloc_id, _ = self._allocate(api_client, tenant, db, cid)
        first = _post_void(api_client, tenant["owner"], cid, alloc_id)
        assert first.status_code == 200
        second = _post_void(api_client, tenant["owner"], cid, alloc_id)
        assert second.status_code == 400
        assert second.json()["detail"] == ALLOCATION_NOT_FOUND_OR_VOIDED_MSG

    def test_void_empty_reason_rejected(self, api_client, tenant, db):
        cid = tenant["company_id"]
        _period, alloc_id, _ = self._allocate(api_client, tenant, db, cid)
        resp = _post_void(api_client, tenant["owner"], cid, alloc_id, reason="   ")
        assert resp.status_code == 400
        assert resp.json()["detail"] == VOID_REASON_REQUIRED_MSG

    def test_void_blocked_by_year_end_close(self, api_client, tenant, db):
        cid = tenant["company_id"]
        period, alloc_id, _ = self._allocate(api_client, tenant, db, cid)
        db.add(
            models.YearEndClose(
                fiscal_year=str(PAST_YEAR), start_date=Y_START, end_date=Y_END,
                status="closed", closed_at=datetime.datetime.now(),
                period_count=1, allocation_count=1, net_income_snapshot=0.0,
                re_balance_at_close=0.0, is_void=False,
                created_at=datetime.datetime.now(), company_id=cid,
            )
        )
        db.commit()
        resp = _post_void(api_client, tenant["owner"], cid, alloc_id)
        assert resp.status_code == 400
        assert "closed" in resp.json()["detail"].lower()
        db.refresh(db.get(models.PartnerProfitAllocation, alloc_id))
        assert db.get(models.PartnerProfitAllocation, alloc_id).is_void is False


# ── Company isolation ────────────────────────────────────────────────────────


class TestCompanyIsolation:
    def test_cannot_close_other_company_period(self, api_client, tenant, db):
        other = tenant["other_company_id"]
        period = _open_period(db, other)
        resp = _post_close(api_client, tenant["owner"], tenant["company_id"], period.id)
        assert resp.status_code == 400
        assert resp.json()["detail"] == PERIOD_NOT_FOUND_OR_CLOSED_MSG
        db.refresh(period)
        assert period.is_closed is False

    def test_cannot_allocate_other_company_period(self, api_client, tenant, db):
        other = tenant["other_company_id"]
        period = _closed_period_with_partners(db, other)
        resp = _post_allocate(api_client, tenant["owner"], tenant["company_id"], period.id)
        assert resp.status_code == 400
        assert resp.json()["detail"] == FISCAL_PERIOD_NOT_FOUND_MSG

    def test_cannot_void_other_company_allocation(self, api_client, tenant, db):
        other = tenant["other_company_id"]
        period = _closed_period_with_partners(db, other)
        # Allocate in the other company directly via kernel (owner there is outsider).
        alloc_id, err = posting.allocate_profit_to_partners(
            db, period.id, tenant["outsider"].id, company_id=other
        )
        db.commit()
        assert err == ""
        resp = _post_void(api_client, tenant["owner"], tenant["company_id"], alloc_id)
        assert resp.status_code == 400
        assert resp.json()["detail"] == ALLOCATION_NOT_FOUND_OR_VOIDED_MSG
        assert db.get(models.PartnerProfitAllocation, alloc_id).is_void is False


# ── Boundary commit ownership ────────────────────────────────────────────────


class TestBoundaryCommit:
    def test_close_boundary_single_commit(self, api_client, tenant, db):
        commit_modes.set_commit_mode_for_tests(PERIOD_CLOSE_FAMILY, CommitMode.BOUNDARY)
        cid = tenant["company_id"]
        period = _open_period(db, cid)
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = _post_close(api_client, tenant["owner"], cid, period.id)
            assert resp.status_code == 200
            assert mock_commit.call_count == 1

    def test_allocate_boundary_single_commit(self, api_client, tenant, db):
        commit_modes.set_commit_mode_for_tests(PROFIT_ALLOCATION_FAMILY, CommitMode.BOUNDARY)
        cid = tenant["company_id"]
        period = _closed_period_with_partners(db, cid)
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = _post_allocate(api_client, tenant["owner"], cid, period.id)
            assert resp.status_code == 200
            assert mock_commit.call_count == 1

    def test_void_boundary_single_commit(self, api_client, tenant, db):
        commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
        cid = tenant["company_id"]
        period = _closed_period_with_partners(db, cid)
        alloc_id = _post_allocate(api_client, tenant["owner"], cid, period.id).json()[
            "allocation_id"
        ]
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = _post_void(api_client, tenant["owner"], cid, alloc_id)
            assert resp.status_code == 200
            assert mock_commit.call_count == 1


# ── No GET commits ───────────────────────────────────────────────────────────


class TestNoGetCommits:
    def test_read_get_performs_no_commit(self, api_client, tenant, db):
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                "/api/v1/receivables",
                headers=api_headers(tenant["owner"], company_id=tenant["company_id"]),
            )
            assert resp.status_code == 200
            mock_commit.assert_not_called()
