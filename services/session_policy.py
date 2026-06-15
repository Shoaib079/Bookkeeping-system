"""AUTH-SESSION-02-IMPL-1 — pure session policy (browser vs remember-device).

Defines idle vs absolute TTLs for live session expiry and restore-cookie max-age.
**Not wired** to ``app.py`` auth yet — policy-only seam for Streamlit + FastAPI.

No Streamlit, no cookie/token format change, no schema change.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Literal

SessionMode = Literal["browser_session", "remember_device"]

MODE_BROWSER_SESSION: SessionMode = "browser_session"
MODE_REMEMBER_DEVICE: SessionMode = "remember_device"

_HOUR = 3600
_DAY = 24 * _HOUR

DEFAULT_IDLE_TTL_SECONDS = 8 * _HOUR
DEFAULT_BROWSER_ABSOLUTE_TTL_SECONDS = 8 * _HOUR
DEFAULT_REMEMBER_ABSOLUTE_TTL_SECONDS = 30 * _DAY


@dataclass(frozen=True)
class SessionPolicy:
    """TTL policy for a login session."""

    mode: SessionMode
    idle_ttl_seconds: int
    absolute_ttl_seconds: int
    should_remember_device: bool
    cookie_ttl_seconds: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "idle_ttl_seconds": self.idle_ttl_seconds,
            "absolute_ttl_seconds": self.absolute_ttl_seconds,
            "should_remember_device": self.should_remember_device,
            "cookie_ttl_seconds": self.cookie_ttl_seconds,
        }


def build_session_policy(mode: SessionMode) -> SessionPolicy:
    """Return the canonical policy for *mode*."""
    if mode == MODE_BROWSER_SESSION:
        return SessionPolicy(
            mode=mode,
            idle_ttl_seconds=DEFAULT_IDLE_TTL_SECONDS,
            absolute_ttl_seconds=DEFAULT_BROWSER_ABSOLUTE_TTL_SECONDS,
            should_remember_device=False,
            cookie_ttl_seconds=DEFAULT_IDLE_TTL_SECONDS,
        )
    if mode == MODE_REMEMBER_DEVICE:
        return SessionPolicy(
            mode=mode,
            idle_ttl_seconds=DEFAULT_IDLE_TTL_SECONDS,
            absolute_ttl_seconds=DEFAULT_REMEMBER_ABSOLUTE_TTL_SECONDS,
            should_remember_device=True,
            cookie_ttl_seconds=DEFAULT_REMEMBER_ABSOLUTE_TTL_SECONDS,
        )
    raise ValueError(f"Unknown session mode: {mode!r}")


def compute_absolute_expiry(
    session_started_at: datetime.datetime,
    policy: SessionPolicy,
) -> datetime.datetime:
    """Hard cap: first authentication time + absolute TTL."""
    return session_started_at + datetime.timedelta(seconds=policy.absolute_ttl_seconds)


def clamp_to_absolute_expiry(
    idle_expiry: datetime.datetime,
    absolute_expiry: datetime.datetime,
) -> datetime.datetime:
    """Return the earlier of idle-based and absolute-based expiry."""
    return idle_expiry if idle_expiry <= absolute_expiry else absolute_expiry


def compute_session_expiry(
    now: datetime.datetime,
    policy: SessionPolicy,
    *,
    session_started_at: datetime.datetime | None = None,
) -> datetime.datetime:
    """Compute live session expiry at *now* (idle window capped by absolute)."""
    started = session_started_at or now
    idle_expiry = now + datetime.timedelta(seconds=policy.idle_ttl_seconds)
    absolute_expiry = compute_absolute_expiry(started, policy)
    return clamp_to_absolute_expiry(idle_expiry, absolute_expiry)


def should_extend_idle(
    now: datetime.datetime,
    current_expiry: datetime.datetime,
    policy: SessionPolicy,
    *,
    session_started_at: datetime.datetime,
) -> bool:
    """True when activity may extend idle expiry (session active, under absolute cap)."""
    if now >= current_expiry:
        return False
    absolute_expiry = compute_absolute_expiry(session_started_at, policy)
    return now < absolute_expiry


def session_policy_from_dict(data: dict[str, Any]) -> SessionPolicy:
    """Deserialize a :class:`SessionPolicy` (API/config seam)."""
    return SessionPolicy(
        mode=data["mode"],
        idle_ttl_seconds=int(data["idle_ttl_seconds"]),
        absolute_ttl_seconds=int(data["absolute_ttl_seconds"]),
        should_remember_device=bool(data["should_remember_device"]),
        cookie_ttl_seconds=int(data["cookie_ttl_seconds"]),
    )


def session_policy_to_dict(policy: SessionPolicy) -> dict[str, Any]:
    """Serialize a :class:`SessionPolicy`."""
    return policy.to_dict()
