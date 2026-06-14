"""FastAPI dependencies — DB session and dev/test request context."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from api.errors import AUTH_MISSING_DETAIL
from db import SessionLocal
from models import CompanyUser, User
from services.context import RequestContext, build_request_context


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped SQLAlchemy session; close without committing."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_request_context(
    session: Annotated[Session, Depends(get_db)],
    x_user_id: Annotated[int | None, Header(alias="X-User-Id")] = None,
    x_company_id: Annotated[int | None, Header(alias="X-Company-Id")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
) -> RequestContext:
    """Build RequestContext from dev/test headers (no JWT yet)."""
    if x_user_id is None:
        raise HTTPException(status_code=401, detail=AUTH_MISSING_DETAIL)

    user = session.get(User, x_user_id)
    fallback_role = user.role if user is not None else None

    membership_role = x_role
    if membership_role is None and x_company_id is not None:
        row = (
            session.query(CompanyUser.role)
            .filter(
                CompanyUser.company_id == x_company_id,
                CompanyUser.user_id == x_user_id,
                CompanyUser.is_active.is_(True),
            )
            .first()
        )
        membership_role = row[0] if row else None

    return build_request_context(
        session,
        user_id=x_user_id,
        company_id=x_company_id,
        membership_role=membership_role,
        fallback_role=fallback_role,
    )
