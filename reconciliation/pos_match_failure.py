"""BANKING-UX-02 P4 — POS settlement match failure explanations (read-only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from reconciliation.pos_settlement_preview import PosSettlementPreview

_TOLERANCE = 0.01

_PREVIEW_WARNING_MAP: dict[str, tuple[str, bool]] = {
    "banking.pos_preview.warn_no_clearing": (
        "banking.match_failure.no_clearing_balance",
        True,
    ),
    "banking.pos_preview.warn_settlement_exceeds_clearing": (
        "banking.match_failure.settlement_exceeds_clearing",
        True,
    ),
    "banking.pos_preview.warn_fee_exceeds_settlement": (
        "banking.match_failure.fee_exceeds_settlement",
        True,
    ),
    "banking.pos_preview.warn_negative_deposit": (
        "banking.match_failure.negative_expected_deposit",
        True,
    ),
}


@dataclass
class MatchFailureItem:
    key: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    blocking: bool = True


@dataclass
class PosMatchFailureCheck:
    status: str  # ready | attention | cannot_post
    items: list[MatchFailureItem] = field(default_factory=list)


def evaluate_pos_match_failure(
    *,
    sel_row: Any | None,
    preview: PosSettlementPreview,
    deposit_amount: float,
    picked_sale_count: int,
    unsettled_sales_available: bool,
    bank_charges_enabled: bool,
    bank_charges_account_exists: bool,
    confirm_inferred_fee: bool,
    fee_gap_needs_confirm: bool,
    import_currency: str | None,
    company_currency: str,
    window_sales_available: bool = True,
) -> PosMatchFailureCheck:
    """Explain why a POS settlement may not match or post (uses P1 preview values)."""
    items: list[MatchFailureItem] = []

    if sel_row is None:
        items.append(
            MatchFailureItem("banking.match_failure.no_row_selected", blocking=True)
        )
        return _finalize(items)

    if getattr(sel_row, "status", None) == "posted":
        items.append(
            MatchFailureItem("banking.match_failure.row_already_posted", blocking=True)
        )

    is_deposit = bool(
        getattr(sel_row, "credit_amount", False)
        and not getattr(sel_row, "debit_amount", False)
    )
    if not is_deposit:
        items.append(MatchFailureItem("banking.match_failure.not_deposit", blocking=True))

    if not unsettled_sales_available:
        items.append(
            MatchFailureItem("banking.match_failure.no_unsettled_sales", blocking=True)
        )
    elif not window_sales_available:
        items.append(
            MatchFailureItem("banking.match_failure.no_sales_in_window", blocking=False)
        )

    if unsettled_sales_available and picked_sale_count == 0:
        items.append(
            MatchFailureItem("banking.match_failure.no_sales_selected", blocking=False)
        )

    for warn in preview.warnings:
        mapped = _PREVIEW_WARNING_MAP.get(warn.key)
        if mapped:
            key, blocking = mapped
            items.append(MatchFailureItem(key, dict(warn.kwargs), blocking=blocking))

    if (
        picked_sale_count > 0
        and preview.settlement_amount > _TOLERANCE
        and abs(deposit_amount - preview.expected_bank_deposit) > _TOLERANCE
    ):
        items.append(
            MatchFailureItem(
                "banking.match_failure.deposit_amount_mismatch",
                {
                    "deposit": deposit_amount,
                    "expected": preview.expected_bank_deposit,
                },
                blocking=True,
            )
        )

    if (
        preview.bank_charges > _TOLERANCE
        and bank_charges_enabled
        and not bank_charges_account_exists
    ):
        items.append(
            MatchFailureItem(
                "banking.match_failure.bank_charges_account_missing",
                blocking=True,
            )
        )

    if fee_gap_needs_confirm and not bank_charges_enabled:
        items.append(
            MatchFailureItem(
                "banking.match_failure.bank_charges_disabled",
                {
                    "deposit": deposit_amount,
                    "settlement": preview.settlement_amount,
                },
                blocking=True,
            )
        )
    elif fee_gap_needs_confirm and not confirm_inferred_fee:
        items.append(
            MatchFailureItem(
                "banking.match_failure.inferred_fee_unconfirmed",
                {"fee": preview.bank_charges},
                blocking=False,
            )
        )

    imp_cur = (import_currency or "").strip().upper()
    co_cur = (company_currency or "").strip().upper()
    if imp_cur and co_cur and imp_cur != co_cur:
        items.append(
            MatchFailureItem(
                "banking.match_failure.currency_mismatch",
                {"import_currency": imp_cur, "company_currency": co_cur},
                blocking=True,
            )
        )

    return _finalize(items)


def _finalize(items: list[MatchFailureItem]) -> PosMatchFailureCheck:
    if any(i.blocking for i in items):
        status = "cannot_post"
    elif items:
        status = "attention"
    else:
        status = "ready"
    return PosMatchFailureCheck(status=status, items=items)
