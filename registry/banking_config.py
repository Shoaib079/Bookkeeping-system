"""BANKING-UX-03 P2.3 — banking workspace config (presentation + policy helpers)."""

from __future__ import annotations

from registry.service import get_setting

# System invariant (A): batch may only target bank_fee; settings may narrow, never widen.
BANKING_BATCH_SAFE_KINDS: frozenset[str] = frozenset({"bank_fee"})

REVIEW_KIND_IDS: frozenset[str] = frozenset(
    {
        "transfer_charges",
        "payroll",
        "vendor",
        "equity_loan",
        "low_confidence",
    }
)

LANDING_IDS: frozenset[str] = frozenset({"cockpit", "queue", "accounts"})
IMPORT_TAB_IDS: frozenset[str] = frozenset({"upload", "review", "match", "history"})
QUEUE_SORT_IDS: frozenset[str] = frozenset({"date", "amount", "confidence"})
QUEUE_DENSITY_IDS: frozenset[str] = frozenset({"compact", "comfortable"})
BANKING_WORKFLOW_MODE_IDS: frozenset[str] = frozenset(
    {"statement_first", "hybrid", "manual_first"}
)
BANKING_WORKFLOW_MODE_DEFAULT = "statement_first"

_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}


def _parse_kind_csv(raw: str | None, *, allowed: frozenset[str]) -> frozenset[str]:
    if not raw:
        return frozenset()
    parts = {p.strip() for p in str(raw).split(",") if p.strip()}
    return frozenset(k for k in parts if k in allowed)


def banking_batch_safe_kinds() -> frozenset[str]:
    return BANKING_BATCH_SAFE_KINDS


def banking_normalize_batch_kinds(requested: str | frozenset[str] | None) -> frozenset[str]:
    """Intersect requested kinds with the safe invariant — never widen."""
    if isinstance(requested, frozenset):
        parts = requested
    else:
        parts = _parse_kind_csv(requested, allowed=BANKING_BATCH_SAFE_KINDS)
    return BANKING_BATCH_SAFE_KINDS & parts


def banking_batch_eligible_kinds(session, company_id: int) -> frozenset[str]:
    raw = get_setting(session, "banking.batch_eligible_kinds", company_id=company_id)
    return banking_normalize_batch_kinds(raw or "bank_fee")


def banking_batch_posting_enabled(session, company_id: int) -> bool:
    return bool(
        get_setting(session, "banking.batch_posting_enabled", company_id=company_id)
    )


def banking_review_required_kinds(session, company_id: int) -> frozenset[str]:
    raw = get_setting(session, "banking.review_required_kinds", company_id=company_id)
    return _parse_kind_csv(raw, allowed=REVIEW_KIND_IDS)


def banking_batch_confidence_threshold(session, company_id: int) -> str:
    val = get_setting(
        session, "banking.batch_confidence_threshold", company_id=company_id
    )
    if val not in ("high", "high_and_medium"):
        return "high"
    return val


def banking_confidence_meets_batch_threshold(threshold: str, confidence: str) -> bool:
    """Bounded batch threshold — never admits low-confidence rows."""
    if confidence == "low":
        return False
    if threshold == "high_and_medium":
        return confidence in ("high", "medium")
    return confidence == "high"


def banking_normalize_workflow_mode(value: str | None) -> str:
    """Company workflow mode — UI routing only; invalid values fall back safely."""
    if value in BANKING_WORKFLOW_MODE_IDS:
        return value
    return BANKING_WORKFLOW_MODE_DEFAULT


def banking_workflow_mode(session, company_id: int) -> str:
    raw = get_setting(session, "banking.workflow_mode", company_id=company_id)
    return banking_normalize_workflow_mode(raw)


def banking_resolve_landing(
    session,
    company_id: int,
    *,
    user_id: int | None = None,
) -> str:
    """Company default landing with optional user override."""
    user_pref = "inherit"
    if user_id is not None:
        user_pref = (
            get_setting(
                session,
                "banking.landing_preference",
                company_id=company_id,
                user_id=user_id,
            )
            or "inherit"
        )
    if user_pref in LANDING_IDS:
        return user_pref
    company_default = (
        get_setting(session, "banking.default_landing", company_id=company_id)
        or "cockpit"
    )
    return company_default if company_default in LANDING_IDS else "cockpit"


def banking_default_import_tab(
    session,
    company_id: int,
    *,
    user_id: int | None = None,
) -> str:
    tab = "match"
    if user_id is not None:
        tab = (
            get_setting(
                session,
                "banking.default_import_tab",
                company_id=company_id,
                user_id=user_id,
            )
            or "match"
        )
    return tab if tab in IMPORT_TAB_IDS else "match"


def banking_show_confidence_chips(
    session,
    company_id: int,
    *,
    user_id: int | None = None,
) -> bool:
    if user_id is None:
        return True
    return bool(
        get_setting(
            session,
            "banking.show_confidence_chips",
            company_id=company_id,
            user_id=user_id,
        )
    )


def banking_show_accounting_previews(
    session,
    company_id: int,
    *,
    user_id: int | None = None,
) -> bool:
    if user_id is None:
        return True
    return bool(
        get_setting(
            session,
            "banking.show_accounting_previews",
            company_id=company_id,
            user_id=user_id,
        )
    )


def banking_queue_sort(
    session,
    company_id: int,
    *,
    user_id: int | None = None,
) -> str:
    sort = "date"
    if user_id is not None:
        sort = (
            get_setting(
                session,
                "banking.queue_sort",
                company_id=company_id,
                user_id=user_id,
            )
            or "date"
        )
    return sort if sort in QUEUE_SORT_IDS else "date"


def banking_queue_density(
    session,
    company_id: int,
    *,
    user_id: int | None = None,
) -> str:
    density = "comfortable"
    if user_id is not None:
        density = (
            get_setting(
                session,
                "banking.queue_density",
                company_id=company_id,
                user_id=user_id,
            )
            or "comfortable"
        )
    return density if density in QUEUE_DENSITY_IDS else "comfortable"


def banking_sort_queue_rows(rows: list[dict], *, sort_key: str) -> list[dict]:
    """Sort queue presentation rows — does not change posting."""
    if sort_key == "amount":
        return sorted(rows, key=lambda r: abs(r.get("amount", 0.0)), reverse=True)
    if sort_key == "confidence":
        return sorted(
            rows,
            key=lambda r: _CONFIDENCE_RANK.get(r.get("confidence", "low"), 0),
            reverse=True,
        )
    return sorted(rows, key=lambda r: (r.get("date") or "", r.get("import_row_index", 0)))


def banking_accounting_preview(kind: str, *, description: str = "") -> str | None:
    """Read-only JE hint for match detail — no posting impact."""
    from reconciliation.match_post import (
        bank_charge_fee_label,
        infer_bank_charge_subtype,
    )

    if kind == "bank_fee":
        subtype = infer_bank_charge_subtype(description)
        label = bank_charge_fee_label(subtype)
        return f"Dr Bank Charges / Cr Bank · {label}"
    if kind == "vendor":
        return "Dr Expense or Payable / Cr Bank"
    if kind == "worker_payroll":
        return "Dr Salary Expense / Cr Bank"
    if kind == "cc_bill":
        return "Dr Credit Card Payable / Cr Bank"
    if kind == "card_clearing":
        return "Dr Bank / Cr Card Sales Clearing (+ fee if applicable)"
    if kind == "equity_loan":
        return "Dr/Cr partner or loan accounts / Cr or Dr Bank"
    if kind == "other_income":
        return "Dr Bank / Cr Income"
    return None


def banking_batch_review_reason_for_row(
    session,
    company_id: int,
    *,
    detected_kind: str,
    confidence: str,
    description: str,
    subtype: str | None = None,
) -> str | None:
    """Extra review-policy codes on top of P2.2-A eligibility (batch narrowing only)."""
    review_kinds = banking_review_required_kinds(session, company_id)
    threshold = banking_batch_confidence_threshold(session, company_id)

    if detected_kind not in banking_batch_eligible_kinds(session, company_id):
        return "batch_kind_excluded"

    if "low_confidence" in review_kinds and confidence == "low":
        return "low_confidence"
    if not banking_confidence_meets_batch_threshold(threshold, confidence):
        return "low_confidence"

    if "transfer_charges" in review_kinds and subtype == "transfer_fee":
        return "review_required_transfer"

    return None
