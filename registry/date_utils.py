"""DATE-MASK-01 — shared date format/parse/mask engine (no Streamlit)."""

from __future__ import annotations

import datetime

DATE_FORMAT_OPTIONS: tuple[str, ...] = ("DD.MM.YYYY", "DD/MM/YYYY", "YYYY-MM-DD")
DATE_FORMAT_DEFAULT = "DD.MM.YYYY"
DATE_FORMAT_LEGACY_TO_CANONICAL = {
    "DD MMM YYYY": "DD.MM.YYYY",
    "MM/DD/YYYY": "DD/MM/YYYY",
}
DATE_FORMAT_STRFTIME: dict[str, str] = {
    "DD.MM.YYYY": "%d.%m.%Y",
    "DD/MM/YYYY": "%d/%m/%Y",
    "YYYY-MM-DD": "%Y-%m-%d",
    "DD MMM YYYY": "%d %b %Y",
    "MM/DD/YYYY": "%m/%d/%Y",
}
DATE_PARSE_HINT = "YYYY-MM-DD · DD.MM.YYYY · DD/MM/YYYY"


def normalize_user_date_format(pref: str) -> str:
    """Map profile/legacy tokens to a known display format key."""
    p = (pref or "").strip()
    if p in DATE_FORMAT_STRFTIME:
        return p
    return DATE_FORMAT_LEGACY_TO_CANONICAL.get(p, DATE_FORMAT_DEFAULT)


def canonical_user_date_format(pref: str) -> str:
    """Profile selectbox value — legacy prefs map to canonical options."""
    p = normalize_user_date_format(pref)
    if p in DATE_FORMAT_OPTIONS:
        return p
    return DATE_FORMAT_LEGACY_TO_CANONICAL.get(p, DATE_FORMAT_DEFAULT)


def normalize_date_digits(raw: str) -> str:
    """Strip non-digits and cap at eight (one complete date without separators)."""
    return "".join(c for c in (raw or "") if c.isdigit())[:8]


def format_date_for_preference(d: datetime.date, preference: str) -> str:
    key = normalize_user_date_format(preference)
    fmt = DATE_FORMAT_STRFTIME.get(key, DATE_FORMAT_STRFTIME[DATE_FORMAT_DEFAULT])
    return d.strftime(fmt)


def parse_date_text(raw: str, preference: str | None = None) -> datetime.date | None:
    """Parse a date string — separators agnostic; digit-only uses *preference* order."""
    s = (raw or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    digits = normalize_date_digits(s)
    if len(digits) != 8:
        return None
    pref = normalize_user_date_format(preference or DATE_FORMAT_DEFAULT)
    try:
        if pref == "YYYY-MM-DD":
            return datetime.datetime.strptime(digits, "%Y%m%d").date()
        return datetime.datetime.strptime(digits, "%d%m%Y").date()
    except ValueError:
        return None


def format_date_input_for_preference(raw: str, preference: str) -> str:
    """Mask typed/pasted text with separators for the user's date-format preference."""
    pref = normalize_user_date_format(preference)
    s = (raw or "").strip()
    if not s:
        return ""

    parsed = parse_date_text(s, preference)
    if parsed is not None and (
        len(normalize_date_digits(s)) == 8 or any(c in s for c in ".-/")
    ):
        return format_date_for_preference(parsed, pref)

    digits = normalize_date_digits(s)
    if not digits:
        return s

    if pref == "YYYY-MM-DD":
        if len(digits) <= 4:
            return digits
        if len(digits) <= 6:
            return f"{digits[:4]}-{digits[4:]}"
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"

    sep = "." if pref == "DD.MM.YYYY" else "/"
    if len(digits) <= 2:
        return digits
    if len(digits) <= 4:
        return f"{digits[:2]}{sep}{digits[2:]}"
    return f"{digits[:2]}{sep}{digits[2:4]}{sep}{digits[4:8]}"


def date_input_placeholder(preference: str) -> str:
    sample = format_date_for_preference(datetime.date(2026, 6, 12), preference)
    return f"{sample} ({DATE_PARSE_HINT})"
