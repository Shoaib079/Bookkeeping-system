"""FASTAPI-P1.2 — documented HTTP error contract for read-only endpoints.

Status mapping (stable):
- 401: missing ``X-User-Id`` (authentication context)
- 400: missing active company (``X-Company-Id``)
- 403: company membership denied or permission denied
- 404: scoped resource not found
- 422: query/path validation (FastAPI default)
"""

from __future__ import annotations

AUTH_MISSING_DETAIL = "X-User-Id header required"
COMPANY_MISSING_MARKER = "active_company_id"
MEMBERSHIP_DENIED_MARKER = "require_company_membership"
NOT_FOUND_PARTNER_STATEMENT = "Partner statement not found."
