"""Monetary amount parsing — mirrors app._parse_amount_str without Streamlit coupling."""

from __future__ import annotations


def parse_amount_str(raw: str | None) -> float | None:
    """Parse amount strings with US/EU decimal and thousands separators."""
    if raw is None:
        return None
    s = str(raw).strip().replace("\xa0", "").replace(" ", "")
    if not s or s in ("-", "—"):
        return None

    has_comma = "," in s
    has_period = "." in s

    if has_comma and has_period:
        if s.rfind(".") > s.rfind(","):
            cleaned = s.replace(",", "")
        else:
            cleaned = s.replace(".", "").replace(",", ".")
    elif has_comma:
        parts = s.split(",")
        if len(parts) > 1 and all(len(g) == 3 and g.isdigit() for g in parts[1:]):
            cleaned = s.replace(",", "")
        else:
            cleaned = s.replace(",", ".")
    elif has_period:
        parts = s.split(".")
        if len(parts) > 1 and all(len(g) == 3 and g.isdigit() for g in parts[1:]):
            cleaned = s.replace(".", "")
        else:
            cleaned = s
    else:
        cleaned = s

    try:
        return float(cleaned)
    except ValueError:
        return None
