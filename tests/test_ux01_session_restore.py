"""UX-01 — narrow session persistence (signed restore token + company revalidation)."""

from __future__ import annotations

import datetime
import hashlib
import hmac
import inspect
import os
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    _st_mock.context = MagicMock(cookies={})
    sys.modules["streamlit"] = _st_mock
else:
    _st_mock = sys.modules["streamlit"]
    if not isinstance(getattr(_st_mock, "session_state", None), dict):
        _st_mock.session_state = {}
    if not hasattr(_st_mock, "context"):
        _st_mock.context = MagicMock(cookies={})

import app as erp
import models
from db import Base

_TEST_SECRET = "ux01-test-restore-secret"


@pytest.fixture(autouse=True)
def restore_secret(monkeypatch):
    monkeypatch.setenv(erp._RESTORE_SECRET_ENV, _TEST_SECRET)
    erp.DEV_MODE = False
    erp.DEVELOPMENT_MODE = False
    yield
    erp.DEV_MODE = False
    erp.DEVELOPMENT_MODE = False


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


def _user(db, username="admin", password="pw"):
    u = models.User(
        username=username,
        display_name=username.title(),
        password_hash=erp._hash_password(password),
        role="viewer",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(u)
    db.flush()
    return u


def _company(db, name: str, slug: str, *, is_active: bool = True):
    c = models.Company(
        name=name,
        slug=slug,
        is_active=is_active,
        created_at=datetime.datetime.now(),
    )
    db.add(c)
    db.flush()
    return c


def _membership(db, user, company, role="manager", *, is_active: bool = True):
    m = models.CompanyUser(
        company_id=company.id,
        user_id=user.id,
        role=role,
        is_active=is_active,
        created_at=datetime.datetime.now(),
    )
    db.add(m)
    db.flush()
    return m


def _signed_token(
    user_id: int,
    exp: int,
    ph_frag: str,
    *,
    company_id: int | None = None,
    secret: str = _TEST_SECRET,
) -> str:
    parts = [str(user_id), "0", str(exp), ph_frag]
    if company_id is not None:
        parts.append(str(company_id))
    payload = ".".join(parts)
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


# ── Token mint / verify ───────────────────────────────────────────────────────


def test_token_mint_verify_round_trip(db):
    user = _user(db)
    db.commit()
    token = erp._mint_restore_token(user.id, user.password_hash, active_company_id=42)
    assert token
    claims = erp._verify_restore_token(token)
    assert claims is not None
    assert claims["user_id"] == user.id
    assert claims["company_id"] == 42
    assert claims["ph_frag"] == erp._password_hash_fragment(user.password_hash)


def test_expired_token_rejected(db):
    user = _user(db)
    db.commit()
    past = int(datetime.datetime.now(datetime.timezone.utc).timestamp()) - 60
    tok = _signed_token(
        user.id, past, erp._password_hash_fragment(user.password_hash)
    )
    assert erp._verify_restore_token(tok) is None


def test_tampered_token_rejected(db):
    user = _user(db)
    db.commit()
    token = erp._mint_restore_token(user.id, user.password_hash)
    assert token
    bad = token[:-4] + "ffff"
    assert erp._verify_restore_token(bad) is None


def test_password_change_invalidates_token(db):
    user = _user(db, password="old")
    db.commit()
    token = erp._mint_restore_token(user.id, user.password_hash)
    user.password_hash = erp._hash_password("new")
    db.commit()
    claims = erp._verify_restore_token(token)
    assert claims is not None
    assert erp._password_hash_fragment(user.password_hash) != claims["ph_frag"]


def test_no_secret_disables_feature(monkeypatch, db):
    monkeypatch.delenv(erp._RESTORE_SECRET_ENV, raising=False)
    user = _user(db)
    db.commit()
    assert erp._restore_secret_configured() is False
    assert erp._mint_restore_token(user.id, user.password_hash) is None
    sys.modules["streamlit"].context.cookies = {
        erp._RESTORE_COOKIE: "anything"
    }
    assert erp._try_restore_session_from_cookie(db) is False


# ── Restore behaviour ─────────────────────────────────────────────────────────


def test_restore_inactive_user_rejected(db):
    user = _user(db)
    user.is_active = False
    db.commit()
    token = erp._mint_restore_token(user.id, user.password_hash)
    sys.modules["streamlit"].context.cookies = {erp._RESTORE_COOKIE: token}
    assert erp._try_restore_session_from_cookie(db) is False


def test_restore_failure_does_not_raise(db):
    sys.modules["streamlit"].context.cookies = {
        erp._RESTORE_COOKIE: "not-a-valid-token"
    }
    assert erp._try_restore_session_from_cookie(db) is False


def test_restore_sets_auth_and_company(db):
    user = _user(db)
    co = _company(db, "Alpha", "alpha")
    _membership(db, user, co, role="owner")
    db.commit()
    token = erp._mint_restore_token(
        user.id, user.password_hash, active_company_id=co.id
    )
    sys.modules["streamlit"].context.cookies = {erp._RESTORE_COOKIE: token}
    assert erp._try_restore_session_from_cookie(db) is True
    assert erp.st.session_state["auth_user"]["id"] == user.id
    assert erp.st.session_state["active_company_id"] == co.id
    assert erp.st.session_state["active_company_role"] == "owner"


def test_revoked_membership_falls_back_to_company_picker(db):
    user = _user(db)
    co_a = _company(db, "Alpha", "alpha")
    co_b = _company(db, "Beta", "beta")
    _membership(db, user, co_a, role="owner")
    _membership(db, user, co_b, role="viewer")
    db.commit()
    mem_b = db.query(models.CompanyUser).filter_by(
        user_id=user.id, company_id=co_b.id
    ).one()
    mem_b.is_active = False
    db.commit()
    token = erp._mint_restore_token(
        user.id, user.password_hash, active_company_id=co_b.id
    )
    sys.modules["streamlit"].context.cookies = {erp._RESTORE_COOKIE: token}
    assert erp._try_restore_session_from_cookie(db) is True
    assert erp.st.session_state.get("auth_user")
    assert erp.st.session_state.get("active_company_id") is None


def test_deactivated_company_falls_back_to_picker(db):
    user = _user(db)
    co = _company(db, "Gone", "gone", is_active=False)
    _membership(db, user, co, role="owner")
    db.commit()
    token = erp._mint_restore_token(
        user.id, user.password_hash, active_company_id=co.id
    )
    sys.modules["streamlit"].context.cookies = {erp._RESTORE_COOKIE: token}
    assert erp._try_restore_session_from_cookie(db) is True
    assert erp.st.session_state.get("active_company_id") is None


def test_role_rederived_from_db_not_token(db):
    user = _user(db)
    co = _company(db, "Alpha", "alpha")
    _membership(db, user, co, role="viewer")
    db.commit()
    token = erp._mint_restore_token(
        user.id, user.password_hash, active_company_id=co.id
    )
    mem = db.query(models.CompanyUser).filter_by(user_id=user.id).one()
    mem.role = "owner"
    db.commit()
    sys.modules["streamlit"].context.cookies = {erp._RESTORE_COOKIE: token}
    erp._try_restore_session_from_cookie(db)
    assert erp.st.session_state["active_company_role"] == "owner"


def test_restore_never_writes_at_or_mob_at_keys(db):
    user = _user(db)
    co = _company(db, "Alpha", "alpha")
    _membership(db, user, co)
    db.commit()
    token = erp._mint_restore_token(
        user.id, user.password_hash, active_company_id=co.id
    )
    sys.modules["streamlit"].context.cookies = {erp._RESTORE_COOKIE: token}
    erp._try_restore_session_from_cookie(db)
    for key in erp.st.session_state:
        assert not key.startswith("at_")
        assert not key.startswith("mob_at_")


def test_date_defaults_to_today_after_restore(db):
    user = _user(db)
    co = _company(db, "Alpha", "alpha")
    _membership(db, user, co)
    db.commit()
    token = erp._mint_restore_token(
        user.id, user.password_hash, active_company_id=co.id
    )
    sys.modules["streamlit"].context.cookies = {erp._RESTORE_COOKIE: token}
    erp._try_restore_session_from_cookie(db)
    assert "at_date" not in erp.st.session_state
    erp._mob_at_ensure_defaults(db, "Expense", "USD", [])
    assert erp.st.session_state["at_date"] == datetime.date.today()


def test_logout_clears_session_and_cookie(monkeypatch):
    calls = []
    monkeypatch.setattr(
        erp, "_render_session_restore_cookie", lambda **kw: calls.append(kw)
    )
    erp.st.session_state["auth_user"] = {"id": 1, "username": "a", "role": "owner"}
    erp.st.session_state["auth_expires"] = datetime.datetime.now() + datetime.timedelta(
        hours=1
    )
    erp.st.session_state["active_company_id"] = 1
    erp._logout()
    assert erp.st.session_state.get(erp._SESSION_LOGGED_OUT) is True
    assert "auth_user" not in erp.st.session_state
    assert calls and calls[-1].get("clear") is True


def test_dev_mode_unaffected(monkeypatch, db):
    erp.DEV_MODE = True
    erp.DEVELOPMENT_MODE = True
    user = _user(db)
    co = _company(db, "Alpha", "alpha")
    _membership(db, user, co)
    db.commit()
    token = erp._mint_restore_token(
        user.id, user.password_hash, active_company_id=co.id
    )
    sys.modules["streamlit"].context.cookies = {erp._RESTORE_COOKIE: token}
    assert erp._try_restore_session_from_cookie(db) is False
    src = inspect.getsource(erp._dev_auto_login)
    assert "_try_restore_session_from_cookie" not in src


def test_main_wires_restore_before_auth_gate():
    src = inspect.getsource(erp.main)
    assert "_try_restore_session_from_cookie" in src
    restore_pos = src.index("_try_restore_session_from_cookie")
    login_pos = src.index("render_login")
    assert restore_pos < login_pos


def test_cookie_component_skipped_in_dev_mode(monkeypatch):
    erp.DEV_MODE = True
    called = []
    monkeypatch.setattr(erp, "st", MagicMock(html=lambda *a, **k: called.append(True)))
    erp._render_session_restore_cookie(token="x")
    assert called == []
