"""Bearer-token authentication for FastAPI auth routes (P1.3d)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from api.bearer_auth import BEARER_INVALID_DETAIL, BEARER_MISSING_DETAIL, extract_bearer_token
from api.dependencies import get_db
from models import User
from services import tokens as token_service


def get_bearer_user(
    session: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Resolve the active user from ``Authorization: Bearer <token>``."""
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail=BEARER_MISSING_DETAIL)
    try:
        return token_service.verify_access_token(token, session)
    except token_service.AuthError as exc:
        raise HTTPException(status_code=401, detail=BEARER_INVALID_DETAIL) from exc
