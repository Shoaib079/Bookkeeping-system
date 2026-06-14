"""FASTAPI-P1.3b — JWT access token issue/verify scaffolding (no endpoints yet)."""

from __future__ import annotations

import datetime
import os
import uuid
from typing import Any

import jwt
from sqlalchemy.orm import Session

from models import User
from services.auth import password_hash_fragment

JWT_SECRET_ENV = "ERP_JWT_SECRET"
DEFAULT_ACCESS_TTL_SECONDS = 30 * 60
JWT_ALGORITHM = "HS256"

_FORBIDDEN_CLAIMS = frozenset(
    {
        "role",
        "permissions",
        "active_company_id",
        "company_id",
        "membership_role",
    }
)


class AuthError(Exception):
    """Authentication failed (invalid, expired, or revoked token)."""


def jwt_secret(*, secret: str | bytes | None = None) -> bytes:
    """Resolve HS256 signing secret from argument or ``ERP_JWT_SECRET``."""
    if secret is not None:
        return secret.encode("utf-8") if isinstance(secret, str) else secret
    raw = os.getenv(JWT_SECRET_ENV, "").strip()
    if not raw:
        raise AuthError(f"{JWT_SECRET_ENV} is not configured")
    return raw.encode("utf-8")


def issue_access_token(
    user: User,
    *,
    secret: str | bytes | None = None,
    ttl_seconds: int = DEFAULT_ACCESS_TTL_SECONDS,
    jti: str | None = None,
    token_version: int | None = None,
) -> str:
    """Mint a short-lived identity-only access token."""
    ph_frag = password_hash_fragment(user.password_hash)
    if not ph_frag:
        raise AuthError("Cannot issue token: user has no password hash fragment")

    now = datetime.datetime.now(datetime.timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "iat": now,
        "exp": now + datetime.timedelta(seconds=ttl_seconds),
        "ph_frag": ph_frag,
        "jti": jti or str(uuid.uuid4()),
    }
    if token_version is not None:
        payload["token_version"] = token_version

    for key in _FORBIDDEN_CLAIMS:
        if key in payload:
            raise AuthError(f"Forbidden claim in access token: {key}")

    return jwt.encode(payload, jwt_secret(secret=secret), algorithm=JWT_ALGORITHM)


def _decode_access_token(
    token: str,
    *,
    secret: str | bytes | None = None,
) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            jwt_secret(secret=secret),
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Access token expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid access token") from exc

    for key in _FORBIDDEN_CLAIMS:
        if key in payload:
            raise AuthError(f"Forbidden claim in access token: {key}")
    return payload


def verify_access_token(
    token: str,
    session: Session,
    *,
    secret: str | bytes | None = None,
) -> User:
    """Validate token and return the active user row."""
    payload = _decode_access_token(token, secret=secret)

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthError("Access token missing subject")

    user = session.get(User, int(user_id))
    if user is None or not user.is_active:
        raise AuthError("Inactive or unknown user")

    ph_frag = payload.get("ph_frag")
    if ph_frag != password_hash_fragment(user.password_hash):
        raise AuthError("Access token invalidated by credential change")

    claim_version = payload.get("token_version")
    user_version = getattr(user, "token_version", None)
    if (
        claim_version is not None
        and user_version is not None
        and claim_version != user_version
    ):
        raise AuthError("Access token revoked")

    return user


def access_token_claims(
    token: str,
    *,
    secret: str | bytes | None = None,
) -> dict[str, Any]:
    """Decode and return claims without loading the user (tests/introspection)."""
    return _decode_access_token(token, secret=secret)
