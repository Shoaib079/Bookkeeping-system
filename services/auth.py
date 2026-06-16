"""Shared password hashing — PBKDF2-HMAC-SHA256 (Streamlit + FastAPI)."""

from __future__ import annotations

import hashlib
import logging
import secrets

_PBKDF2_ITERATIONS = 260_000
_log = logging.getLogger(__name__)


def password_hash_fragment(password_hash: str) -> str:
    """Short fragment of stored hash — invalidates tokens on password change."""
    try:
        _salt, key_hex = password_hash.split(":", 1)
        return key_hex[:16]
    except (ValueError, AttributeError):
        _log.debug("password_hash_fragment: malformed hash input")
        return ""


def hash_password(password: str) -> str:
    """Return a salted PBKDF2-SHA256 hash of *password*."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
    )
    return f"{salt}:{key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Return True if *password* matches *stored_hash*."""
    try:
        salt, key_hex = stored_hash.split(":", 1)
        key = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), _PBKDF2_ITERATIONS
        )
        return secrets.compare_digest(key.hex(), key_hex)
    except (ValueError, AttributeError, TypeError):
        _log.debug("verify_password: malformed stored hash")
        return False
