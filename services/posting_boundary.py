"""FASTAPI-REACT-01 — posting boundary scope helpers (PS-P7).

Thin context managers for per-family boundary commits. Streamlit shims and
future API handlers wrap post/void/recon orchestration without duplicating
``is_boundary_mode`` + ``boundary_depth`` checks.
"""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from typing import Iterator

from services import commit_modes as _commit_modes
from services.unit_of_work import boundary_commit_scope, boundary_depth


@contextmanager
def posting_boundary_scope(session, family: str) -> Iterator[None]:
    """Wrap a post-family shim when commit mode is ``boundary`` at outer depth."""
    if _commit_modes.is_boundary_mode(family) and boundary_depth() == 0:
        with boundary_commit_scope(session, family):
            yield
    else:
        with nullcontext():
            yield


@contextmanager
def recon_boundary_scope(session) -> Iterator[None]:
    """One boundary commit for reconciliation poster + audit (FASTAPI-P0.5d-S7)."""
    family = _commit_modes.RECONCILIATION_FAMILY
    if _commit_modes.is_boundary_mode(family) and boundary_depth() == 0:
        with boundary_commit_scope(session, family):
            yield
    else:
        with nullcontext():
            yield


@contextmanager
def void_boundary_scope(session) -> Iterator[None]:
    """One boundary commit for void cascade + audit (FASTAPI-P0.5d-S8)."""
    family = _commit_modes.VOID_CASCADE_FAMILY
    if _commit_modes.is_boundary_mode(family) and boundary_depth() == 0:
        with boundary_commit_scope(session, family):
            yield
    else:
        with nullcontext():
            yield
