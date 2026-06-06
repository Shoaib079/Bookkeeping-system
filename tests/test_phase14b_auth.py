"""Tests for Phase 14B — Auth Flow + Active Company Context.

Uses an isolated in-memory SQLite database — no production data is read or written.

Verification checklist:
 1.  Single-company user is auto-selected after login (no picker shown)
 2.  Multi-company user leaves active_company_id unset (picker required)
 3.  User with no active membership can log in (company picker + create)
 4.  User with inactive-only membership can log in (picker; no active company)
 5.  User whose only company is inactive can log in (picker; no active company)
 6.  active_company_role reflects CompanyUser.role, not User.role
 7.  _can() uses active_company_role (viewer cannot do owner actions)
 8.  _can() uses active_company_role (owner via CompanyUser beats viewer User.role)
 9.  _can() falls back to User.role when active_company_role absent (stale session)
10.  Inactive membership is excluded from auto-select count
11.  _logout() clears all auth + company context keys
12.  _execute_company_switch() clears company context, preserves auth identity
13.  _validate_company_membership() returns True for a valid live membership
14.  _validate_company_membership() returns False when active_company_id absent
15.  _validate_company_membership() catches mid-session membership deactivation
"""

import sys
import datetime
from unittest.mock import MagicMock, patch

# ── Streamlit mock — must happen before importing app ────────────────────────
# We need st.session_state to behave like a real dict so auth functions can
# read and write values normally. The MagicMock handles all other st.* calls.
if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock
else:
    _st_mock = sys.modules["streamlit"]
    if not isinstance(getattr(_st_mock, "session_state", None), dict):
        _st_mock.session_state = {}

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app

# Real auth flow must be active for these tests
app.DEVELOPMENT_MODE = False


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_session():
    """Wipe session_state before and after every test."""
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def db():
    """Fresh in-memory SQLite per test."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


# ─── Seed helpers ────────────────────────────────────────────────────────────

def _user(db, username="alice", role="owner"):
    u = models.User(
        username=username,
        display_name=username.title(),
        password_hash=app._hash_password("pw"),
        role=role,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(u)
    db.flush()
    return u


def _company(db, name="Acme", slug="co1", is_active=True):
    c = models.Company(
        name=name,
        slug=slug,
        is_active=is_active,
        created_at=datetime.datetime.now(),
    )
    db.add(c)
    db.flush()
    return c


def _membership(db, user, company, role="owner", is_active=True):
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


def _ss():
    """Return current session_state dict."""
    return sys.modules["streamlit"].session_state


# ─── 1–2. Auto-select vs picker required ─────────────────────────────────────

class TestSingleCompanyAutoSelect:
    def test_auto_selects_company_id_role_and_name(self, db):
        u = _user(db, "alice", role="owner")
        co = _company(db, "Acme Corp", "acme")
        _membership(db, u, co, role="owner")

        err = app._login(db, "alice", "pw")

        assert err is None
        ss = _ss()
        assert ss["active_company_id"]   == co.id
        assert ss["active_company_role"] == "owner"
        assert ss["active_company_name"] == "Acme Corp"
        assert ss["active_company_membership_count"] == 1

    def test_auth_user_also_set(self, db):
        u = _user(db, "bob")
        co = _company(db)
        _membership(db, u, co)

        app._login(db, "bob", "pw")

        assert "auth_user" in _ss()
        assert "auth_expires" in _ss()


class TestMultiCompanyPickerRequired:
    def test_active_company_id_absent_for_multi_company(self, db):
        u = _user(db, "carl")
        co1 = _company(db, "Alpha", "alpha")
        co2 = _company(db, "Beta",  "beta")
        _membership(db, u, co1, role="owner")
        _membership(db, u, co2, role="viewer")

        err = app._login(db, "carl", "pw")

        assert err is None
        ss = _ss()
        assert "active_company_id" not in ss
        assert ss["active_company_membership_count"] == 2
        assert "auth_user" in ss  # auth identity is set


# ─── 3–5. No active company → picker (create allowed) ─────────────────────────

class TestNoActiveCompanyAfterLogin:
    def test_user_with_zero_memberships_can_login(self, db):
        _user(db, "dana")  # no CompanyUser rows

        err = app._login(db, "dana", "pw")

        assert err is None
        ss = _ss()
        assert "auth_user" in ss
        assert "active_company_id" not in ss
        assert ss["active_company_membership_count"] == 0

    def test_inactive_membership_only_can_login_without_active_company(self, db):
        u = _user(db, "evan")
        co = _company(db)
        _membership(db, u, co, is_active=False)

        err = app._login(db, "evan", "pw")

        assert err is None
        ss = _ss()
        assert "auth_user" in ss
        assert "active_company_id" not in ss
        assert ss["active_company_membership_count"] == 0

    def test_inactive_company_only_can_login_without_active_company(self, db):
        u = _user(db, "faye")
        co = _company(db, is_active=False)
        _membership(db, u, co, is_active=True)

        err = app._login(db, "faye", "pw")

        assert err is None
        ss = _ss()
        assert "auth_user" in ss
        assert "active_company_id" not in ss
        assert ss["active_company_membership_count"] == 0


# ─── 6. Role differs per company ─────────────────────────────────────────────

class TestRoleDiffersPerCompany:
    def test_company_role_overrides_user_role(self, db):
        """CompanyUser.role='viewer' wins over User.role='owner'."""
        u = _user(db, "gina", role="owner")
        co = _company(db)
        _membership(db, u, co, role="viewer")

        app._login(db, "gina", "pw")

        assert _ss()["active_company_role"] == "viewer"


# ─── 7–9. _can() role source ─────────────────────────────────────────────────

class TestCanUsesCompanyRole:
    def test_viewer_company_role_blocks_owner_action(self, db):
        u = _user(db, "hal", role="owner")   # User.role=owner
        co = _company(db)
        _membership(db, u, co, role="viewer")  # CompanyUser.role=viewer

        app._login(db, "hal", "pw")

        assert app._can("perform_year_end_close") is False
        assert app._can("manage_settings")        is False
        assert app._can("manage_users")           is False

    def test_owner_company_role_grants_owner_action(self, db):
        u = _user(db, "iris", role="viewer")   # User.role=viewer
        co = _company(db)
        _membership(db, u, co, role="owner")   # CompanyUser.role=owner

        app._login(db, "iris", "pw")

        assert app._can("perform_year_end_close") is True
        assert app._can("manage_settings")        is True

    def test_fallback_to_user_role_when_company_role_absent(self):
        """Stale session: active_company_role absent → _can() falls back to User.role."""
        ss = _ss()
        ss["auth_user"] = {
            "id": 999, "username": "stale", "display_name": "Stale",
            "role": "owner",
            "email": "", "phone": "", "last_login": None, "created_at": None,
        }
        ss["auth_expires"] = datetime.datetime.now() + datetime.timedelta(hours=4)
        # active_company_role intentionally absent

        assert app._can("perform_year_end_close") is True   # owner via fallback
        assert app._current_company_role() is None          # confirmed absent


# ─── 10. Inactive membership excluded from count ─────────────────────────────

class TestInactiveMembershipExcluded:
    def test_inactive_membership_not_counted(self, db):
        """Only active memberships count; one active + one inactive → auto-select."""
        u = _user(db, "jake")
        co_active   = _company(db, "ActiveCo",   "active_co")
        co_inactive = _company(db, "InactiveCo", "inactive_co")
        _membership(db, u, co_active,   role="owner",   is_active=True)
        _membership(db, u, co_inactive, role="manager", is_active=False)

        app._login(db, "jake", "pw")

        ss = _ss()
        assert ss["active_company_id"]             == co_active.id
        assert ss["active_company_membership_count"] == 1


# ─── 11. Sign-out clears all context ─────────────────────────────────────────

class TestSignOutClearsCompanyContext:
    def test_logout_removes_auth_and_company_keys(self, db):
        u = _user(db, "kim")
        co = _company(db)
        _membership(db, u, co)
        app._login(db, "kim", "pw")

        assert "active_company_id" in _ss()

        app._logout()

        ss = _ss()
        assert ss.get("session_logged_out") is True
        for key in ("auth_user", "auth_expires",
                    "active_company_id", "active_company_role",
                    "active_company_name", "active_company_membership_count"):
            assert key not in ss, f"{key} should be cleared by _logout()"


class TestDevModeSignOut:
    def test_logout_in_dev_mode_returns_no_current_user(self, db):
        prev = app.DEVELOPMENT_MODE
        try:
            app.DEVELOPMENT_MODE = True
            ss = _ss()
            ss.clear()
            ss["active_company_id"] = 1
            app._logout()
            assert app._current_user() is None
        finally:
            app.DEVELOPMENT_MODE = prev


# ─── 12. Company switch returns to picker flow ───────────────────────────────

class TestCompanySwitchReturnsToPickerFlow:
    def test_switch_clears_company_and_form_state_but_keeps_auth(self, db):
        u = _user(db, "leo")
        co1 = _company(db, "Corp A", "corp_a")
        co2 = _company(db, "Corp B", "corp_b")
        _membership(db, u, co1, role="owner")
        _membership(db, u, co2, role="viewer")
        app._login(db, "leo", "pw")

        # Manually set company context (simulates multi-company selection)
        ss = _ss()
        ss["active_company_id"]   = co1.id
        ss["active_company_role"] = "owner"
        ss["active_company_name"] = "Corp A"
        # Transient form / nav state that must be cleared on switch
        ss["confirm_void_99"]   = True
        ss["advanced_subpage"]  = "Fiscal Periods"
        ss["paying_sale_5"]     = True

        # st.rerun is already a MagicMock — calling it does nothing
        app._execute_company_switch()

        ss = _ss()
        assert "active_company_id"   not in ss
        assert "active_company_role" not in ss
        assert "active_company_name" not in ss
        assert "confirm_void_99"     not in ss
        assert "advanced_subpage"    not in ss
        assert "paying_sale_5"       not in ss
        # Auth identity must survive the switch
        assert "auth_user" in ss
        assert "auth_expires" in ss
        assert ss["active_company_membership_count"] == 2  # preserved for picker


# ─── 13–15. Membership validation ────────────────────────────────────────────

class TestValidateCompanyMembership:
    def test_valid_live_membership_returns_true(self, db):
        u = _user(db, "mia")
        co = _company(db)
        _membership(db, u, co, role="owner")
        app._login(db, "mia", "pw")

        assert app._validate_company_membership(db) is True

    def test_missing_active_company_id_returns_false(self):
        ss = _ss()
        ss["auth_user"] = {
            "id": 888, "username": "ghost", "display_name": "Ghost",
            "role": "owner",
            "email": "", "phone": "", "last_login": None, "created_at": None,
        }
        ss["auth_expires"] = datetime.datetime.now() + datetime.timedelta(hours=4)
        # active_company_id absent

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        _e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=_e)
        _S = sessionmaker(bind=_e)
        with _S() as _s:
            assert app._validate_company_membership(_s) is False

    def test_deactivated_membership_returns_false(self, db):
        u = _user(db, "ned")
        co = _company(db)
        m = _membership(db, u, co, role="owner")
        app._login(db, "ned", "pw")

        # Simulate mid-session deactivation
        m.is_active = False
        db.commit()

        assert app._validate_company_membership(db) is False
