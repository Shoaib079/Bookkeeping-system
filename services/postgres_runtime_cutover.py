"""POSTGRES-CUTOVER-PREP — flag-gated runtime cutover gate (parse-only; not wired).

Production ``DATABASE_URL`` remains SQLite until a future approved slice wires this
into startup. Separate from ``ERP_MONEY_NUMERIC_CUTOVER`` (schema 0001→0002 on SQLite).
"""

from __future__ import annotations

import os
from collections.abc import Mapping

RUNTIME_CUTOVER_ENV_VAR = "ERP_POSTGRES_RUNTIME_CUTOVER"
RUNTIME_CUTOVER_APPROVAL_ENV_VAR = "ERP_POSTGRES_RUNTIME_APPROVAL"
RUNTIME_CUTOVER_APPROVAL_PHRASE = "APPROVE PRODUCTION POSTGRES CUTOVER"

_TRUE_FLAG_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_FLAG_VALUES = frozenset({"0", "false", "no", "off"})


def parse_postgres_runtime_cutover_flag(value: str | None) -> bool:
    """Parse ``ERP_POSTGRES_RUNTIME_CUTOVER`` (default off)."""
    if value is None:
        return False
    normalized = value.strip().lower()
    if not normalized:
        return False
    if normalized in _TRUE_FLAG_VALUES:
        return True
    if normalized in _FALSE_FLAG_VALUES:
        return False
    return False


def is_postgres_runtime_cutover_enabled(
    environ: Mapping[str, str] | None = None,
) -> bool:
    source = os.environ if environ is None else environ
    return parse_postgres_runtime_cutover_flag(source.get(RUNTIME_CUTOVER_ENV_VAR))


def is_postgres_runtime_approval_given(
    environ: Mapping[str, str] | None = None,
) -> bool:
    source = os.environ if environ is None else environ
    value = source.get(RUNTIME_CUTOVER_APPROVAL_ENV_VAR)
    if value is None:
        return False
    return value.strip() == RUNTIME_CUTOVER_APPROVAL_PHRASE


def runtime_cutover_blocked_reason(
    *,
    cutover_flag: bool,
    approval_given: bool,
    target_is_sqlite: bool,
) -> str | None:
    """Return a human-readable block reason, or None when all gates pass (prep-only)."""
    if not cutover_flag:
        return "ERP_POSTGRES_RUNTIME_CUTOVER is off (default)."
    if not approval_given:
        return (
            f"Operator approval required: set {RUNTIME_CUTOVER_APPROVAL_ENV_VAR}="
            f"{RUNTIME_CUTOVER_APPROVAL_PHRASE!r}"
        )
    if target_is_sqlite:
        return "Target DATABASE_URL is still SQLite; runtime cutover not applied."
    return None
