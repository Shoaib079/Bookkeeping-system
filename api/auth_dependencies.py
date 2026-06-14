"""Bearer-token authentication for FastAPI auth routes (P1.3d)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db
from models import User
from services import tokens as token_service

BEARER_MISSING_CODE = "missing_bearer_token"
BEARER_MISSING_MESSAGE = "Bearer token required."
BEARER_INVALID_CODE = "invalid_bearer_token"
BEARER_INVALID_MESSAGE = "Invalid or expired bearer token."

BEARER_MISSING_DETAIL = {"code": BEARER_MISSING_CODE, "message": BEARER_MISSING_MESSAGE}
BEARER_INVALID_DETAIL = {"code": BEARER_INVALID_CODE, "message": BEARER_INVALID_MESSAGE}


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        return None
    return credentials.strip()


def get_bearer_user(
    session: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Resolve the active user from ``Authorization: Bearer <token>``."""
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail=BEARER_MISSING_DETAIL)

    try:
        return token_service.verify_access_token(token, session)
    except token_service.AuthError as exc:
        raise HTTPException(status_code=401, detail=BEARER_INVALID_DETAIL) from exc
