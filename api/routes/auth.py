"""Auth routes — login and bearer identity/company access."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.auth_dependencies import get_bearer_user
from api.dependencies import get_db
from models import User
from services import auth_profile as auth_profile_service
from services import tokens as token_service
from services.login import LoginError, authenticate_user

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., description="Login identifier (username)")
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    is_active: bool
    token_version: int | None = None


class CompanyAccessItem(BaseModel):
    company_id: int
    company_name: str
    role: str
    is_default: bool = False


class CompaniesResponse(BaseModel):
    companies: list[CompanyAccessItem]


@router.post(
    "/login",
    summary="Issue access token",
    description=(
        "Authenticate with username and password. Returns a short-lived "
        "identity-only bearer token. Company and permissions are resolved "
        "per request from the database, not embedded in the token."
    ),
    response_model=LoginResponse,
    responses={
        401: {
            "description": "Invalid credentials (unknown user, wrong password, or inactive user)."
        }
    },
)
def post_login(
    body: LoginRequest,
    session: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    try:
        user = authenticate_user(session, body.username, body.password)
    except LoginError as exc:
        raise HTTPException(
            status_code=401,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    try:
        access_token = token_service.issue_access_token(user)
    except token_service.AuthError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=token_service.DEFAULT_ACCESS_TTL_SECONDS,
    )


@router.get(
    "/me",
    summary="Current user identity",
    description=(
        "Return identity fields for the bearer-authenticated user. "
        "Permissions and company context are not embedded in the token."
    ),
    response_model=MeResponse,
    response_model_exclude_none=True,
    responses={401: {"description": "Missing or invalid bearer token."}},
)
def get_me(
    user: Annotated[User, Depends(get_bearer_user)],
) -> MeResponse:
    return MeResponse(**auth_profile_service.user_identity_dict(user))


@router.get(
    "/companies",
    summary="Accessible companies",
    description=(
        "List companies the current user can access via active membership rows. "
        "``is_default`` reflects the saved last-active company preference when valid."
    ),
    response_model=CompaniesResponse,
    responses={401: {"description": "Missing or invalid bearer token."}},
)
def get_companies(
    user: Annotated[User, Depends(get_bearer_user)],
    session: Annotated[Session, Depends(get_db)],
) -> CompaniesResponse:
    rows = auth_profile_service.list_user_accessible_companies(session, user.id)
    return CompaniesResponse(
        companies=[CompanyAccessItem(**row.to_dict()) for row in rows]
    )
