"""Shared JWT helpers for FastAPI P1 tests (P1.3e+)."""

from __future__ import annotations

from services import auth as auth_service
from services import tokens as token_service

TEST_JWT_SECRET = "p1e-test-jwt-secret-32-bytes-minimum!!"
TEST_USER_PASSWORD = "api-test-pass"
_TEST_PASSWORD_HASH = auth_service.hash_password(TEST_USER_PASSWORD)


def password_hash_for_tests() -> str:
    return _TEST_PASSWORD_HASH


def bearer_token(user) -> str:
    return token_service.issue_access_token(user, secret=TEST_JWT_SECRET)


def api_headers(
    user_or_token,
    *,
    company_id: int | None = None,
    user_id_spoof: int | None = None,
    role_spoof: str | None = None,
) -> dict[str, str]:
    token = user_or_token if isinstance(user_or_token, str) else bearer_token(user_or_token)
    headers = {"Authorization": f"Bearer {token}"}
    if company_id is not None:
        headers["X-Company-Id"] = str(company_id)
    if user_id_spoof is not None:
        headers["X-User-Id"] = str(user_id_spoof)
    if role_spoof is not None:
        headers["X-Role"] = role_spoof
    return headers
