"""Description normalization for soft duplicate detection — Phase 18-MVP-2."""

from __future__ import annotations

import re

from services.money import money_to_float


def normalize_description(text: str | None) -> str:
    """Lowercase, strip, collapse whitespace for duplicate comparison."""
    if not text:
        return ""
    s = text.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def duplicate_row_key(
    *,
    row_date,
    amount: float,
    normalized_description: str,
    balance_after: float | None,
) -> tuple:
    """Composite soft-dup key per ROADMAP guardrails."""
    amt = money_to_float(amount or 0)
    if balance_after is not None:
        return (row_date, amt, normalized_description, money_to_float(balance_after))
    return (row_date, amt, normalized_description)
