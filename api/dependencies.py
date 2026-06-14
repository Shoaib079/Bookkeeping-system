"""FastAPI dependencies — DB session and request context (JWT + company header)."""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from api.bearer_auth import (
    BEARER_INVALID_DETAIL,
    BEARER_MISSING_DETAIL,
    extract_bearer_token,
)
from api.errors import AUTH_MISSING_DETAIL
from db import SessionLocal
from models import Company, CompanyUser, User
from services import tokens as token_service
from services.context import RequestContext, build_request_context

DEV_HEADERS_ENV = "ERP_API_DEV_HEADERS"


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped SQLAlchemy session; close without committing."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _dev_headers_enabled() -> bool:
    return os.getenv(DEV_HEADERS_ENV, "").strip().lower() in ("1", "true", "yes")


def _membership_role_from_db(
    session: Session,
    *,
    company_id: int,
    user_id: int,
) -> str | None:
    row = (
        session.query(CompanyUser.role)
        .filter(
            CompanyUser.company_id == company_id,
            CompanyUser.user_id == user_id,
            CompanyUser.is_active.is_(True),
        )
        .first()
    )
    return row[0] if row else None


def _resolve_identity(
    session: Session,
    *,
    authorization: str | None,
    x_user_id: int | None,
    x_role: str | None,
    x_company_id: int | None,
) -> tuple[int, str | None]:
    """Return ``(user_id, fallback_role)`` from JWT or optional dev headers."""
    token = extract_bearer_token(authorization)
    if token is not None:
        try:
            user = token_service.verify_access_token(token, session)
        except token_service.AuthError as exc:
            raise HTTPException(status_code=401, detail=BEARER_INVALID_DETAIL) from exc
        return user.id, user.role

    if _dev_headers_enabled() and x_user_id is not None:
        user = session.get(User, x_user_id)
        fallback_role = user.role if user is not None else None
        return x_user_id, fallback_role

    raise HTTPException(status_code=401, detail=BEARER_MISSING_DETAIL)


def get_request_context(
    session: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    x_company_id: Annotated[int | None, Header(alias="X-Company-Id")] = None,
    x_user_id: Annotated[int | None, Header(alias="X-User-Id")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
) -> RequestContext:
    """Build RequestContext from bearer JWT identity and ``X-Company-Id``.

    ``X-User-Id`` and ``X-Role`` are ignored unless ``ERP_API_DEV_HEADERS`` is enabled
    and no bearer token is supplied (test/dev fallback only).
    """
    user_id, fallback_role = _resolve_identity(
        session,
        authorization=authorization,
        x_user_id=x_user_id,
        x_role=x_role,
        x_company_id=x_company_id,
    )

    membership_role: str | None = None
    if x_company_id is not None:
        company = session.get(Company, x_company_id)
        if company is None or not company.is_active:
            membership_role = None
        else:
            membership_role = _membership_role_from_db(
                session,
                company_id=x_company_id,
                user_id=user_id,
            )
    elif _dev_headers_enabled() and x_role is not None:
        membership_role = x_role

    return build_request_context(
        session,
        user_id=user_id,
        company_id=x_company_id,
        membership_role=membership_role,
        fallback_role=fallback_role,
    )


def get_request_context_dev_headers(
    session: Annotated[Session, Depends(get_db)],
    x_user_id: Annotated[int | None, Header(alias="X-User-Id")] = None,
    x_company_id: Annotated[int | None, Header(alias="X-Company-Id")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
) -> RequestContext:
    """Legacy dev-header context (explicit tests only)."""
    if x_user_id is None:
        raise HTTPException(status_code=401, detail=AUTH_MISSING_DETAIL)

    user = session.get(User, x_user_id)
    fallback_role = user.role if user is not None else None

    membership_role = x_role
    if membership_role is None and x_company_id is not None:
        membership_role = _membership_role_from_db(
            session,
            company_id=x_company_id,
            user_id=x_user_id,
        )

    return build_request_context(
        session,
        user_id=x_user_id,
        company_id=x_company_id,
        membership_role=membership_role,
        fallback_role=fallback_role,
    )
