"""Reusable section headers — Phase 16A stub for 16C page sweep.

UI-1 accent policy: default page banners use accent="info" (implicit).
Use accent-success/danger/warning/purple/teal only for workflow-status
subsections (validation, import steps, warnings) — not routine page titles.
See docs/UI_STYLE_GUIDE.md — Global Readability and Financial Statement Rules.
"""

from __future__ import annotations

import html
from typing import Any

_ACCENT_CLASS = {
    "info": "",
    "success": "accent-success",
    "danger": "accent-danger",
    "warning": "accent-warning",
    "purple": "accent-purple",
    "teal": "accent-teal",
}

_FIN_SECTION_ACCENT = {
    "info": ("var(--theme-info)", "color-mix(in srgb,var(--theme-info) 12%,var(--theme-card) 88%)",
             "color-mix(in srgb,var(--theme-info) 35%,var(--theme-border) 65%)"),
    "success": ("var(--theme-success)", "color-mix(in srgb,var(--theme-success) 12%,var(--theme-card) 88%)",
                "color-mix(in srgb,var(--theme-success) 35%,var(--theme-border) 65%)"),
    "danger": ("var(--theme-danger)", "color-mix(in srgb,var(--theme-danger) 12%,var(--theme-card) 88%)",
               "color-mix(in srgb,var(--theme-danger) 35%,var(--theme-border) 65%)"),
    "warning": ("var(--theme-warning)", "color-mix(in srgb,var(--theme-warning) 14%,var(--theme-card) 86%)",
                "color-mix(in srgb,var(--theme-warning) 35%,var(--theme-border) 65%)"),
    "purple": ("var(--theme-purple)", "color-mix(in srgb,var(--theme-purple) 12%,var(--theme-card) 88%)",
               "color-mix(in srgb,var(--theme-purple) 35%,var(--theme-border) 65%)"),
}

# (header label, row dict key, cell kind: code|name|amount|num|text)
FinColumn = tuple[str, str, str]

_NUMERIC_COL_HINTS = (
    "amount", "total", "debit", "credit", "balance", "cash", "card",
    "count", "transactions", "invoices", "budgeted", "actual", "variance",
    "paid", "outstanding", "qty", "quantity", "sales", "expenses", "profit",
    "diff", "pending", "share", "avg", "net", "gross", "fee", "deposit",
    "withdrawal", "movement", "estimate", "snapshot", "now", "valid", "errors",
)
_NAME_COL_HINTS = (
    "customer", "vendor", "account", "description", "category", "method",
    "supplier", "party", "name", "partner", "worker", "product", "reference",
    "warnings", "closed by", "template", "note", "recon", "type", "status",
    "bank_name", "account_number", "kind", "weekday", "closed at",
)
_CODE_COL_HINTS = ("code", "je#", "id")


def infer_column_kind(col: str) -> str:
    """Map a DataFrame column name to a financial table cell kind."""
    c = str(col).lower().strip()
    if c in _CODE_COL_HINTS or c.endswith("#") or c in ("id", "je#"):
        return "code"
    if c.endswith("%") or any(h in c for h in _NUMERIC_COL_HINTS):
        return "amount"
    if any(h in c for h in _NAME_COL_HINTS):
        return "name"
    if c in ("date", "month", "active", "voided", "actioned", "next due", "due date"):
        return "text"
    return "text"


def section_header_html(title: str, *, accent: str = "info") -> str:
    """Token-based section title (replaces inline #3b82f6 / #6b7280 blocks)."""
    safe = html.escape(str(title))
    extra = _ACCENT_CLASS.get(accent, "")
    cls = f"erp-section-hdr {extra}".strip()
    return f'<div class="{cls}">{safe}</div>'


def page_report_banner_html(
    title: str,
    *,
    subtitle: str = "",
    meta: str = "",
    meta_sub: str = "",
) -> str:
    """Mono report page banner — card surface with left info accent (no gradients)."""
    safe_title = html.escape(str(title))
    sub = (
        f'<div class="erp-page-banner-sub">{html.escape(subtitle)}</div>'
        if subtitle else ""
    )
    meta_block = ""
    if meta or meta_sub:
        meta_main = f'<div class="erp-page-banner-meta-main">{html.escape(meta)}</div>' if meta else ""
        meta_sub_html = (
            f'<div class="erp-page-banner-meta-sub">{html.escape(meta_sub)}</div>'
            if meta_sub else ""
        )
        meta_block = f'<div class="erp-page-banner-meta">{meta_main}{meta_sub_html}</div>'
    return (
        f'<div class="erp-page-banner">'
        f'<div class="erp-page-banner-left">'
        f'<div class="erp-page-banner-title">{safe_title}</div>{sub}'
        f"</div>{meta_block}</div>"
    )


def aging_buckets_html(
    buckets: dict[str, float],
    currency: str,
    label_for,
    *,
    decimals: int = 0,
) -> str:
    """Mono aging bucket grid — same card style for every bucket; amounts stay readable."""
    parts: list[str] = []
    fmt = f",.{decimals}f"
    for bucket, amt in buckets.items():
        if amt <= 0:
            continue
        label = html.escape(str(label_for(bucket)))
        parts.append(
            f'<div class="erp-aging-bucket">'
            f'<div class="erp-aging-bucket-label">{label}</div>'
            f'<div class="erp-aging-bucket-amt">{html.escape(currency)} {amt:{fmt}}</div>'
            f"</div>"
        )
    if not parts:
        return ""
    return f'<div class="erp-aging-grid">{"".join(parts)}</div>'


def mono_role_pill_html(label: str) -> str:
    """Single-style role pill — role name carries meaning, not background color."""
    return f'<span class="erp-mono-pill">{html.escape(str(label))}</span>'


_MOB_STATUS_VARIANTS = frozenset({
    "success", "warning", "danger", "info", "neutral", "void", "corrected",
})


def mobile_status_pill_html(label: str, *, variant: str = "neutral") -> str:
    """Token-based status pill for mobile list cards and ledger rows."""
    v = variant if variant in _MOB_STATUS_VARIANTS else "neutral"
    cls = f"erp-mob-status-pill erp-mob-status-pill--{v}"
    return f'<span class="{cls}">{html.escape(str(label))}</span>'


def mobile_kpi_chip_html(label: str, value: str, *, variant: str = "") -> str:
    """Compact KPI chip — label + value using shared mobile token grammar."""
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))
    value_cls = "erp-mob-kpi-value"
    if variant:
        if variant.startswith(("kpi-", "amt-")):
            value_cls += f" {variant}"
        elif variant in ("success", "danger", "warning", "info", "neutral"):
            value_cls += f" kpi-{variant}"
    return (
        f'<div class="erp-mob-kpi-chip">'
        f'<div class="erp-mob-kpi-label">{safe_label}</div>'
        f'<div class="{value_cls}">{safe_value}</div>'
        f"</div>"
    )


def mobile_kpi_grid_html(*chips: str) -> str:
    return f'<div class="erp-mob-kpi-grid">{"".join(chips)}</div>'


def mobile_empty_state_html(message: str) -> str:
    return f'<div class="erp-mob-empty">{html.escape(str(message))}</div>'


def mobile_section_label_html(label: str) -> str:
    return f'<div class="erp-mob-section-label">{html.escape(str(label))}</div>'


def mobile_screen_title_html(title: str) -> str:
    return f'<div class="erp-mob-screen-title">{html.escape(str(title))}</div>'


def mobile_list_row_html(
    title: str,
    *,
    subtitle: str = "",
    amount: str = "",
    amount_variant: str = "",
    icon_block: str = "",
    title_extra_html: str = "",
    meta_sub: str = "",
) -> str:
    """Mobile list row — optional icon column, title/subtitle, right-aligned amount."""
    amt_cls = "erp-mob-list-row-amt"
    if amount_variant in ("in", "pos", "success"):
        amt_cls += " amt-pos"
    elif amount_variant in ("out", "neg", "danger"):
        amt_cls += " amt-neg"
    sub = (
        f'<div class="erp-mob-list-row-sub">{html.escape(str(subtitle))}</div>'
        if subtitle
        else ""
    )
    if amount or meta_sub:
        meta_amt_cls = "erp-mob-list-row-meta-amt"
        if amount_variant in ("in", "pos", "success"):
            meta_amt_cls += " amt-pos"
        elif amount_variant in ("out", "neg", "danger"):
            meta_amt_cls += " amt-neg"
        meta_amt = (
            f'<div class="{meta_amt_cls}">{html.escape(str(amount))}</div>'
            if amount
            else ""
        )
        meta_date = (
            f'<div class="erp-mob-list-row-meta-sub">{html.escape(str(meta_sub))}</div>'
            if meta_sub
            else ""
        )
        amt = (
            f'<div class="erp-mob-list-row-meta">{meta_amt}{meta_date}</div>'
        )
    else:
        amt = ""
    return (
        f'<div class="erp-mob-list-row">'
        f"{icon_block}"
        f'<div class="erp-mob-list-row-main">'
        f'<div class="erp-mob-list-row-title">{html.escape(str(title))}{title_extra_html}</div>'
        f"{sub}</div>"
        f"{amt}</div>"
    )


def mobile_highlight_banner_html(
    title: str,
    value: str,
    *,
    subtitle: str = "",
    variant: str = "success",
) -> str:
    """Token highlight banner for net P&L / cash-flow summary rows."""
    v = variant if variant in ("success", "danger", "neutral") else "neutral"
    sub = (
        f'<div class="erp-mob-highlight-banner-sub">{html.escape(str(subtitle))}</div>'
        if subtitle
        else ""
    )
    return (
        f'<div class="erp-mob-highlight-banner erp-mob-highlight-banner--{v}">'
        f'<div><div class="erp-mob-highlight-banner-title">{html.escape(str(title))}</div>'
        f"{sub}</div>"
        f'<div class="erp-mob-highlight-banner-value">{html.escape(str(value))}</div>'
        f"</div>"
    )


def theme_table_html(
    columns: list[str],
    rows: list[list[str]],
    *,
    numeric_cols: set[int] | None = None,
) -> str:
    """Token-themed HTML table (`.erp-data-table`) — dark/light safe."""
    num_set = numeric_cols or set()
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in columns)
    body_rows: list[str] = []
    for row in rows:
        cells: list[str] = []
        for i, cell in enumerate(row):
            cls = ' class="num"' if i in num_set else ""
            cells.append(f"<td{cls}>{html.escape(str(cell))}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return (
        '<div class="erp-data-table-wrap">'
        f'<table class="erp-data-table"><thead><tr>{head}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody></table></div>"
    )


def _format_fin_cell(value: Any, kind: str) -> str:
    if value is None or value == "":
        return "—" if kind in ("amount", "num") else ""
    if kind in ("amount", "num") and isinstance(value, (int, float)):
        return f"{value:,.2f}"
    return str(value)


def _fin_cell_class(kind: str) -> str:
    if kind == "code":
        return "erp-fin-code"
    if kind == "name":
        return "erp-fin-name"
    if kind in ("amount", "num"):
        return "erp-fin-amount"
    return "erp-fin-text"


def financial_statement_table_html(
    columns: list[FinColumn],
    rows: list[dict],
    *,
    total_row_indexes: set[int] | None = None,
    row_flags: dict[int, str] | None = None,
) -> str:
    """Readable financial table — code, name, and amounts never clipped.

    Uses `.erp-fin-table` (see docs/UI_STYLE_GUIDE.md).
    row_flags: optional {row_index: "over"|"ok"|"warn"} for status highlighting.
    """
    totals = total_row_indexes or set()
    flags = row_flags or {}
    head = "".join(
        f'<th class="{_fin_cell_class(kind)}">{html.escape(label)}</th>'
        for label, _, kind in columns
    )
    body_rows: list[str] = []
    for idx, row in enumerate(rows):
        tr_cls = "erp-fin-row"
        if idx in totals:
            tr_cls += " erp-fin-row-total"
        flag = flags.get(idx)
        if flag:
            tr_cls += f" erp-fin-row-{flag}"
        cells: list[str] = []
        for _, key, kind in columns:
            raw = row.get(key, "")
            text = _format_fin_cell(raw, kind)
            cells.append(
                f'<td class="{_fin_cell_class(kind)}">{html.escape(text)}</td>'
            )
        body_rows.append(f'<tr class="{tr_cls}">{"".join(cells)}</tr>')
    return (
        '<div class="erp-fin-table-wrap">'
        f'<table class="erp-fin-table"><thead><tr>{head}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody></table></div>"
    )


def readable_dataframe_table_html(
    df,
    *,
    total_row_indexes: set[int] | None = None,
    status_col: str | None = None,
) -> str:
    """Build `.erp-fin-table` HTML from a pandas DataFrame (read-only display)."""
    import pandas as pd

    if df is None or getattr(df, "empty", True):
        return ""
    columns: list[FinColumn] = [
        (str(c), str(c), infer_column_kind(str(c))) for c in df.columns
    ]
    records: list[dict] = []
    for rec in df.to_dict("records"):
        clean: dict = {}
        for k, v in rec.items():
            if v is None or (isinstance(v, float) and pd.isna(v)):
                clean[k] = None
            else:
                clean[k] = v
        records.append(clean)
    row_flags: dict[int, str] = {}
    if status_col:
        for i, rec in enumerate(records):
            st = rec.get(status_col)
            if st == "Over":
                row_flags[i] = "over"
            elif st in ("On track", "Balanced", "OK", "Active"):
                row_flags[i] = "ok"
            elif st in ("Warning", "Stale", "Voided"):
                row_flags[i] = "warn"
    return financial_statement_table_html(
        columns,
        records,
        total_row_indexes=total_row_indexes,
        row_flags=row_flags or None,
    )


def financial_section_header_html(
    title: str,
    amount_text: str = "",
    *,
    subtitle: str = "",
    accent: str = "info",
) -> str:
    """Section card header for financial statements (token-safe, mono)."""
    fg, bg, border = _FIN_SECTION_ACCENT.get(accent, _FIN_SECTION_ACCENT["info"])
    safe_title = html.escape(str(title))
    amt_html = (
        f'<span class="erp-fin-section-amt">{html.escape(amount_text)}</span>'
        if amount_text
        else ""
    )
    sub_html = (
        f'<span class="erp-fin-section-sub">{html.escape(subtitle)}</span>'
        if subtitle
        else ""
    )
    right = amt_html or sub_html
    if amt_html and sub_html:
        right = f'{amt_html}<span class="erp-fin-section-sub">{html.escape(subtitle)}</span>'
    return (
        f'<div class="erp-fin-section-hdr" style="background:{bg};border-bottom:1px solid {border};">'
        f'<span class="erp-fin-section-title" style="color:{fg};">{safe_title}</span>'
        f'<span class="erp-fin-section-right" style="color:{fg};">{right}</span>'
        f"</div>"
    )


def tab_panel_intro(
    title: str | None = None,
    *,
    caption: str | None = None,
) -> str:
    """Heading strip inside a tab panel — separates tab bar from panel content."""
    parts: list[str] = []
    if title:
        parts.append(f'<div class="erp-tab-intro-title">{html.escape(title)}</div>')
    if caption:
        parts.append(f'<div class="erp-tab-intro-caption">{html.escape(caption)}</div>')
    if not parts:
        return '<div class="erp-tab-intro erp-tab-intro--gap-only" aria-hidden="true"></div>'
    return f'<div class="erp-tab-intro">{"".join(parts)}</div>'


__all__ = [
    "FinColumn",
    "aging_buckets_html",
    "financial_section_header_html",
    "financial_statement_table_html",
    "infer_column_kind",
    "mobile_empty_state_html",
    "mobile_highlight_banner_html",
    "mobile_kpi_chip_html",
    "mobile_kpi_grid_html",
    "mobile_list_row_html",
    "mobile_screen_title_html",
    "mobile_section_label_html",
    "mobile_status_pill_html",
    "mono_role_pill_html",
    "page_report_banner_html",
    "readable_dataframe_table_html",
    "section_header_html",
    "tab_panel_intro",
    "theme_table_html",
]
