"""DEV-AUTH-01 — development authentication bypass."""

from __future__ import annotations

import datetime
import importlib
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock
else:
    _st_mock = sys.modules["streamlit"]
    if not isinstance(getattr(_st_mock, "session_state", None), dict):
        _st_mock.session_state = {}

app.DEV_MODE = False
app.DEVELOPMENT_MODE = False


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


def _user(db, username="admin", role="owner"):
    u = models.User(
        username=username,
        display_name=username.title(),
        password_hash=app._hash_password("admin123"),
        role=role,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(u)
    db.flush()
    return u


def _company(db, name="Acme", slug="company_1"):
    c = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(c)
    db.flush()
    return c


def _membership(db, user, company, role="owner"):
    m = models.CompanyUser(
        company_id=company.id,
        user_id=user.id,
        role=role,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(m)
    db.flush()
    return m


def _ss():
    return sys.modules["streamlit"].session_state


def test_dev_mode_defaults_off_without_env(monkeypatch):
    monkeypatch.delenv("ERP_DEV_MODE", raising=False)
    importlib.reload(app)
    assert app.DEV_MODE is False
    assert app.DEVELOPMENT_MODE is False
    importlib.reload(app)


def test_dev_mode_on_when_env_set(monkeypatch):
    monkeypatch.setenv("ERP_DEV_MODE", "1")
    importlib.reload(app)
    assert app.DEV_MODE is True
    assert app.DEVELOPMENT_MODE is True
    monkeypatch.delenv("ERP_DEV_MODE", raising=False)
    importlib.reload(app)


def test_dev_auto_login_establishes_normal_session(db, monkeypatch):
    monkeypatch.setattr(app, "DEV_MODE", True)
    monkeypatch.setattr(app, "DEVELOPMENT_MODE", True)
    u = _user(db, "admin")
    co = _company(db)
    _membership(db, u, co, role="owner")
    db.commit()

    err = app._dev_auto_login(db)
    assert err is None
    ss = _ss()
    assert ss["auth_user"]["username"] == "admin"
    assert ss["auth_user"]["id"] == u.id
    assert "auth_expires" in ss
    assert ss["active_company_id"] == co.id
    assert ss["active_company_role"] == "owner"
    assert ss["active_company_membership_count"] == 1
    assert app._current_user() is not None


def test_dev_auto_login_uses_configurable_username(db, monkeypatch):
    monkeypatch.setattr(app, "DEV_MODE", True)
    monkeypatch.setattr(app, "_DEV_USERNAME", "devuser")
    u = _user(db, "devuser", role="manager")
    co = _company(db, slug="dev_co")
    _membership(db, u, co, role="manager")
    db.commit()

    err = app._dev_auto_login(db)
    assert err is None
    assert _ss()["auth_user"]["username"] == "devuser"
    assert _ss()["active_company_role"] == "manager"


def test_normal_login_unchanged_when_dev_mode_off(db):
    u = _user(db, "alice")
    co = _company(db, slug="alice_co")
    _membership(db, u, co)
    db.commit()

    bad = app._login(db, "alice", "wrong")
    assert bad is not None
    assert "auth_user" not in _ss()

    ok = app._login(db, "alice", "admin123")
    assert ok is None
    assert _ss()["auth_user"]["username"] == "alice"
    assert _ss()["active_company_id"] == co.id


def test_dev_mode_does_not_bypass_password_login(db, monkeypatch):
    monkeypatch.setattr(app, "DEV_MODE", True)
    _user(db, "admin")
    db.commit()

    assert app._dev_auto_login(db) is None
    assert _ss()["auth_user"]["username"] == "admin"

    app._logout()
    err = app._login(db, "admin", "bad-password")
    assert err is not None
    assert app._current_user() is None


def test_dev_auto_login_skipped_after_explicit_logout(db, monkeypatch):
    monkeypatch.setattr(app, "DEV_MODE", True)
    _user(db, "admin")
    db.commit()

    app._logout()
    assert app._dev_auto_login(db) is None
    assert "auth_user" not in _ss()


def test_dev_banner_copy_in_messages():
    from registry.i18n import t

    banner = t("dev.banner", "en")
    assert "DEVELOPMENT MODE ACTIVE" in banner
    assert "Authentication bypass enabled" in banner
