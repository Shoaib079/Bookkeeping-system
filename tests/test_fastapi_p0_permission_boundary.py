"""FASTAPI-P0.4a-b — permission boundary contract tests."""

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
from services.context import build_request_context, legacy_permissions_for_role
from services import permissions as perms
from services import user_access as ua

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

_COMPANY_REQUIRED_MSG = (
    "current_company_required(): no active_company_id in session. "
    "This call reached a company-scoped query before Gate 2 was satisfied."
)

_ALL_ACTIONS = sorted(
    set(ua.LEGACY_PERMISSION_MATRIX)
    | set(ua.STAFF_CAPTURE_PERMISSION_MATRIX)
    | {ua.MANAGE_PERMISSIONS_KEY}
)

_MATRIX_ROLES = ("owner", "manager", "cashier", "partner", "staff", "viewer", "accountant")


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
        co_a = models.Company(
            name="Alpha",
            slug="alpha",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        co_b = models.Company(
            name="Beta",
            slug="beta",
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
            username="mgr_p04",
            display_name="Mgr P04",
            password_hash="x",
            role="manager",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add_all([co_a, co_b, owner, manager])
        s.flush()
        s.add_all(
            [
                models.CompanyUser(
                    company_id=co_a.id,
                    user_id=owner.id,
                    role="owner",
                    is_active=True,
                    created_at=datetime.datetime.now(),
                ),
                models.CompanyUser(
                    company_id=co_a.id,
                    user_id=manager.id,
                    role="manager",
                    is_active=True,
                    created_at=datetime.datetime.now(),
                ),
                models.CompanyUser(
                    company_id=co_b.id,
                    user_id=owner.id,
                    role="manager",
                    is_active=True,
                    created_at=datetime.datetime.now(),
                ),
            ]
        )
        s.commit()
        yield s, co_a.id, co_b.id, owner.id, manager.id


def _ctx_for_role(session, co_id, user_id, role, *, fallback_role=None):
    s, *_ = session
    return build_request_context(
        s,
        user_id=user_id,
        company_id=co_id,
        membership_role=role,
        fallback_role=fallback_role or role,
    )


class TestCheckPermission:
    def test_matches_request_context_can(self, session):
        ctx = _ctx_for_role(session, session[1], session[3], "owner")
        for action in _ALL_ACTIONS:
            assert perms.check_permission(ctx, action) == ctx.can(action)

    def test_matches_can_with_company_context(self, session, bind_session_local_to_test):
        s, co_id, _co_b, owner_id, mgr_id = session
        sys.modules["streamlit"].session_state["active_company_id"] = co_id
        sys.modules["streamlit"].session_state["active_company_role"] = "owner"
        ctx = erp_app.build_streamlit_request_context(s)
        assert ctx is not None
        for action in _ALL_ACTIONS:
            assert perms.check_permission(ctx, action) == erp_app._can(action)

        sys.modules["streamlit"].session_state["auth_user"] = {
            **erp_app._DEV_USER,
            "id": mgr_id,
            "role": "manager",
        }
        sys.modules["streamlit"].session_state["active_company_role"] = "manager"
        erp_app._clear_permission_cache()
        ctx_mgr = erp_app.build_streamlit_request_context(s)
        assert ctx_mgr is not None
        for action in _ALL_ACTIONS:
            assert perms.check_permission(ctx_mgr, action) == erp_app._can(action)


class TestRequirePermission:
    def test_allows_when_permitted(self, session):
        ctx = _ctx_for_role(session, session[1], session[3], "owner")
        perms.require_permission(ctx, "manage_settings")

    def test_raises_when_denied(self, session):
        ctx = _ctx_for_role(session, session[1], session[4], "manager")
        with pytest.raises(perms.PermissionDenied, match="manage_users"):
            perms.require_permission(ctx, "manage_users")


class TestRequireCompany:
    def test_returns_company_id(self, session):
        s, co_id, *_ = session
        sys.modules["streamlit"].session_state["active_company_id"] = co_id
        sys.modules["streamlit"].session_state["active_company_role"] = "owner"
        ctx = _ctx_for_role(session, co_id, session[3], "owner")
        assert perms.require_company(ctx) == co_id
        assert perms.require_company(ctx) == erp_app.current_company_required()

    def test_fail_loud_without_company(self, session):
        s, *_ = session
        sys.modules["streamlit"].session_state.pop("active_company_id", None)
        ctx = erp_app.build_streamlit_request_context(s)
        assert ctx is not None
        assert ctx.company_id is None
        with pytest.raises(RuntimeError, match=re.escape(_COMPANY_REQUIRED_MSG)):
            erp_app.current_company_required()
        with pytest.raises(RuntimeError, match=re.escape(_COMPANY_REQUIRED_MSG)):
            perms.require_company(ctx)


class TestRequireCompanyMembership:
    def test_returns_active_membership_role(self, session):
        s, co_id, _co_b, owner_id, mgr_id = session
        ctx = build_request_context(
            s,
            user_id=mgr_id,
            company_id=co_id,
            membership_role="manager",
            fallback_role="manager",
        )
        assert perms.require_company_membership(s, ctx) == "manager"

    def test_rejects_inactive_membership(self, session):
        s, co_id, _co_b, owner_id, mgr_id = session
        inactive = (
            s.query(models.CompanyUser)
            .filter_by(company_id=co_id, user_id=mgr_id)
            .one()
        )
        inactive.is_active = False
        s.commit()
        ctx = build_request_context(
            s,
            user_id=mgr_id,
            company_id=co_id,
            membership_role="manager",
            fallback_role="manager",
        )
        with pytest.raises(RuntimeError, match="not an active member"):
            perms.require_company_membership(s, ctx)

    def test_rejects_wrong_company_membership(self, session):
        s, co_a, co_b, owner_id, _mgr_id = session
        ctx = build_request_context(
            s,
            user_id=owner_id,
            company_id=co_b,
            membership_role="manager",
            fallback_role="owner",
        )
        assert perms.require_company_membership(s, ctx) == "manager"

        outsider = models.User(
            username="outsider",
            display_name="Outsider",
            password_hash="x",
            role="manager",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(outsider)
        s.commit()
        ctx_out = build_request_context(
            s,
            user_id=outsider.id,
            company_id=co_a,
            membership_role="manager",
            fallback_role="manager",
        )
        with pytest.raises(RuntimeError, match="not an active member"):
            perms.require_company_membership(s, ctx_out)

    def test_requires_company_before_membership(self, session):
        s, *_ = session
        ctx = build_request_context(
            s,
            user_id=session[3],
            company_id=None,
            membership_role=None,
            fallback_role="owner",
        )
        with pytest.raises(RuntimeError, match=re.escape(_COMPANY_REQUIRED_MSG)):
            perms.require_company_membership(s, ctx)


class TestGoldenRoleActionMatrix:
    @pytest.mark.parametrize("role", _MATRIX_ROLES)
    def test_role_action_matrix_matches_can(self, session, bind_session_local_to_test, role):
        s, co_id, _co_b, owner_id, _mgr_id = session
        sys.modules["streamlit"].session_state["active_company_id"] = co_id
        sys.modules["streamlit"].session_state["active_company_role"] = role
        sys.modules["streamlit"].session_state["auth_user"] = {
            **erp_app._DEV_USER,
            "role": role,
        }
        erp_app._clear_permission_cache()

        ctx = erp_app.build_streamlit_request_context(s)
        assert ctx is not None
        for action in _ALL_ACTIONS:
            assert perms.check_permission(ctx, action) == erp_app._can(action)


class TestOverridesAndOwnerLocked:
    def test_deny_override_preserved(self, session, bind_session_local_to_test):
        s, co_id, _co_b, owner_id, mgr_id = session
        ua.set_override(s, co_id, mgr_id, "create_transaction", "deny", owner_id)
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
        assert perms.check_permission(ctx, "create_transaction") is False
        assert perms.check_permission(ctx, "create_transaction") == erp_app._can(
            "create_transaction"
        )

    def test_grant_override_preserved(self, session, bind_session_local_to_test):
        s, co_id, _co_b, owner_id, mgr_id = session
        ua.set_override(s, co_id, mgr_id, "manage_budget", "grant", owner_id)
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
        assert perms.check_permission(ctx, "manage_budget") == erp_app._can("manage_budget")
        assert perms.check_permission(ctx, "manage_budget") is True

    def test_owner_locked_grant_ignored(self, session, bind_session_local_to_test):
        s, co_id, _co_b, owner_id, mgr_id = session
        ua.set_override(s, co_id, mgr_id, "manage_users", "grant", owner_id)
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
        assert perms.check_permission(ctx, "manage_users") is False
        assert perms.check_permission(ctx, "manage_users") == erp_app._can("manage_users")


class TestNoCompanyLegacyFallback:
    def test_legacy_fallback_matches_can(self, session, bind_session_local_to_test):
        s, *_ = session
        sys.modules["streamlit"].session_state.pop("active_company_id", None)
        sys.modules["streamlit"].session_state.pop("active_company_role", None)
        erp_app._clear_permission_cache()

        ctx = erp_app.build_streamlit_request_context(s)
        assert ctx is not None
        assert ctx.company_id is None
        assert ctx.effective_permissions == legacy_permissions_for_role("owner")
        for action in _ALL_ACTIONS:
            assert perms.check_permission(ctx, action) == erp_app._can(action)


class TestModulePurity:
    def test_permissions_module_has_no_streamlit_or_app(self):
        import inspect

        src = inspect.getsource(perms)
        assert "streamlit" not in src
        assert "import app" not in src
        assert "from app" not in src


class TestCanConvergence:
    def test_can_delegates_to_check_permission(self):
        import inspect

        src = inspect.getsource(erp_app._can)
        assert "check_permission" in src
        assert "build_streamlit_request_context" in src

    def test_can_matches_boundary_for_all_actions(self, session, bind_session_local_to_test):
        s, co_id, _co_b, owner_id, mgr_id = session
        sys.modules["streamlit"].session_state["active_company_id"] = co_id
        sys.modules["streamlit"].session_state["active_company_role"] = "manager"
        sys.modules["streamlit"].session_state["auth_user"] = {
            **erp_app._DEV_USER,
            "id": mgr_id,
            "role": "manager",
        }
        erp_app._clear_permission_cache()
        ctx = erp_app.build_streamlit_request_context(s)
        assert ctx is not None
        for action in _ALL_ACTIONS:
            assert erp_app._can(action) == perms.check_permission(ctx, action)


class TestTeamRosterVisibility:
    def test_company_settings_uses_manage_users_not_require_role(self):
        import inspect

        src = inspect.getsource(erp_app.render_company_settings)
        assert '_can("manage_users")' in src
        assert "render_member_roster_summary" in src
        assert "_require_role" not in src

    def test_require_role_retired_from_app(self):
        import inspect

        app_src = inspect.getsource(erp_app)
        assert "def _require_role" not in app_src

    def test_owner_sees_team_roster_permission(self, session, bind_session_local_to_test):
        s, co_id, _co_b, owner_id, _mgr_id = session
        sys.modules["streamlit"].session_state["active_company_id"] = co_id
        sys.modules["streamlit"].session_state["active_company_role"] = "owner"
        assert erp_app._can("manage_users") is True

    def test_non_owner_hidden_from_team_roster_permission(
        self, session, bind_session_local_to_test
    ):
        s, co_id, _co_b, _owner_id, mgr_id = session
        sys.modules["streamlit"].session_state["auth_user"] = {
            **erp_app._DEV_USER,
            "id": mgr_id,
            "role": "manager",
        }
        sys.modules["streamlit"].session_state["active_company_id"] = co_id
        sys.modules["streamlit"].session_state["active_company_role"] = "manager"
        erp_app._clear_permission_cache()
        assert erp_app._can("manage_users") is False

    def test_manage_users_grant_override_still_owner_locked(
        self, session, bind_session_local_to_test
    ):
        s, co_id, _co_b, owner_id, mgr_id = session
        ua.set_override(s, co_id, mgr_id, "manage_users", "grant", owner_id)
        s.commit()
        erp_app._clear_permission_cache()
        sys.modules["streamlit"].session_state["auth_user"] = {
            **erp_app._DEV_USER,
            "id": mgr_id,
            "role": "manager",
        }
        sys.modules["streamlit"].session_state["active_company_id"] = co_id
        sys.modules["streamlit"].session_state["active_company_role"] = "manager"
        assert erp_app._can("manage_users") is False

