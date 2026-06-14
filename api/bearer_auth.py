"""Bearer token parsing and verification helpers (shared by API dependencies)."""

from __future__ import annotations

BEARER_MISSING_CODE = "missing_bearer_token"
BEARER_MISSING_MESSAGE = "Bearer token required."
BEARER_INVALID_CODE = "invalid_bearer_token"
BEARER_INVALID_MESSAGE = "Invalid or expired bearer token."

BEARER_MISSING_DETAIL = {"code": BEARER_MISSING_CODE, "message": BEARER_MISSING_MESSAGE}
BEARER_INVALID_DETAIL = {"code": BEARER_INVALID_CODE, "message": BEARER_INVALID_MESSAGE}


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        return None
    return credentials.strip()

