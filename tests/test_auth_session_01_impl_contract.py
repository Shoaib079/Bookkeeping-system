"""AUTH-SESSION-01-IMPL-1 — session restore config/operator + contract tests."""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_TEST_SECRET = "auth-session-01-impl-test-secret"
_OPERATOR_DOC = Path(__file__).resolve().parents[1] / "docs" / "AUTH_SESSION_01_OPERATOR.md"
_IMPL_DOC = Path(__file__).resolve().parents[1] / "docs" / "AUTH_SESSION_01_IMPLEMENTATION.md"


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
        username="admin",
        display_name="Admin",
        password_hash=erp._hash_password(password),
        role="viewer",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(u)
    db.flush()
    return u


# ── Operator documentation contract ───────────────────────────────────────────


def test_operator_doc_exists():
    assert _OPERATOR_DOC.exists()
    assert _OPERATOR_DOC.stat().st_size > 0


@pytest.fixture(scope="module")
def operator_text() -> str:
    return _OPERATOR_DOC.read_text(encoding="utf-8")


def test_operator_doc_covers_secret_and_dev_mode(operator_text):
    lowered = operator_text.lower()
    assert "erp_session_restore_secret" in lowered
    assert "erp_dev_mode" in lowered or "dev_mode" in lowered
    assert "dev" in lowered and "skip" in lowered


def test_operator_doc_covers_generation_and_local_setup(operator_text):
    lowered = operator_text.lower()
    assert "secrets.token_urlsafe" in lowered or "openssl rand" in lowered
    assert "export erp_session_restore_secret" in lowered


def test_operator_doc_covers_ttl_logout_password_limitations(operator_text):
    lowered = operator_text.lower()
    assert "8" in lowered and "hour" in lowered
    assert "logout" in lowered
    assert "password" in lowered
    assert "httponly" in lowered
    assert "fastapi" in lowered or "jwt" in lowered


def test_implementation_doc_exists():
    assert _IMPL_DOC.exists()
    text = _IMPL_DOC.read_text(encoding="utf-8").lower()
    assert "implemented" in text
    assert "operator" in text


# ── Behavioral contract (extends test_ux01_session_restore gaps) ────────────


def test_secret_unset_mint_and_restore_noop(monkeypatch, db):
    monkeypatch.delenv(erp._RESTORE_SECRET_ENV, raising=False)
    user = _user(db)
    db.commit()
    assert erp._restore_secret_configured() is False
    assert erp._mint_restore_token(user.id, user.password_hash) is None
    sys.modules["streamlit"].context.cookies = {erp._RESTORE_COOKIE: "any-token"}
    assert erp._try_restore_session_from_cookie(db) is False


def test_secret_set_mint_verify_round_trip(db):
    user = _user(db)
    db.commit()
    token = erp._mint_restore_token(user.id, user.password_hash)
    assert token
    claims = erp._verify_restore_token(token)
    assert claims is not None
    assert claims["user_id"] == user.id


def test_restore_rejects_ph_frag_mismatch(db):
    user = _user(db, password="old")
    db.commit()
    token = erp._mint_restore_token(user.id, user.password_hash)
    user.password_hash = erp._hash_password("new")
    db.commit()
    sys.modules["streamlit"].context.cookies = {erp._RESTORE_COOKIE: token}
    assert erp._try_restore_session_from_cookie(db) is False
    assert "auth_user" not in erp.st.session_state


def test_logout_blocks_subsequent_restore(db):
    user = _user(db)
    co = models.Company(
        name="Co",
        slug="co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.flush()
    db.add(
        models.CompanyUser(
            company_id=co.id,
            user_id=user.id,
            role="owner",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
    )
    db.commit()
    token = erp._mint_restore_token(
        user.id, user.password_hash, active_company_id=co.id
    )
    erp._logout()
    sys.modules["streamlit"].context.cookies = {erp._RESTORE_COOKIE: token}
    assert erp._try_restore_session_from_cookie(db) is False


def test_render_cookie_noop_when_secret_unset(monkeypatch):
    monkeypatch.delenv(erp._RESTORE_SECRET_ENV, raising=False)
    called: list[bool] = []
    monkeypatch.setattr(
        sys.modules["streamlit.components.v1"],
        "html",
        lambda *a, **k: called.append(True),
    )
    erp._render_session_restore_cookie(token="signed-token")
    assert called == []


def test_session_ttl_constants_documented():
    assert erp._SESSION_TTL_HOURS == 8
    assert erp._RESTORE_TOKEN_TTL_HOURS == 8
    assert erp._RESTORE_COOKIE == "erp_session_restore"
    assert erp._RESTORE_SECRET_ENV == "ERP_SESSION_RESTORE_SECRET"
