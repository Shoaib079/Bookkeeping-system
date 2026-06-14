"""FASTAPI-P1.3c — POST /auth/login contract tests."""

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
from api.dependencies import get_db
from api.main import create_app
from db import Base
from services import auth as auth_service
from services import login as login_service
from services import tokens as token_service

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

_TEST_SECRET = "p13c-test-jwt-secret-32-bytes-minimum!"
_PASSWORD = "admin123"
_BAD_DETAIL = {
    "code": login_service.INVALID_CREDENTIALS_CODE,
    "message": login_service.INVALID_CREDENTIALS_MESSAGE,
}


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


def _seed_user(db, *, username="alice", password=_PASSWORD, active=True):
    user = models.User(
        username=username,
        display_name=username.title(),
        password_hash=auth_service.hash_password(password),
        role="owner",
        is_active=active,
        created_at=datetime.datetime.now(),
    )
    db.add(user)
    db.commit()
    return user


class TestLoginSuccess:
    def test_success_returns_bearer_token(self, api_client, db):
        _seed_user(db, username="alice")
        resp = api_client.post(
            "/auth/login",
            json={"username": "alice", "password": _PASSWORD},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == token_service.DEFAULT_ACCESS_TTL_SECONDS
        assert isinstance(body["access_token"], str)
        assert body["access_token"]

    def test_token_verifies_with_verify_access_token(self, api_client, db):
        user = _seed_user(db, username="bob")
        resp = api_client.post(
            "/auth/login",
            json={"username": "bob", "password": _PASSWORD},
        )
        token = resp.json()["access_token"]
        verified = token_service.verify_access_token(token, db, secret=_TEST_SECRET)
        assert verified.id == user.id

    def test_token_payload_has_no_role_permissions_or_company(self, api_client, db):
        _seed_user(db, username="carol")
        resp = api_client.post(
            "/auth/login",
            json={"username": "carol", "password": _PASSWORD},
        )
        claims = token_service.access_token_claims(
            resp.json()["access_token"], secret=_TEST_SECRET
        )
        assert "role" not in claims
        assert "permissions" not in claims
        assert "company_id" not in claims
        assert "active_company_id" not in claims
        assert "membership_role" not in claims


class TestLoginFailures:
    def test_wrong_password_rejected(self, api_client, db):
        _seed_user(db, username="dave")
        resp = api_client.post(
            "/auth/login",
            json={"username": "dave", "password": "wrong-password"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == _BAD_DETAIL

    def test_unknown_user_same_error_shape(self, api_client, db):
        resp = api_client.post(
            "/auth/login",
            json={"username": "nobody", "password": _PASSWORD},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == _BAD_DETAIL

    def test_inactive_user_same_public_error_shape(self, api_client, db):
        _seed_user(db, username="inactive", active=False)
        resp = api_client.post(
            "/auth/login",
            json={"username": "inactive", "password": _PASSWORD},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == _BAD_DETAIL

    def test_wrong_password_and_unknown_user_match(self, api_client, db):
        _seed_user(db, username="erin")
        bad_pw = api_client.post(
            "/auth/login",
            json={"username": "erin", "password": "nope"},
        )
        unknown = api_client.post(
            "/auth/login",
            json={"username": "missing", "password": "nope"},
        )
        assert bad_pw.json() == unknown.json()
        assert bad_pw.status_code == unknown.status_code == 401


class TestStreamlitAuthUnchanged:
    def test_app_login_behavior_unchanged(self, db):
        import app as erp_app
        from registry.i18n import t

        sys.modules["streamlit"].session_state.clear()
        user = models.User(
            username="streamlit_user",
            display_name="Streamlit User",
            password_hash=erp_app._hash_password(_PASSWORD),
            role="owner",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        db.add(user)
        db.commit()

        assert erp_app._login(db, "streamlit_user", "wrong") == t(
            "login.bad_credentials", "en"
        )
        assert erp_app._login(db, "streamlit_user", _PASSWORD) is None
        assert sys.modules["streamlit"].session_state["auth_user"]["username"] == (
            "streamlit_user"
        )


class TestLoginNoGetCommits:
    def test_health_get_still_performs_no_commit(self, api_client, db):
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.get("/health")
        assert resp.status_code == 200
        assert mock_commit.call_count == 0

    def test_login_post_performs_no_commit(self, api_client, db):
        _seed_user(db, username="frank")
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            resp = api_client.post(
                "/auth/login",
                json={"username": "frank", "password": _PASSWORD},
            )
        assert resp.status_code == 200
        assert mock_commit.call_count == 0
