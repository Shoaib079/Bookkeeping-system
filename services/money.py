"""MONEY-DECIMAL-03 — pure Decimal money helpers for ORM and migration boundaries.

Parse/quantize utilities used by posting, read services, and Numeric(asdecimal=True) columns.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Union

MoneyInput = Union[int, float, str, Decimal, None]

MONEY_PRECISION = Decimal("0.01")
FX_PRECISION = Decimal("0.0001")
RATE_PRECISION = Decimal("0.00000001")


def parse_money(value: MoneyInput) -> Decimal:
    """Parse int/float/str/Decimal/None to Decimal.

    Floats are converted via ``str(value)`` so ``100.01`` stays ``Decimal('100.01')``
    instead of inheriting IEEE-754 binary expansion from ``Decimal(float)``.
    """
    if value is None:
        return Decimal("0")
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


def line_money(value: MoneyInput) -> float:
    """2 dp float from a JE line debit/credit or other ORM money column."""
    return money_to_float(value)


def net_balance_delta(
    debit: MoneyInput,
    credit: MoneyInput,
    *,
    normal_debit: bool,
) -> float:
    """Signed net for one JE line (asset/expense vs liability/equity/income normal)."""
    d = money_to_float(debit)
    c = money_to_float(credit)
    return (d - c) if normal_debit else (c - d)


def persist_money(value: MoneyInput) -> Decimal:
    """Quantized Decimal for Numeric(19,2) ORM assignment."""
    return quantize_money(value)


def persist_fx(value: MoneyInput) -> Decimal:
    """Quantized Decimal for Numeric(19,4) ORM assignment."""
    return quantize_fx(value)


def persist_rate(value: MoneyInput) -> Decimal:
    """Quantized Decimal for Numeric(19,8) ORM assignment."""
    return quantize_rate(value)


def fx_to_float(value: MoneyInput) -> float:
    """4 dp native FX amount → float after quantize."""
    return float(quantize_fx(value))


def rate_to_float(value: MoneyInput) -> float:
    """8 dp FX rate → float after quantize."""
    return float(quantize_rate(value))


def decimal_equal(a: MoneyInput, b: MoneyInput) -> bool:
    """Return True when *a* and *b* match after money quantization."""
    return quantize_money(a) == quantize_money(b)
