"""FASTAPI-P1.2 — API contract polish (OpenAPI, errors, no-write invariant)."""

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
from api.bearer_auth import BEARER_MISSING_DETAIL
from api.dependencies import get_db
from api.errors import COMPANY_MISSING_MARKER, MEMBERSHIP_DENIED_MARKER
from api.main import create_app
from api.openapi_tags import OPENAPI_TAGS
from db import Base
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import tokens as token_service
from tests.fastapi_p1_jwt import TEST_JWT_SECRET, api_headers, password_hash_for_tests

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

FROM_DATE = datetime.date(2026, 6, 1)
TO_DATE = datetime.date(2026, 6, 30)

EXPECTED_PATHS = {
    "/health",
    "/auth/login",
    "/auth/me",
    "/auth/companies",
    "/api/v1/reports/profit-loss",
    "/api/v1/reports/balance-sheet",
    "/api/v1/reports/cash-flow",
    "/api/v1/transactions",
    "/api/v1/ledger",
    "/api/v1/chart-of-accounts",
    "/api/v1/receivables",
    "/api/v1/payables",
    "/api/v1/partners",
    "/api/v1/bank-accounts",
    "/api/v1/bank-statement-rows",
    "/api/v1/fiscal-periods",
    "/api/v1/vendors",
    "/api/v1/workers",
    "/api/v1/partners/{partner_id}/statement",
    "/api/v1/banking/readiness",
}

EXPECTED_TAGS = {
    "health",
    "auth",
    "reports",
    "transactions",
    "ledger",
    "chart-of-accounts",
    "receivables",
    "payables",
    "partners",
    "bank-accounts",
    "bank-statement-rows",
    "fiscal-periods",
    "vendors",
    "workers",
    "banking",
    "writes",
}

GET_ROUTES = [
    ("/health", {}),
    (
        "/api/v1/reports/profit-loss",
        {"start_date": FROM_DATE.isoformat(), "end_date": TO_DATE.isoformat()},
    ),
    ("/api/v1/reports/balance-sheet", {"as_of": TO_DATE.isoformat()}),
    (
        "/api/v1/reports/cash-flow",
        {"start_date": FROM_DATE.isoformat(), "end_date": TO_DATE.isoformat()},
    ),
    (
        "/api/v1/transactions",
        {"start_date": FROM_DATE.isoformat(), "end_date": TO_DATE.isoformat()},
    ),
    ("/api/v1/ledger", {"account_id": 1}),
    ("/api/v1/chart-of-accounts", {}),
    ("/api/v1/receivables", {}),
    ("/api/v1/payables", {}),
    ("/api/v1/partners", {}),
    ("/api/v1/bank-accounts", {}),
    ("/api/v1/bank-statement-rows", {}),
    ("/api/v1/fiscal-periods", {}),
    ("/api/v1/vendors", {}),
    ("/api/v1/workers", {}),
    (
        "/api/v1/partners/{partner_id}/statement",
        {"from_date": FROM_DATE.isoformat(), "to_date": TO_DATE.isoformat()},
    ),
    ("/api/v1/banking/readiness", {}),
]


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, TEST_JWT_SECRET)


@pytest.fixture()
def db():
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        yield s


def _resolve_path(path: str, seeded_tenant: dict) -> str:
    if "{partner_id}" in path:
        return path.format(partner_id=seeded_tenant["partner_id"])
    return path


def _resolve_params(params: dict, seeded_tenant: dict) -> dict:
    out = dict(params)
    if "account_id" in out and out["account_id"] == 1:
        out["account_id"] = seeded_tenant["cash_account_id"]
    return out


@pytest.fixture()
def seeded_tenant(db):
    owner = models.User(
        id=erp_app._DEV_USER["id"],
        username=erp_app._DEV_USER["username"],
        display_name=erp_app._DEV_USER["display_name"],
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    cashier = models.User(
        username="cashier_p12",
        display_name="Cashier P12",
        password_hash=password_hash_for_tests(),
        role="cashier",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co = models.Company(
        name="P12 Co",
        slug="p12_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    other = models.Company(
        name="Other Co",
        slug="other_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add_all([owner, cashier, co, other])
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
    cash = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=co.id, account_name="Cash")
        .one()
    )
    cap = models.ChartOfAccounts(
        account_code="P12-CAP",
        account_name="Partner Capital",
        account_type="Equity",
        is_active=True,
        balance=0.0,
        company_id=co.id,
    )
    cur = models.ChartOfAccounts(
        account_code="P12-CUR",
        account_name="Partner Current",
        account_type="Equity",
        is_active=True,
        balance=0.0,
        company_id=co.id,
    )
    adv = models.ChartOfAccounts(
        account_code="P12-ADV",
        account_name="Partner Advances",
        account_type="Asset",
        is_active=True,
        balance=0.0,
        company_id=co.id,
    )
    db.add_all([cap, cur, adv])
    db.flush()
    partner = models.Partner(
        name="Contract Partner",
        profit_share_pct=50.0,
        capital_account_id=cap.id,
        current_account_id=cur.id,
        advance_account_id=adv.id,
        is_active=True,
        created_at=datetime.datetime.now(),
        company_id=co.id,
    )
    db.add(partner)
    db.commit()
    return {
        "owner_id": owner.id,
        "owner": owner,
        "cashier_id": cashier.id,
        "cashier": cashier,
        "company_id": co.id,
        "other_company_id": other.id,
        "cash_account_id": cash.id,
        "partner_id": partner.id,
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


class TestOpenApiSchema:
    def test_openapi_includes_all_read_routes(self, api_client):
        schema = api_client.get("/openapi.json").json()
        paths = set(schema["paths"].keys())
        assert EXPECTED_PATHS <= paths

    def test_openapi_tags_registered(self, api_client):
        schema = api_client.get("/openapi.json").json()
        tag_names = {t["name"] for t in schema["tags"]}
        assert EXPECTED_TAGS <= tag_names
        assert {t["name"] for t in OPENAPI_TAGS} == EXPECTED_TAGS

    def test_each_business_route_has_summary(self, api_client):
        schema = api_client.get("/openapi.json").json()
        for path in EXPECTED_PATHS - {"/health", "/auth/login", "/auth/me", "/auth/companies"}:
            get_op = schema["paths"][path]["get"]
            assert get_op.get("summary"), f"missing summary on {path}"
        post_login = schema["paths"]["/auth/login"]["post"]
        assert post_login.get("summary"), "missing summary on /auth/login"
        for auth_path in ("/auth/me", "/auth/companies"):
            get_auth = schema["paths"][auth_path]["get"]
            assert get_auth.get("summary"), f"missing summary on {auth_path}"

    def test_route_tags_match_contract(self, api_client):
        schema = api_client.get("/openapi.json").json()
        assert schema["paths"]["/health"]["get"]["tags"] == ["health"]
        assert schema["paths"]["/auth/login"]["post"]["tags"] == ["auth"]
        assert schema["paths"]["/auth/me"]["get"]["tags"] == ["auth"]
        assert schema["paths"]["/auth/companies"]["get"]["tags"] == ["auth"]
        assert schema["paths"]["/api/v1/ledger"]["get"]["tags"] == ["ledger"]
        assert schema["paths"]["/api/v1/receivables"]["get"]["tags"] == ["receivables"]
        assert schema["paths"]["/api/v1/payables"]["get"]["tags"] == ["payables"]
        assert schema["paths"]["/api/v1/banking/readiness"]["get"]["tags"] == ["banking"]


class TestErrorContract:
    @pytest.mark.parametrize("path,params", GET_ROUTES[1:])
    def test_missing_bearer_returns_401(self, api_client, seeded_tenant, path, params):
        resp = api_client.get(
            _resolve_path(path, seeded_tenant),
            params=_resolve_params(params, seeded_tenant),
            headers={"X-Company-Id": str(seeded_tenant["company_id"])},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    @pytest.mark.parametrize("path,params", GET_ROUTES[1:])
    def test_missing_company_returns_400(self, api_client, seeded_tenant, path, params):
        resp = api_client.get(
            _resolve_path(path, seeded_tenant),
            params=_resolve_params(params, seeded_tenant),
            headers=api_headers(seeded_tenant["owner"]),
        )
        assert resp.status_code == 400
        assert COMPANY_MISSING_MARKER in resp.json()["detail"]

    def test_non_member_company_returns_403(self, api_client, seeded_tenant):
        resp = api_client.get(
            "/api/v1/receivables",
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["other_company_id"],
            ),
        )
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]

    def test_permission_denied_returns_403(self, api_client, seeded_tenant):
        resp = api_client.get(
            "/api/v1/reports/profit-loss",
            params={
                "start_date": FROM_DATE.isoformat(),
                "end_date": TO_DATE.isoformat(),
            },
            headers=api_headers(
                seeded_tenant["cashier"],
                company_id=seeded_tenant["company_id"],
            ),
        )
        assert resp.status_code == 403
        assert "Permission denied" in resp.json()["detail"]

    @pytest.mark.parametrize(
        "path,params",
        [
            (
                "/api/v1/reports/profit-loss",
                {"start_date": "bad", "end_date": TO_DATE.isoformat()},
            ),
            ("/api/v1/reports/balance-sheet", {"as_of": "not-a-date"}),
            (
                "/api/v1/partners/{partner_id}/statement",
                {"from_date": "x", "to_date": TO_DATE.isoformat()},
            ),
            ("/api/v1/ledger", {"account_id": 1, "start_date": "nope"}),
            ("/api/v1/banking/readiness", {"limit": 0}),
            ("/api/v1/banking/readiness", {"limit": 101}),
        ],
    )
    def test_invalid_query_returns_422(self, api_client, seeded_tenant, path, params):
        resp = api_client.get(
            _resolve_path(path, seeded_tenant),
            params=_resolve_params(params, seeded_tenant),
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_id"],
            ),
        )
        assert resp.status_code == 422
        assert "detail" in resp.json()


class TestResponsePrimitives:
    def test_receivables_json_is_primitive_dict(self, api_client, seeded_tenant):
        resp = api_client.get(
            "/api/v1/receivables",
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_id"],
            ),
        )
        body = resp.json()
        assert isinstance(body, dict)
        assert isinstance(body.get("rows"), list)
        assert isinstance(body.get("filters"), dict)
        assert isinstance(body.get("aging"), dict)

    def test_banking_readiness_includes_meta_limit(self, api_client, seeded_tenant):
        resp = api_client.get(
            "/api/v1/banking/readiness",
            params={"limit": 5},
            headers=api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_id"],
            ),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"] == {"limit": 5, "count": 0}


class TestNoWriteInvariant:
    @pytest.mark.parametrize("path,params", GET_ROUTES)
    def test_get_never_commits_session(
        self, api_client, db, seeded_tenant, path, params
    ):
        if path == "/health":
            auth_headers = {}
        else:
            auth_headers = api_headers(
                seeded_tenant["owner"],
                company_id=seeded_tenant["company_id"],
            )
        resolved_path = _resolve_path(path, seeded_tenant)
        resolved_params = _resolve_params(params, seeded_tenant)
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                resolved_path, params=resolved_params, headers=auth_headers
            )
        assert resp.status_code == 200
        assert mock_commit.call_count == 0
