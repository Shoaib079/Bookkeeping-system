"""FASTAPI-P0.5d — boundary unit-of-work helper (TD-PS-01)."""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session

from services.commit_modes import is_boundary_mode

_boundary_depth: contextvars.ContextVar[int] = contextvars.ContextVar(
    "boundary_depth", default=0
)
_active_boundary_family: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "active_boundary_family", default=None
)


def boundary_depth() -> int:
    return _boundary_depth.get()


def get_active_boundary_family() -> str | None:
    return _active_boundary_family.get()


@contextmanager
def unit_of_work(session: Session) -> Generator[None, None, None]:
    """Own one transaction boundary: commit once on success, rollback on error."""
    try:
        yield
        session.commit()
    except Exception:
        session.rollback()
        raise


@contextmanager
def boundary_commit_scope(session: Session, family: str) -> Generator[None, None, None]:
    """Reentrant boundary scope: outermost exit commits once when family is boundary."""
    if not is_boundary_mode(family):
        yield
        return

    depth = _boundary_depth.get() + 1
    depth_token = _boundary_depth.set(depth)
    family_token = None
    if depth == 1:
        family_token = _active_boundary_family.set(family)
    try:
        yield
        if depth == 1:
            session.commit()
    except Exception:
        if depth == 1:
            session.rollback()
        raise
    finally:
        _boundary_depth.reset(depth_token)
        if depth == 1 and family_token is not None:
            _active_boundary_family.reset(family_token)


__all__ = (
    "boundary_commit_scope",
    "boundary_depth",
    "get_active_boundary_family",
    "unit_of_work",
)
