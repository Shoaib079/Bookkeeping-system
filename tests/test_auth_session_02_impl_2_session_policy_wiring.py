"""AUTH-SESSION-02-IMPL-2 — SessionPolicy wired into app.py auth flow."""

from __future__ import annotations

import datetime
import inspect
import sys
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock
    sys.modules["streamlit.components"] = MagicMock()
    sys.modules["streamlit.components.v1"] = MagicMock()
else:
    _st_mock = sys.modules["streamlit"]
    if not isinstance(getattr(_st_mock, "session_state", None), dict):
        _st_mock.session_state = {}
    if not hasattr(_st_mock, "context"):
        _st_mock.context = MagicMock(cookies={})
    if getattr(_st_mock, "__path__", None) is None:
        if "streamlit.components" not in sys.modules:
            sys.modules["streamlit.components"] = MagicMock()
        if "streamlit.components.v1" not in sys.modules:
            sys.modules["streamlit.components.v1"] = MagicMock()

import app as erp
import models
from db import Base
from services.session_policy import MODE_BROWSER_SESSION, build_session_policy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_TEST_SECRET = "auth-session-02-impl-2-test-secret"
_EIGHT_HOURS = 8 * 3600


@pytest.fixture(autouse=True)
def restore_env(monkeypatch):
    monkeypatch.setenv(erp._RESTORE_SECRET_ENV, _TEST_SECRET)
    erp.DEV_MODE = False
    erp.DEVELOPMENT_MODE = False
    yield


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    sys.modules["streamlit"].context.cookies = {}
    yield
    sys.modules["streamlit"].session_state.clear()
    sys.modules["streamlit"].context.cookies = {}


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


def _user(db, *, password="pw"):
    u = models.User(
        username="sess02",
        display_name="Sess02",
        password_hash=erp._hash_password(password),
        role="viewer",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(u)
    db.flush()
    return u


class TestPolicyWiringSource:
    def test_active_session_policy_uses_browser_session(self):
        policy = erp._active_session_policy()
        assert policy.mode == MODE_BROWSER_SESSION
        assert policy.should_remember_device is False

    def test_legacy_ttl_constants_match_browser_policy(self):
        policy = build_session_policy(MODE_BROWSER_SESSION)
        assert erp._SESSION_TTL_HOURS == policy.idle_ttl_seconds // 3600
        assert erp._RESTORE_TOKEN_TTL_HOURS == policy.cookie_ttl_seconds // 3600
        assert erp._SESSION_TTL_HOURS == 8
        assert erp._RESTORE_TOKEN_TTL_HOURS == 8

    def test_establish_auth_session_uses_compute_session_expiry(self):
        src = inspect.getsource(erp._establish_auth_session)
        assert "compute_session_expiry" in src
        assert "session_started_at" in src
        assert "_active_session_policy" in src
        assert "timedelta(hours=_SESSION_TTL_HOURS)" not in src

    def test_mint_restore_token_uses_policy_cookie_ttl(self):
        src = inspect.getsource(erp._mint_restore_token)
        assert "cookie_ttl_seconds" in src
        assert "_RESTORE_TOKEN_TTL_HOURS * 3600" not in src

    def test_render_cookie_uses_policy_cookie_ttl(self):
        src = inspect.getsource(erp._render_session_restore_cookie)
        assert "cookie_ttl_seconds" in src
        assert "_RESTORE_TOKEN_TTL_HOURS * 3600" not in src

    def test_no_remember_device_checkbox_in_login(self):
        src = inspect.getsource(erp.render_login)
        assert "should_remember_device" not in src
        assert "remember_device" not in src
        assert "remember me" not in src.lower()

    def test_logout_clears_session_started_at(self):
        src = inspect.getsource(erp._logout)
        assert '"session_started_at"' in src


class TestEstablishAndRestoreBehavior:
    def test_establish_sets_session_started_at_and_8h_expiry(self, db):
        before = datetime.datetime.now()
        user = _user(db)
        erp._establish_auth_session(db, user)
        after = datetime.datetime.now()
        started = erp.st.session_state["session_started_at"]
        expires = erp.st.session_state["auth_expires"]
        assert before <= started <= after
        assert expires - started == datetime.timedelta(seconds=_EIGHT_HOURS)

    def test_restore_sets_session_started_at(self, db):
        user = _user(db)
        token = erp._mint_restore_token(user.id, user.password_hash)
        assert token is not None
        erp.st.context.cookies = {erp._RESTORE_COOKIE: token}
        before = datetime.datetime.now()
        assert erp._try_restore_session_from_cookie(db) is True
        after = datetime.datetime.now()
        started = erp.st.session_state.get("session_started_at")
        assert started is not None
        assert before <= started <= after
        assert erp.st.session_state.get("auth_user", {}).get("id") == user.id

    def test_restore_token_expiry_is_8h(self, db):
        user = _user(db)
        token = erp._mint_restore_token(user.id, user.password_hash)
        claims = erp._verify_restore_token(token)
        assert claims is not None
        assert claims["exp"] - claims["iat"] == _EIGHT_HOURS

    def test_cookie_max_age_is_8h(self, monkeypatch):
        captured: list[str] = []

        def _capture_html(script, **kwargs):
            captured.append(script)

        monkeypatch.setattr(
            sys.modules["streamlit.components.v1"], "html", _capture_html
        )
        erp._render_session_restore_cookie(token="signed-token")
        assert len(captured) == 1
        assert f"max-age={_EIGHT_HOURS}" in captured[0]

    def test_active_policy_not_remember_device(self):
        assert erp._active_session_policy().should_remember_device is False
        assert erp._active_session_policy().cookie_ttl_seconds == _EIGHT_HOURS
