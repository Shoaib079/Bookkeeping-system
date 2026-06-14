"""FASTAPI-P1.3e — JWT runtime auth for protected read endpoints."""

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
from api.bearer_auth import BEARER_INVALID_DETAIL, BEARER_MISSING_DETAIL
from api.dependencies import DEV_HEADERS_ENV, get_db
from api.errors import COMPANY_MISSING_MARKER, MEMBERSHIP_DENIED_MARKER
from api.main import create_app
from db import Base
from services import auth as auth_service
from services import tokens as token_service
from tests.fastapi_p1_jwt import TEST_JWT_SECRET, api_headers, bearer_token, password_hash_for_tests

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

FROM_DATE = datetime.date(2026, 6, 1)
TO_DATE = datetime.date(2026, 6, 30)


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, TEST_JWT_SECRET)
    monkeypatch.delenv(DEV_HEADERS_ENV, raising=False)


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
        username="owner_p13e",
        display_name="Owner P13E",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    cashier = models.User(
        username="cashier_p13e",
        display_name="Cashier P13E",
        password_hash=password_hash_for_tests(),
        role="cashier",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    outsider = models.User(
        username="outsider_p13e",
        display_name="Outsider P13E",
        password_hash=password_hash_for_tests(),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    co = models.Company(
        name="Active Co",
        slug="active_co_p13e",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    inactive_co = models.Company(
        name="Inactive Co",
        slug="inactive_co_p13e",
        is_active=False,
        created_at=datetime.datetime.now(),
    )
    other_co = models.Company(
        name="Other Co",
        slug="other_co_p13e",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add_all([owner, cashier, outsider, co, inactive_co, other_co])
    db.flush()
    db.add_all(
        [
            models.CompanyUser(
                company_id=co.id,
                user_id=owner.id,
                role="owner",
                is_active=True,
                created_at=datetime.datetime.now(),
            ),
            models.CompanyUser(
                company_id=co.id,
                user_id=cashier.id,
                role="cashier",
                is_active=True,
                created_at=datetime.datetime.now(),
            ),
            models.CompanyUser(
                company_id=inactive_co.id,
                user_id=owner.id,
                role="owner",
                is_active=True,
                created_at=datetime.datetime.now(),
            ),
            models.CompanyUser(
                company_id=other_co.id,
                user_id=outsider.id,
                role="owner",
                is_active=True,
                created_at=datetime.datetime.now(),
            ),
        ]
    )
    db.commit()
    return {
        "owner": owner,
        "cashier": cashier,
        "outsider": outsider,
        "company_id": co.id,
        "inactive_company_id": inactive_co.id,
        "other_company_id": other_co.id,
    }


def _pl_params():
    return {
        "start_date": FROM_DATE.isoformat(),
        "end_date": TO_DATE.isoformat(),
    }


class TestJwtRuntimeRejectsLegacyHeaders:
    def test_old_headers_without_bearer_rejected(self, api_client, tenant):
        resp = api_client.get(
            "/api/v1/reports/profit-loss",
            params=_pl_params(),
            headers={
                "X-User-Id": str(tenant["owner"].id),
                "X-Company-Id": str(tenant["company_id"]),
                "X-Role": "owner",
            },
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL


class TestJwtRuntimeSuccess:
    def test_valid_bearer_and_company_works(self, api_client, tenant):
        resp = api_client.get(
            "/api/v1/reports/profit-loss",
            params=_pl_params(),
            headers=api_headers(tenant["owner"], company_id=tenant["company_id"]),
        )
        assert resp.status_code == 200


class TestJwtRuntimeAuthFailures:
    def test_missing_bearer_rejected(self, api_client, tenant):
        resp = api_client.get(
            "/api/v1/receivables",
            headers={"X-Company-Id": str(tenant["company_id"])},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_invalid_bearer_rejected(self, api_client, tenant):
        resp = api_client.get(
            "/api/v1/receivables",
            headers=api_headers("not-a-jwt", company_id=tenant["company_id"]),
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_INVALID_DETAIL

    def test_expired_bearer_rejected(self, api_client, tenant):
        token = token_service.issue_access_token(
            tenant["owner"], secret=TEST_JWT_SECRET, ttl_seconds=-30
        )
        resp = api_client.get(
            "/api/v1/receivables",
            headers=api_headers(token, company_id=tenant["company_id"]),
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_INVALID_DETAIL


class TestJwtRuntimeCompanyFailures:
    def test_missing_company_rejected(self, api_client, tenant):
        resp = api_client.get(
            "/api/v1/receivables",
            headers=api_headers(tenant["owner"]),
        )
        assert resp.status_code == 400
        assert COMPANY_MISSING_MARKER in resp.json()["detail"]

    def test_user_without_membership_rejected(self, api_client, tenant):
        resp = api_client.get(
            "/api/v1/receivables",
            headers=api_headers(
                tenant["outsider"], company_id=tenant["company_id"]
            ),
        )
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]

    def test_inactive_company_rejected(self, api_client, tenant):
        resp = api_client.get(
            "/api/v1/receivables",
            headers=api_headers(
                tenant["owner"], company_id=tenant["inactive_company_id"]
            ),
        )
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]


class TestJwtRuntimeDbBackedRole:
    def test_role_from_db_membership_not_header(self, api_client, tenant):
        resp = api_client.get(
            "/api/v1/reports/profit-loss",
            params=_pl_params(),
            headers=api_headers(
                tenant["cashier"],
                company_id=tenant["company_id"],
                role_spoof="owner",
            ),
        )
        assert resp.status_code == 403
        assert "view_management_reports" in resp.json()["detail"]

    def test_spoofed_user_id_ignored(self, api_client, tenant):
        resp = api_client.get(
            "/api/v1/receivables",
            headers=api_headers(
                tenant["cashier"],
                company_id=tenant["other_company_id"],
                user_id_spoof=tenant["outsider"].id,
                role_spoof="owner",
            ),
        )
        assert resp.status_code == 403
        assert MEMBERSHIP_DENIED_MARKER in resp.json()["detail"]


class TestJwtRuntimeDevHeaderFallback:
    def test_dev_headers_work_only_when_flag_enabled(
        self, api_client, tenant, monkeypatch
    ):
        monkeypatch.setenv(DEV_HEADERS_ENV, "1")
        resp = api_client.get(
            "/api/v1/receivables",
            headers={
                "X-User-Id": str(tenant["owner"].id),
                "X-Company-Id": str(tenant["company_id"]),
                "X-Role": "owner",
            },
        )
        assert resp.status_code == 200


class TestJwtRuntimeNoCommits:
    def test_read_get_performs_no_commit(self, api_client, tenant, db):
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get(
                "/api/v1/receivables",
                headers=api_headers(tenant["owner"], company_id=tenant["company_id"]),
            )
        assert resp.status_code == 200
        assert mock_commit.call_count == 0
