"""FASTAPI-P0.5d-S0 — boundary unit-of-work helper (scaffolding only).

Not wired into posting/audit families yet. Callers may use this directly in
tests or future shims when a family flips to boundary commit mode.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session


@contextmanager
def unit_of_work(session: Session) -> Generator[None, None, None]:
    """Own one transaction boundary: commit once on success, rollback on error."""
    try:
        yield
        session.commit()
    except Exception:
        session.rollback()
        raise


__all__ = ("unit_of_work",)
