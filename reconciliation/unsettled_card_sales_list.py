"""BANKING-UX-02 P3 — Unsettled card sales list helpers (read-only)."""

from __future__ import annotations

import datetime
from typing import Any

from models import Sale

_TOLERANCE = 0.01
DEFAULT_LIST_LIMIT = 50


def sum_unsettled_card_sales(rows: list[dict[str, Any]]) -> float:
    return round(sum(r.get("amount", 0) for r in rows), 2)


def list_total_mismatch(list_total: float, visibility_total: float) -> bool:
    return abs(round(list_total, 2) - round(visibility_total, 2)) > _TOLERANCE


def filter_unsettled_by_date(
    rows: list[dict[str, Any]],
    *,
    date_from: datetime.date | None,
    date_to: datetime.date | None,
) -> list[dict[str, Any]]:
    out = rows
    if date_from is not None:
        out = [r for r in out if r.get("date") and r["date"] >= date_from]
    if date_to is not None:
        out = [r for r in out if r.get("date") and r["date"] <= date_to]
    return out


def apply_list_limit(
    rows: list[dict[str, Any]],
    *,
    show_all: bool,
    limit: int = DEFAULT_LIST_LIMIT,
) -> tuple[list[dict[str, Any]], bool]:
    if show_all or len(rows) <= limit:
        return rows, False
    return rows[-limit:], True


def enrich_unsettled_sale_row(
    session,
    row: dict[str, Any],
    *,
    default_currency: str,
) -> dict[str, Any]:
    sale = session.get(Sale, row.get("sale_id"))
    currency = default_currency
    notes = row.get("customer") or ""
    payment_method = "Card"
    if sale is not None:
        currency = sale.currency or default_currency
        if sale.description:
            notes = sale.description
        elif sale.customer_name:
            notes = sale.customer_name
        payment_method = sale.sale_type or "Card"
    return {
        **row,
        "currency": currency,
        "payment_method": payment_method,
        "notes": notes,
        "reference": row.get("invoice") or f"#{row.get('sale_id')}",
        "settlement_status": "unsettled",
    }
