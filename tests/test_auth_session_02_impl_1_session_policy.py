"""AUTH-SESSION-02-IMPL-1 — session policy service tests."""

from __future__ import annotations

import ast
import datetime
from pathlib import Path

import pytest

from services import session_policy as sp

_HOUR = 3600
_DAY = 24 * _HOUR


def _now() -> datetime.datetime:
    return datetime.datetime(2026, 6, 15, 12, 0, 0)


class TestBuildSessionPolicy:
    def test_browser_session_defaults(self):
        policy = sp.build_session_policy(sp.MODE_BROWSER_SESSION)
        assert policy.mode == "browser_session"
        assert policy.idle_ttl_seconds == 8 * _HOUR
        assert policy.absolute_ttl_seconds == 8 * _HOUR
        assert policy.should_remember_device is False
        assert policy.cookie_ttl_seconds == 8 * _HOUR

    def test_remember_device_defaults(self):
        policy = sp.build_session_policy(sp.MODE_REMEMBER_DEVICE)
        assert policy.mode == "remember_device"
        assert policy.idle_ttl_seconds == 8 * _HOUR
        assert policy.absolute_ttl_seconds == 30 * _DAY
        assert policy.should_remember_device is True
        assert policy.cookie_ttl_seconds == 30 * _DAY

    def test_remember_cookie_ttl_longer_than_browser(self):
        browser = sp.build_session_policy(sp.MODE_BROWSER_SESSION)
        remember = sp.build_session_policy(sp.MODE_REMEMBER_DEVICE)
        assert remember.cookie_ttl_seconds > browser.cookie_ttl_seconds

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match="Unknown session mode"):
            sp.build_session_policy("invalid")  # type: ignore[arg-type]


class TestExpiryHelpers:
    def test_compute_session_expiry_idle_window(self):
        now = _now()
        policy = sp.build_session_policy(sp.MODE_BROWSER_SESSION)
        expiry = sp.compute_session_expiry(now, policy)
        assert expiry == now + datetime.timedelta(hours=8)

    def test_absolute_cap_enforced_for_remember_device(self):
        now = _now()
        started = now - datetime.timedelta(days=29, hours=20)
        policy = sp.build_session_policy(sp.MODE_REMEMBER_DEVICE)
        expiry = sp.compute_session_expiry(now, policy, session_started_at=started)
        absolute = sp.compute_absolute_expiry(started, policy)
        assert expiry == absolute
        assert expiry < now + datetime.timedelta(hours=8)

    def test_clamp_to_absolute_expiry(self):
        idle = _now() + datetime.timedelta(hours=8)
        absolute = _now() + datetime.timedelta(hours=2)
        assert sp.clamp_to_absolute_expiry(idle, absolute) == absolute

    def test_should_extend_idle_when_active_and_under_cap(self):
        now = _now()
        started = now - datetime.timedelta(hours=1)
        policy = sp.build_session_policy(sp.MODE_REMEMBER_DEVICE)
        current = now + datetime.timedelta(hours=2)
        assert sp.should_extend_idle(
            now, current, policy, session_started_at=started
        )

    def test_should_not_extend_idle_when_expired(self):
        now = _now()
        started = now - datetime.timedelta(hours=1)
        policy = sp.build_session_policy(sp.MODE_BROWSER_SESSION)
        current = now - datetime.timedelta(minutes=1)
        assert not sp.should_extend_idle(
            now, current, policy, session_started_at=started
        )

    def test_should_not_extend_idle_past_absolute_cap(self):
        now = _now()
        started = now - datetime.timedelta(days=30)
        policy = sp.build_session_policy(sp.MODE_REMEMBER_DEVICE)
        current = now + datetime.timedelta(hours=1)
        assert not sp.should_extend_idle(
            now, current, policy, session_started_at=started
        )


class TestSerialization:
    def test_round_trip_dict(self):
        policy = sp.build_session_policy(sp.MODE_REMEMBER_DEVICE)
        restored = sp.session_policy_from_dict(sp.session_policy_to_dict(policy))
        assert restored == policy


class TestPurity:
    def test_no_streamlit_imports(self):
        src = Path(__file__).resolve().parents[1].joinpath(
            "services", "session_policy.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(src)
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    roots.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        assert "streamlit" not in roots

    def test_app_imports_session_policy(self):
        app_src = Path(__file__).resolve().parents[1].joinpath("app.py").read_text(
            encoding="utf-8"
        )
        assert "from services.session_policy import" in app_src
        assert "build_session_policy" in app_src
        assert "compute_session_expiry" in app_src
