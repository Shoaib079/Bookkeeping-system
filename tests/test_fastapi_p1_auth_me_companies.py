"""FASTAPI-P1.3d — GET /auth/me and GET /auth/companies contract tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from api.bearer_auth import BEARER_INVALID_DETAIL, BEARER_MISSING_DETAIL
from api.dependencies import get_db
from api.errors import COMPANY_MISSING_MARKER
from api.main import create_app
from db import Base
from services import auth as auth_service
from services import tokens as token_service

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

_TEST_SECRET = "p13d-test-jwt-secret-32-bytes-minimum!!"
_PASSWORD = "admin123"
FROM_DATE = datetime.date(2026, 6, 1)
TO_DATE = datetime.date(2026, 6, 30)


@pytest.fixture(autouse=True)
def jwt_secret(monkeypatch):
    monkeypatch.setenv(token_service.JWT_SECRET_ENV, _TEST_SECRET)


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


def _user(
    db,
    *,
    username="alice",
    password=_PASSWORD,
    active=True,
    display_name="Alice Owner",
):
    user = models.User(
        username=username,
        display_name=display_name,
        password_hash=auth_service.hash_password(password),
        role="owner",
        is_active=active,
        created_at=datetime.datetime.now(),
    )
    db.add(user)
    db.flush()
    return user


def _company(db, *, name: str, slug: str):
    co = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.flush()
    return co


def _membership(db, *, user_id: int, company_id: int, role: str, active=True):
    row = models.CompanyUser(
        company_id=company_id,
        user_id=user_id,
        role=role,
        is_active=active,
        created_at=datetime.datetime.now(),
    )
    db.add(row)
    db.flush()
    return row


def _token_for(user, **kwargs) -> str:
    return token_service.issue_access_token(user, secret=_TEST_SECRET, **kwargs)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def tenant(db):
    user = _user(db, username="alice", display_name="Alice Owner")
    co_a = _company(db, name="Alpha Co", slug="alpha_co")
    co_b = _company(db, name="Beta Co", slug="beta_co")
    co_other = _company(db, name="Other Co", slug="other_co")
    _membership(db, user_id=user.id, company_id=co_a.id, role="owner")
    _membership(db, user_id=user.id, company_id=co_b.id, role="cashier")
    other_user = _user(db, username="bob", display_name="Bob Only")
    _membership(db, user_id=other_user.id, company_id=co_other.id, role="owner")
    db.add(
        models.AppSetting(
            key=f"user_pref_{user.id}_last_active_company_id",
            value=str(co_b.id),
        )
    )
    db.commit()
    return {
        "user": user,
        "company_a_id": co_a.id,
        "company_b_id": co_b.id,
        "other_company_id": co_other.id,
        "other_user": other_user,
    }


class TestAuthMe:
    def test_me_works_with_valid_bearer_token(self, api_client, tenant):
        token = _token_for(tenant["user"])
        resp = api_client.get("/auth/me", headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        assert body == {
            "id": tenant["user"].id,
            "username": "alice",
            "display_name": "Alice Owner",
            "is_active": True,
        }

    def test_me_rejects_missing_token(self, api_client, tenant):
        resp = api_client.get("/auth/me")
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_me_rejects_invalid_token(self, api_client, tenant):
        resp = api_client.get("/auth/me", headers=_auth("not-a-jwt"))
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_INVALID_DETAIL

    def test_me_rejects_expired_token(self, api_client, tenant):
        token = _token_for(tenant["user"], ttl_seconds=-30)
        resp = api_client.get("/auth/me", headers=_auth(token))
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_INVALID_DETAIL

    def test_me_rejects_inactive_user_through_verify_path(self, api_client, db, tenant):
        token = _token_for(tenant["user"])
        tenant["user"].is_active = False
        db.commit()
        resp = api_client.get("/auth/me", headers=_auth(token))
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_INVALID_DETAIL

    def test_me_does_not_expose_password_hash(self, api_client, tenant):
        token = _token_for(tenant["user"])
        resp = api_client.get("/auth/me", headers=_auth(token))
        body = resp.json()
        assert "password_hash" not in body
        assert "ph_frag" not in body

    def test_me_includes_token_version_when_present(self, api_client, db, tenant):
        tenant["user"].token_version = 7
        db.commit()
        token = _token_for(tenant["user"], token_version=7)
        resp = api_client.get("/auth/me", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["token_version"] == 7


class TestAuthCompanies:
    def test_companies_returns_only_memberships_for_user(self, api_client, tenant):
        token = _token_for(tenant["user"])
        resp = api_client.get("/auth/companies", headers=_auth(token))
        assert resp.status_code == 200
        companies = resp.json()["companies"]
        assert len(companies) == 2
        assert {c["company_id"] for c in companies} == {
            tenant["company_a_id"],
            tenant["company_b_id"],
        }
        by_id = {c["company_id"]: c for c in companies}
        assert by_id[tenant["company_a_id"]] == {
            "company_id": tenant["company_a_id"],
            "company_name": "Alpha Co",
            "role": "owner",
            "is_default": False,
        }
        assert by_id[tenant["company_b_id"]] == {
            "company_id": tenant["company_b_id"],
            "company_name": "Beta Co",
            "role": "cashier",
            "is_default": True,
        }

    def test_companies_excludes_without_membership(self, api_client, tenant):
        token = _token_for(tenant["user"])
        resp = api_client.get("/auth/companies", headers=_auth(token))
        ids = {c["company_id"] for c in resp.json()["companies"]}
        assert tenant["other_company_id"] not in ids

    def test_companies_excludes_inactive_membership(self, api_client, db, tenant):
        db.add(
            models.CompanyUser(
                company_id=tenant["other_company_id"],
                user_id=tenant["user"].id,
                role="viewer",
                is_active=False,
                created_at=datetime.datetime.now(),
            )
        )
        db.commit()
        token = _token_for(tenant["user"])
        resp = api_client.get("/auth/companies", headers=_auth(token))
        ids = {c["company_id"] for c in resp.json()["companies"]}
        assert tenant["other_company_id"] not in ids

    def test_companies_rejects_missing_token(self, api_client, tenant):
        resp = api_client.get("/auth/companies")
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_MISSING_DETAIL

    def test_companies_rejects_invalid_token(self, api_client, tenant):
        resp = api_client.get("/auth/companies", headers=_auth("bad-token"))
        assert resp.status_code == 401
        assert resp.json()["detail"] == BEARER_INVALID_DETAIL


class TestReadEndpointsUseBearer:
    def test_read_endpoint_requires_company_with_bearer(self, api_client, tenant):
        token = _token_for(tenant["user"])
        resp = api_client.get(
            "/api/v1/reports/profit-loss",
            params={
                "start_date": FROM_DATE.isoformat(),
                "end_date": TO_DATE.isoformat(),
            },
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert COMPANY_MISSING_MARKER in resp.json()["detail"]


class TestAuthMeCompaniesNoCommits:
    def test_me_get_performs_no_commit(self, api_client, tenant, db):
        token = _token_for(tenant["user"])
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get("/auth/me", headers=_auth(token))
        assert resp.status_code == 200
        assert mock_commit.call_count == 0

    def test_companies_get_performs_no_commit(self, api_client, tenant, db):
        token = _token_for(tenant["user"])
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get("/auth/companies", headers=_auth(token))
        assert resp.status_code == 200
        assert mock_commit.call_count == 0
