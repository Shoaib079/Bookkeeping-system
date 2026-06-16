"""AUTH-SESSION-02-IMPL-3 — idle session extension wired into Streamlit auth flow."""

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
from services.session_policy import (
    MODE_BROWSER_SESSION,
    MODE_REMEMBER_DEVICE,
    build_session_policy,
    compute_session_expiry,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_TEST_SECRET = "auth-session-02-impl-3-test-secret"
_EIGHT_HOURS = 8 * 3600
_DEV_USER = {
    "id": 1,
    "username": "admin",
    "display_name": "Admin",
    "role": "owner",
    "email": "",
    "phone": "",
    "last_login": None,
    "created_at": None,
}


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
        username="impl3",
        display_name="Impl3",
        password_hash=erp._hash_password(password),
        role="viewer",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(u)
    db.flush()
    return u


def _seed_active_session(
    *,
    started_at: datetime.datetime,
    expires_at: datetime.datetime,
) -> None:
    erp.st.session_state["auth_user"] = dict(_DEV_USER)
    erp.st.session_state["session_started_at"] = started_at
    erp.st.session_state["auth_expires"] = expires_at


class TestIdleExtensionWiring:
    def test_main_calls_maybe_extend_idle_session(self):
        src = inspect.getsource(erp.main)
        assert "_maybe_extend_idle_session" in src
        assert "should_extend_idle" in inspect.getsource(erp._maybe_extend_idle_session)
        assert "compute_session_expiry" in inspect.getsource(erp._maybe_extend_idle_session)

    def test_helper_does_not_clear_session_started_at(self):
        src = inspect.getsource(erp._maybe_extend_idle_session)
        assert "session_started_at" in src
        assert 'pop("session_started_at"' not in src

    def test_no_remember_device_checkbox_in_login(self):
        src = inspect.getsource(erp.render_login)
        assert "should_remember_device" not in src
        assert "remember_device" not in src
        assert "remember me" not in src.lower()


class TestIdleExtensionBehavior:
    def test_extends_auth_expires_when_absolute_allows(self, monkeypatch):
        now = datetime.datetime.now()
        started = now - datetime.timedelta(hours=1)
        current = now + datetime.timedelta(hours=2)
        _seed_active_session(started_at=started, expires_at=current)
        remember = build_session_policy(MODE_REMEMBER_DEVICE)
        monkeypatch.setattr(erp, "_active_session_policy", lambda: remember)

        assert erp._maybe_extend_idle_session() is True
        assert erp.st.session_state["session_started_at"] == started
        expected = compute_session_expiry(
            now, remember, session_started_at=started
        )
        actual = erp.st.session_state["auth_expires"]
        assert actual > current
        assert abs((actual - expected).total_seconds()) < 0.05

    def test_auth_expires_does_not_exceed_absolute_cap(self, monkeypatch):
        now = datetime.datetime.now()
        started = now - datetime.timedelta(days=29, hours=20)
        current = now + datetime.timedelta(hours=1)
        _seed_active_session(started_at=started, expires_at=current)
        remember = build_session_policy(MODE_REMEMBER_DEVICE)
        monkeypatch.setattr(erp, "_active_session_policy", lambda: remember)

        assert erp._maybe_extend_idle_session() is True
        expected = compute_session_expiry(
            now, remember, session_started_at=started
        )
        assert erp.st.session_state["auth_expires"] == expected
        assert erp.st.session_state["auth_expires"] < now + datetime.timedelta(
            hours=8
        )

    def test_session_started_at_unchanged_on_extension(self, monkeypatch):
        now = datetime.datetime.now()
        started = now - datetime.timedelta(hours=2)
        current = now + datetime.timedelta(hours=1)
        _seed_active_session(started_at=started, expires_at=current)
        monkeypatch.setattr(
            erp,
            "_active_session_policy",
            lambda: build_session_policy(MODE_REMEMBER_DEVICE),
        )

        erp._maybe_extend_idle_session()
        assert erp.st.session_state["session_started_at"] == started

    def test_browser_session_no_extension_when_idle_equals_absolute(self):
        now = datetime.datetime.now()
        started = now - datetime.timedelta(hours=1)
        browser = build_session_policy(MODE_BROWSER_SESSION)
        current = compute_session_expiry(now, browser, session_started_at=started)
        _seed_active_session(started_at=started, expires_at=current)

        assert erp._maybe_extend_idle_session() is False
        assert erp.st.session_state["auth_expires"] == current

    def test_expired_session_not_revived(self):
        now = datetime.datetime.now()
        expired = now - datetime.timedelta(minutes=5)
        started = now - datetime.timedelta(hours=2)
        _seed_active_session(started_at=started, expires_at=expired)

        assert erp._maybe_extend_idle_session() is False
        assert erp.st.session_state["auth_expires"] == expired

    def test_logged_out_flag_blocks_extension(self):
        now = datetime.datetime.now()
        _seed_active_session(
            started_at=now - datetime.timedelta(hours=1),
            expires_at=now + datetime.timedelta(hours=2),
        )
        erp.st.session_state[erp._SESSION_LOGGED_OUT] = True

        assert erp._maybe_extend_idle_session() is False


class TestLogoutAndDevMode:
    def test_logout_clears_session_started_at(self, db):
        user = _user(db)
        erp._establish_auth_session(db, user)
        assert erp.st.session_state.get("session_started_at") is not None
        erp._logout()
        assert "session_started_at" not in erp.st.session_state
        assert "auth_expires" not in erp.st.session_state
        assert "auth_user" not in erp.st.session_state

    def test_dev_mode_restore_still_skipped(self, monkeypatch, db):
        erp.DEV_MODE = True
        user = _user(db)
        token = erp._mint_restore_token(user.id, user.password_hash)
        assert token is not None
        sys.modules["streamlit"].context.cookies = {erp._RESTORE_COOKIE: token}
        assert erp._try_restore_session_from_cookie(db) is False

    def test_dev_mode_cookie_render_still_noop(self, monkeypatch):
        erp.DEV_MODE = True
        captured: list[str] = []
        monkeypatch.setattr(
            sys.modules["streamlit.components.v1"], "html", lambda s, **k: captured.append(s)
        )
        erp._render_session_restore_cookie(token="tok")
        assert captured == []


class TestRestoreCookieCompatibility:
    def test_cookie_refresh_after_extension_uses_browser_ttl(self, db, monkeypatch):
        user = _user(db)
        erp._establish_auth_session(db, user)
        erp._maybe_extend_idle_session()

        captured: list[str] = []
        monkeypatch.setattr(
            sys.modules["streamlit.components.v1"], "html", lambda s, **k: captured.append(s)
        )
        token = erp._mint_restore_token_for_user(db, user.id)
        assert token is not None
        erp._render_session_restore_cookie(token=token)
        assert len(captured) == 1
        assert f"max-age={_EIGHT_HOURS}" in captured[0]
        assert "max-age=2592000" not in captured[0]

    def test_restore_token_still_8h_not_30d(self, db):
        user = _user(db)
        token = erp._mint_restore_token(user.id, user.password_hash)
        claims = erp._verify_restore_token(token)
        assert claims is not None
        assert claims["exp"] - claims["iat"] == _EIGHT_HOURS
