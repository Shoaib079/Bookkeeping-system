"""MONEY-DECIMAL-03 — pure Decimal money helpers for future migration.

Boundary parse/quantize utilities only. Not wired into posting, models, or ORM yet.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Union

MoneyInput = Union[int, float, str, Decimal]

MONEY_PRECISION = Decimal("0.01")
FX_PRECISION = Decimal("0.0001")
RATE_PRECISION = Decimal("0.00000001")


def parse_money(value: MoneyInput) -> Decimal:
    """Parse int/float/str/Decimal to Decimal.

    Floats are converted via ``str(value)`` so ``100.01`` stays ``Decimal('100.01')``
    instead of inheriting IEEE-754 binary expansion from ``Decimal(float)``.
    """
    if isinstance(value, bool):
        raise TypeError(f"parse_money does not accept bool, got {value!r}")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("parse_money: empty string")
        return Decimal(cleaned)
    raise TypeError(f"parse_money does not accept {type(value).__name__}")


def quantize_money(value: MoneyInput) -> Decimal:
    """Quantize to reporting currency (2 dp, ROUND_HALF_UP)."""
    return parse_money(value).quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)


def quantize_fx(value: MoneyInput) -> Decimal:
    """Quantize native FX amounts (4 dp, ROUND_HALF_UP)."""
    return parse_money(value).quantize(FX_PRECISION, rounding=ROUND_HALF_UP)


def quantize_rate(value: MoneyInput) -> Decimal:
    """Quantize FX rates (8 dp, ROUND_HALF_UP)."""
    return parse_money(value).quantize(RATE_PRECISION, rounding=ROUND_HALF_UP)


def money_to_float(value: MoneyInput) -> float:
    """Explicit float conversion after money quantization (Float compatibility seam)."""
    return float(quantize_money(value))


def decimal_equal(a: MoneyInput, b: MoneyInput) -> bool:
    """Return True when *a* and *b* match after money quantization."""
    return quantize_money(a) == quantize_money(b)
