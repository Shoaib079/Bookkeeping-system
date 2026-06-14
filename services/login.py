"""FASTAPI-P1.3c — credential authentication (API login; no Streamlit session)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import User
from services.auth import verify_password

INVALID_CREDENTIALS_CODE = "invalid_credentials"
INVALID_CREDENTIALS_MESSAGE = "Incorrect username or password."


class LoginError(Exception):
    """Raised when username/password authentication fails."""

    def __init__(
        self,
        code: str = INVALID_CREDENTIALS_CODE,
        message: str = INVALID_CREDENTIALS_MESSAGE,
    ) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def authenticate_user(session: Session, username: str, password: str) -> User:
    """Verify credentials using the same rules as Streamlit ``_login``."""
    user = (
        session.query(User)
        .filter_by(username=username.strip(), is_active=True)
        .first()
    )
    if not user or not verify_password(password, user.password_hash):
        raise LoginError()
    return user
