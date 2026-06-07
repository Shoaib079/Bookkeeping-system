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
    "financial_section_header_html",
    "financial_statement_table_html",
    "infer_column_kind",
    "readable_dataframe_table_html",
    "section_header_html",
    "tab_panel_intro",
    "theme_table_html",
]
