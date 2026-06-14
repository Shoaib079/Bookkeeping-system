"""FASTAPI-P1.0 — read-only API foundation contract tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

import app as erp_app
import models
from api.dependencies import get_db
from api.main import create_app
from api.serialization import profit_loss_to_dict
from db import Base
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import read_reports as rr

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

POST_DATE = datetime.date(2026, 6, 1)
START = datetime.date(2026, 6, 1)
END = datetime.date(2026, 6, 30)


def _headers(
    user_id: int,
    *,
    company_id: int | None = None,
    role: str | None = None,
) -> dict[str, str]:
    out = {"X-User-Id": str(user_id)}
    if company_id is not None:
        out["X-Company-Id"] = str(company_id)
    if role is not None:
        out["X-Role"] = role
    return out


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


@pytest.fixture()
def seeded_tenant(db):
    """Owner user + company A with seeded COA and one income JE."""
    owner = models.User(
        id=erp_app._DEV_USER["id"],
        username=erp_app._DEV_USER["username"],
        display_name=erp_app._DEV_USER["display_name"],
        password_hash="x",
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    cashier = models.User(
        username="cashier_p1",
        display_name="Cashier P1",
        password_hash="x",
        role="cashier",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co = models.Company(
        name="P1 API Co",
        slug="p1_api_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add_all([owner, cashier, co])
    db.flush()
    db.add(
        models.CompanyUser(
            company_id=co.id,
            user_id=owner.id,
            role="owner",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
    )
    db.add(
        models.CompanyUser(
            company_id=co.id,
            user_id=cashier.id,
            role="cashier",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
    )
    seed_chart_of_accounts_for_company(db, co.id)
    sales = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=co.id, account_name="Sales Revenue")
        .one()
    )
    cash = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=co.id, account_name="Cash")
        .one()
    )
    je = models.JournalEntry(
        entry_date=POST_DATE,
        description="Cash sale",
        reference_type="CashSale",
        reference_id=1,
        company_id=co.id,
    )
    db.add(je)
    db.flush()
    db.add_all(
        [
            models.JournalEntryLine(
                journal_entry_id=je.id,
                account_id=cash.id,
                debit=250.0,
                credit=0.0,
                company_id=co.id,
            ),
            models.JournalEntryLine(
                journal_entry_id=je.id,
                account_id=sales.id,
                debit=0.0,
                credit=250.0,
                company_id=co.id,
            ),
        ]
    )
    db.commit()
    return {
        "company_id": co.id,
        "owner_id": owner.id,
        "cashier_id": cashier.id,
    }


@pytest.fixture()
def two_company_tenant(db):
    """Owner member of co A (with income JE) and co B (empty)."""
    owner = models.User(
        id=erp_app._DEV_USER["id"],
        username=erp_app._DEV_USER["username"],
        display_name=erp_app._DEV_USER["display_name"],
        password_hash="x",
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(owner)
    db.flush()

    co_a = models.Company(
        name="P1 API Co A",
        slug="p1_api_co_a",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co_b = models.Company(
        name="P1 API Co B",
        slug="p1_api_co_b",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add_all([co_a, co_b])
    db.flush()
    db.add_all(
        [
            models.CompanyUser(
                company_id=co_a.id,
                user_id=owner.id,
                role="owner",
                is_active=True,
                created_at=datetime.datetime.now(),
            ),
            models.CompanyUser(
                company_id=co_b.id,
                user_id=owner.id,
                role="owner",
                is_active=True,
                created_at=datetime.datetime.now(),
            ),
        ]
    )
    seed_chart_of_accounts_for_company(db, co_a.id)
    seed_chart_of_accounts_for_company(db, co_b.id)
    sales = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=co_a.id, account_name="Sales Revenue")
        .one()
    )
    cash = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=co_a.id, account_name="Cash")
        .one()
    )
    je = models.JournalEntry(
        entry_date=POST_DATE,
        description="Cash sale",
        reference_type="CashSale",
        reference_id=1,
        company_id=co_a.id,
    )
    db.add(je)
    db.flush()
    db.add_all(
        [
            models.JournalEntryLine(
                journal_entry_id=je.id,
                account_id=cash.id,
                debit=250.0,
                credit=0.0,
                company_id=co_a.id,
            ),
            models.JournalEntryLine(
                journal_entry_id=je.id,
                account_id=sales.id,
                debit=0.0,
                credit=250.0,
                company_id=co_a.id,
            ),
        ]
    )
    db.commit()
    return {
        "company_a_id": co_a.id,
        "company_b_id": co_b.id,
        "owner_id": owner.id,
    }


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


class TestApiBoot:
    def test_create_app_boots(self):
        app = create_app()
        assert app.title == "Streamlit Accounting ERP API"

    def test_health_returns_ok(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestReportContextAndPermissions:
    def test_profit_loss_requires_user_header(self, api_client, seeded_tenant):
        resp = api_client.get(
            "/api/v1/reports/profit-loss",
            params={"start_date": START.isoformat(), "end_date": END.isoformat()},
        )
        assert resp.status_code == 401

    def test_profit_loss_requires_company_header(self, api_client, seeded_tenant):
        resp = api_client.get(
            "/api/v1/reports/profit-loss",
            params={"start_date": START.isoformat(), "end_date": END.isoformat()},
            headers=_headers(seeded_tenant["owner_id"]),
        )
        assert resp.status_code == 400
        assert "active_company_id" in resp.json()["detail"]

    def test_profit_loss_denies_non_member(self, api_client, db, seeded_tenant):
        other = models.Company(
            name="Other Co",
            slug="other_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        db.add(other)
        db.commit()
        resp = api_client.get(
            "/api/v1/reports/profit-loss",
            params={"start_date": START.isoformat(), "end_date": END.isoformat()},
            headers=_headers(
                seeded_tenant["owner_id"],
                company_id=other.id,
                role="owner",
            ),
        )
        assert resp.status_code == 403
        assert "membership" in resp.json()["detail"].lower()

    def test_profit_loss_denies_without_report_permission(
        self, api_client, seeded_tenant
    ):
        resp = api_client.get(
            "/api/v1/reports/profit-loss",
            params={"start_date": START.isoformat(), "end_date": END.isoformat()},
            headers=_headers(
                seeded_tenant["cashier_id"],
                company_id=seeded_tenant["company_id"],
                role="cashier",
            ),
        )
        assert resp.status_code == 403
        assert "view_management_reports" in resp.json()["detail"]


class TestReportDtoResponse:
    def test_profit_loss_returns_expected_dto_json(self, api_client, db, seeded_tenant):
        expected = profit_loss_to_dict(
            rr.compute_profit_loss(
                db,
                company_id=seeded_tenant["company_id"],
                start_date=START,
                end_date=END,
            )
        )
        resp = api_client.get(
            "/api/v1/reports/profit-loss",
            params={"start_date": START.isoformat(), "end_date": END.isoformat()},
            headers=_headers(
                seeded_tenant["owner_id"],
                company_id=seeded_tenant["company_id"],
                role="owner",
            ),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body == expected
        assert body["net"] == pytest.approx(250.0)
        assert len(body["income_lines"]) == 1
        assert body["income_lines"][0]["account_name"] == "Sales Revenue"

    def test_get_profit_loss_performs_no_commit(self, api_client, db, seeded_tenant):
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                "/api/v1/reports/profit-loss",
                params={"start_date": START.isoformat(), "end_date": END.isoformat()},
                headers=_headers(
                    seeded_tenant["owner_id"],
                    company_id=seeded_tenant["company_id"],
                    role="owner",
                ),
            )
        assert resp.status_code == 200
        assert mock_commit.call_count == 0


class TestCompanyIsolation:
    def test_profit_loss_scoped_to_requested_company(
        self, api_client, two_company_tenant
    ):
        resp_a = api_client.get(
            "/api/v1/reports/profit-loss",
            params={"start_date": START.isoformat(), "end_date": END.isoformat()},
            headers=_headers(
                two_company_tenant["owner_id"],
                company_id=two_company_tenant["company_a_id"],
                role="owner",
            ),
        )
        resp_b = api_client.get(
            "/api/v1/reports/profit-loss",
            params={"start_date": START.isoformat(), "end_date": END.isoformat()},
            headers=_headers(
                two_company_tenant["owner_id"],
                company_id=two_company_tenant["company_b_id"],
                role="owner",
            ),
        )
        assert resp_a.status_code == 200
        assert resp_b.status_code == 200
        assert resp_a.json()["net"] == pytest.approx(250.0)
        assert resp_b.json()["net"] == pytest.approx(0.0)
        assert resp_a.json()["income_lines"]
        assert resp_b.json()["income_lines"] == []
