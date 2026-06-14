"""FASTAPI-P2.6 — shared feature flag for partner/worker write endpoints."""

from __future__ import annotations

import os

from fastapi import HTTPException

WRITE_PARTNER_WORKER_ENV = "ERP_API_WRITE_PARTNER_WORKER"


def _write_partner_worker_enabled() -> bool:
    return os.getenv(WRITE_PARTNER_WORKER_ENV, "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def require_write_partner_worker_feature() -> None:
    if not _write_partner_worker_enabled():
        raise HTTPException(status_code=404, detail="Not Found")
