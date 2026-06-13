"""FASTAPI-P0.1 — RequestContext foundation contract tests."""

from __future__ import annotations

import datetime
import re
import sys
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

import app as erp_app
from db import Base
import models
from services.context import RequestContext, build_request_context, legacy_permissions_for_role
from services import user_access as ua

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True


@pytest.fixture(autouse=True)
def _restore_dev_mode_after_test():
    """Isolate DEV_MODE from other modules that mutate it during the full suite."""
    prev_dev = erp_app.DEV_MODE
    prev_legacy = erp_app.DEVELOPMENT_MODE
    erp_app.DEV_MODE = True
    erp_app.DEVELOPMENT_MODE = True
    yield
    erp_app.DEV_MODE = prev_dev
    erp_app.DEVELOPMENT_MODE = prev_legacy


_COMPANY_REQUIRED_MSG = (
    "current_company_required(): no active_company_id in session. "
    "This call reached a company-scoped query before Gate 2 was satisfied."
)

_SAMPLE_ACTIONS = (
    "create_transaction",
    "edit_transaction",
    "void_transaction",
    "manage_settings",
    "view_reconciliation",
)


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    _seed_dev_auth_user()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def bind_session_local_to_test(session):
    """Route app._can through the in-memory test DB (matches builder session)."""
    s, *_ = session
    with patch.object(erp_app, "SessionLocal", return_value=s):
        with patch.object(s, "close", lambda: None):
            yield


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        co = models.Company(
            name="P0 Context Co",
            slug="p0_context_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        owner = models.User(
            id=erp_app._DEV_USER["id"],
            username=erp_app._DEV_USER["username"],
            display_name=erp_app._DEV_USER["display_name"],
            password_hash="x",
            role=erp_app._DEV_USER["role"],
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        manager = models.User(
            username="mgr_ctx",
            display_name="Mgr Ctx",
            password_hash="x",
            role="manager",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add_all([co, owner, manager])
        s.flush()
        s.add(
            models.CompanyUser(
                company_id=co.id,
                user_id=owner.id,
                role="owner",
                is_active=True,
                created_at=datetime.datetime.now(),
            )
        )
        s.add(
            models.CompanyUser(
                company_id=co.id,
                user_id=manager.id,
                role="manager",
                is_active=True,
                created_at=datetime.datetime.now(),
            )
        )
        s.commit()
        yield s, co.id, owner.id, manager.id


def test_request_context_is_frozen():
    ctx = RequestContext(
        user_id=1,
        company_id=2,
        role="owner",
        effective_permissions=frozenset({"a"}),
    )
    with pytest.raises(AttributeError):
        ctx.user_id = 3  # type: ignore[misc]


def test_build_streamlit_returns_none_without_user():
    sys.modules["streamlit"].session_state.clear()
    sess = MagicMock()
    assert erp_app.build_streamlit_request_context(sess) is None


def test_context_matches_ambient_helpers_with_company(session):
    s, co_id, owner_id, _mgr_id = session
    sys.modules["streamlit"].session_state["active_company_id"] = co_id
    sys.modules["streamlit"].session_state["active_company_role"] = "owner"

    ctx = erp_app.build_streamlit_request_context(s)
    assert ctx is not None
    assert ctx.user_id == erp_app._current_user()["id"]
    assert ctx.company_id == erp_app._current_company_id()
    assert ctx.role == erp_app._current_company_role() or erp_app._current_user()["role"]
    assert ctx.company_id == erp_app.current_company_required()


def test_permissions_match_can_with_company_context(session, bind_session_local_to_test):
    s, co_id, owner_id, mgr_id = session
    sys.modules["streamlit"].session_state["active_company_id"] = co_id
    sys.modules["streamlit"].session_state["active_company_role"] = "owner"

    ctx = erp_app.build_streamlit_request_context(s)
    assert ctx is not None
    for action in _SAMPLE_ACTIONS:
        assert ctx.can(action) == erp_app._can(action)

    sys.modules["streamlit"].session_state["auth_user"] = {
        **erp_app._DEV_USER,
        "id": mgr_id,
        "role": "manager",
    }
    sys.modules["streamlit"].session_state["active_company_role"] = "manager"
    erp_app._clear_permission_cache()

    ctx_mgr = erp_app.build_streamlit_request_context(s)
    assert ctx_mgr is not None
    for action in _SAMPLE_ACTIONS:
        assert ctx_mgr.can(action) == erp_app._can(action)


def test_effective_permissions_match_user_access_service(session):
    s, co_id, owner_id, _mgr_id = session
    view = ua.effective_permissions(s, co_id, owner_id, membership_role="owner")
    ctx = build_request_context(
        s,
        user_id=owner_id,
        company_id=co_id,
        membership_role="owner",
        fallback_role="owner",
    )
    assert ctx.effective_permissions == view.effective_keys


def test_legacy_fallback_without_company_matches_can(session, bind_session_local_to_test):
    s, _co_id, owner_id, _mgr_id = session
    sys.modules["streamlit"].session_state.pop("active_company_id", None)
    sys.modules["streamlit"].session_state.pop("active_company_role", None)
    erp_app._clear_permission_cache()

    ctx = erp_app.build_streamlit_request_context(s)
    assert ctx is not None
    assert ctx.company_id is None
    assert ctx.effective_permissions == legacy_permissions_for_role("owner")
    for action in _SAMPLE_ACTIONS:
        assert ctx.can(action) == erp_app._can(action)


def test_require_company_id_matches_current_company_required(session):
    s, co_id, _owner_id, _mgr_id = session
    sys.modules["streamlit"].session_state["active_company_id"] = co_id
    sys.modules["streamlit"].session_state["active_company_role"] = "owner"

    ctx = erp_app.build_streamlit_request_context(s)
    assert ctx is not None
    assert ctx.require_company_id() == erp_app.current_company_required()

    sys.modules["streamlit"].session_state.pop("active_company_id", None)
    ctx_none = erp_app.build_streamlit_request_context(s)
    assert ctx_none is not None
    assert ctx_none.company_id is None

    with pytest.raises(RuntimeError, match=re.escape(_COMPANY_REQUIRED_MSG)):
        erp_app.current_company_required()
    with pytest.raises(RuntimeError, match=re.escape(_COMPANY_REQUIRED_MSG)):
        ctx_none.require_company_id()


def test_dev_mode_auth_user_preserved_in_context(session):
    s, co_id, owner_id, _mgr_id = session
    sys.modules["streamlit"].session_state["active_company_id"] = co_id
    sys.modules["streamlit"].session_state["active_company_role"] = "owner"

    assert erp_app.DEV_MODE is True
    u = erp_app._current_user()
    assert u is not None
    assert u["username"] == erp_app._DEV_USERNAME

    ctx = erp_app.build_streamlit_request_context(s)
    assert ctx is not None
    assert ctx.user_id == owner_id
    assert ctx.user_id == u["id"]


def test_permission_override_reflected_in_context_and_can(session, bind_session_local_to_test):
    s, co_id, owner_id, mgr_id = session
    ua.set_override(
        s,
        co_id,
        mgr_id,
        "create_transaction",
        "deny",
        owner_id,
    )
    s.commit()
    erp_app._clear_permission_cache()

    sys.modules["streamlit"].session_state["auth_user"] = {
        **erp_app._DEV_USER,
        "id": mgr_id,
        "role": "manager",
    }
    sys.modules["streamlit"].session_state["active_company_id"] = co_id
    sys.modules["streamlit"].session_state["active_company_role"] = "manager"

    ctx = erp_app.build_streamlit_request_context(s)
    assert ctx is not None
    assert ctx.can("create_transaction") == erp_app._can("create_transaction")
    assert ctx.can("create_transaction") is False
