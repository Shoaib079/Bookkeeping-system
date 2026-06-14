"""FASTAPI-P1.3b — access token service scaffolding contract tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import jwt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from db import Base
from services import auth as auth_service
from services import tokens as token_service

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock

_TEST_SECRET = "p13b-test-jwt-secret-32-bytes-minimum!!"


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


def _user(db, *, active: bool = True, password: str = "admin123"):
    u = models.User(
        username="token_user",
        display_name="Token User",
        password_hash=auth_service.hash_password(password),
        role="owner",
        is_active=active,
        created_at=datetime.datetime.now(),
    )
    db.add(u)
    db.commit()
    return u


class TestPasswordParity:
    def test_hash_and_verify_match_streamlit_helpers(self):
        import app as erp_app

        stored = erp_app._hash_password("secret-pw")
        assert auth_service.hash_password("x") != stored
        assert erp_app._verify_password("secret-pw", stored) is True
        assert auth_service.verify_password("secret-pw", stored) is True
        assert erp_app._verify_password("wrong", stored) is False
        assert auth_service.verify_password("wrong", stored) is False

    def test_password_hash_fragment_matches_streamlit_helper(self):
        import app as erp_app

        stored = erp_app._hash_password("frag")
        assert erp_app._password_hash_fragment(stored) == auth_service.password_hash_fragment(
            stored
        )


class TestAccessTokenRoundtrip:
    def test_issue_and_verify_returns_active_user(self, db):
        user = _user(db)
        token = token_service.issue_access_token(user, secret=_TEST_SECRET)
        verified = token_service.verify_access_token(token, db, secret=_TEST_SECRET)
        assert verified.id == user.id
        assert verified.is_active is True

    def test_token_claims_are_identity_only(self, db):
        user = _user(db)
        token = token_service.issue_access_token(
            user,
            secret=_TEST_SECRET,
            jti="fixed-jti",
            token_version=3,
        )
        claims = token_service.access_token_claims(token, secret=_TEST_SECRET)
        assert claims["sub"] == str(user.id)
        assert claims["ph_frag"] == auth_service.password_hash_fragment(user.password_hash)
        assert claims["jti"] == "fixed-jti"
        assert claims["token_version"] == 3
        assert "role" not in claims
        assert "permissions" not in claims
        assert "company_id" not in claims
        assert "active_company_id" not in claims


class TestAccessTokenDenials:
    def test_expired_token_denied(self, db):
        user = _user(db)
        token = token_service.issue_access_token(
            user, secret=_TEST_SECRET, ttl_seconds=-60
        )
        with pytest.raises(token_service.AuthError, match="expired"):
            token_service.verify_access_token(token, db, secret=_TEST_SECRET)

    def test_password_change_invalidates_token(self, db):
        user = _user(db)
        token = token_service.issue_access_token(user, secret=_TEST_SECRET)
        user.password_hash = auth_service.hash_password("new-password")
        db.commit()
        with pytest.raises(token_service.AuthError, match="credential change"):
            token_service.verify_access_token(token, db, secret=_TEST_SECRET)

    def test_inactive_user_denied(self, db):
        user = _user(db, active=False)
        token = token_service.issue_access_token(user, secret=_TEST_SECRET)
        with pytest.raises(token_service.AuthError, match="Inactive"):
            token_service.verify_access_token(token, db, secret=_TEST_SECRET)

    def test_invalid_signature_denied(self, db):
        user = _user(db)
        token = token_service.issue_access_token(user, secret=_TEST_SECRET)
        with pytest.raises(token_service.AuthError, match="Invalid"):
            token_service.verify_access_token(
                token, db, secret="other-secret-32-bytes-minimum!!"
            )

    def test_missing_subject_denied(self, db):
        user = _user(db)
        now = datetime.datetime.now(datetime.timezone.utc)
        raw = jwt.encode(
            {
                "iat": now,
                "exp": now + datetime.timedelta(minutes=5),
                "ph_frag": auth_service.password_hash_fragment(user.password_hash),
            },
            _TEST_SECRET,
            algorithm="HS256",
        )
        with pytest.raises(token_service.AuthError, match="subject"):
            token_service.verify_access_token(raw, db, secret=_TEST_SECRET)
