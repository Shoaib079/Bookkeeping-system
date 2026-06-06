"""Merchant settlement statement parsing — Phase 18-MVP-4."""

from __future__ import annotations

import datetime
import json
from typing import Any

import pandas as pd

from reconciliation.amounts import parse_amount_str
from reconciliation.statement_parse import (
    _cell_raw,
    _cell_str,
    _parse_date,
    _raw_line_from_row,
    mapping_to_json,
    read_tabular_preview,
    suggest_column_mapping,
    _read_dataframe,
)

SETTLEMENT_FIELDS = (
    "date",
    "description",
    "gross",
    "fee",
    "net",
    "batch_reference",
)

SETTLEMENT_PRESETS: dict[str, dict[str, tuple[str, ...]]] = {
    "generic_en": {
        "date": ("date", "settlement date", "batch date", "value date"),
        "description": ("description", "details", "batch", "merchant"),
        "gross": ("gross", "gross amount", "sales amount", "total sales"),
        "fee": ("fee", "fees", "commission", "processor fee", "bank charge"),
        "net": ("net", "net amount", "deposit", "settlement amount", "paid amount"),
        "batch_reference": ("reference", "batch id", "batch no", "batch number"),
    },
    "generic_tr": {
        "date": ("tarih", "işlem tarihi", "islem tarihi", "valör tarihi", "valor tarihi"),
        "description": ("açıklama", "aciklama", "detay", "batch"),
        "gross": (
            "brüt",
            "brut",
            "brüt tutar",
            "brut tutar",
            "satış tutarı",
            "satis tutari",
            "toplam satış",
        ),
        "fee": (
            "komisyon",
            "kesinti",
            "ücret",
            "ucret",
            "masraf",
            "banka masrafı",
            "işlem ücreti",
        ),
        "net": (
            "net",
            "net tutar",
            "yatırılan",
            "yatirilan",
            "hesaba geçen",
            "hesaba gecen",
            "ödeme tutarı",
        ),
        "batch_reference": ("referans", "batch no", "işlem no", "islem no"),
    },
}

_SETTLEMENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "date": ("tarih", "date"),
    "description": ("açıklama", "aciklama", "description"),
    "gross": ("brüt", "brut", "gross", "satış", "satis"),
    "fee": ("komisyon", "kesinti", "fee", "ücret", "ucret", "masraf"),
    "net": ("net", "yatırılan", "yatirilan", "deposit"),
    "batch_reference": ("referans", "batch", "reference"),
}


def _alias_matches_header(low: str, alias: str) -> bool:
    a = alias.lower()
    return low == a or a in low.split()


def suggest_settlement_mapping(headers: list[str]) -> dict[str, str | None]:
    """Suggest column mapping for settlement imports from header row."""
    lower_map = {h: h.strip().lower() for h in headers}
    mapping: dict[str, str | None] = {f: None for f in SETTLEMENT_FIELDS}
    used: set[str] = set()
    for preset in SETTLEMENT_PRESETS.values():
        for field, aliases in preset.items():
            if mapping.get(field):
                continue
            for header, low in lower_map.items():
                if header in used:
                    continue
                if any(_alias_matches_header(low, a) for a in aliases):
                    mapping[field] = header
                    used.add(header)
                    break
    for field in SETTLEMENT_FIELDS:
        if mapping.get(field):
            continue
        keywords = _SETTLEMENT_KEYWORDS.get(field, ())
        for header, low in lower_map.items():
            if header in used:
                continue
            if any(kw in low for kw in keywords):
                mapping[field] = header
                used.add(header)
                break
    return mapping


def _parse_amount_cell(row: pd.Series, col: str | None) -> float | None:
    if not col:
        return None
    raw = _cell_raw(row, col)
    if raw is None:
        return None
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return round(abs(float(raw)), 2)
    val = parse_amount_str(_cell_str(row, col))
    if val is None:
        return None
    return round(abs(val), 2)


def parse_settlement_statement(
    file_bytes: bytes,
    filename: str,
    column_mapping: dict[str, str | None],
    *,
    currency: str = "TRY",
    header_row: int = 1,
    sheet_name: str | None = None,
) -> list[dict[str, Any]]:
    """Parse settlement rows into dicts ready for persistence."""
    df = _read_dataframe(
        file_bytes, filename, header_row=header_row, sheet_name=sheet_name
    )
    rows: list[dict[str, Any]] = []
    for idx in range(len(df)):
        row = df.iloc[idx]
        import_row_index = idx + 1
        desc = _cell_str(row, column_mapping.get("description"))
        batch_ref = _cell_str(row, column_mapping.get("batch_reference")) or None
        row_date = _parse_date(_cell_raw(row, column_mapping.get("date")))
        gross = _parse_amount_cell(row, column_mapping.get("gross"))
        fee = _parse_amount_cell(row, column_mapping.get("fee")) or 0.0
        net = _parse_amount_cell(row, column_mapping.get("net"))

        if net is None and gross is not None:
            net = round(gross - fee, 2)

        parsed_ok = (
            row_date is not None
            and gross is not None
            and gross > 0
            and net is not None
            and net > 0
            and abs((gross or 0) - fee - net) <= 0.02
        )
        parse_error = None
        if not parsed_ok:
            errs = []
            if row_date is None:
                errs.append("invalid_date")
            if gross is None or gross <= 0:
                errs.append("invalid_gross")
            if net is None or net <= 0:
                errs.append("invalid_net")
            if gross and net and abs(gross - fee - net) > 0.02:
                errs.append("gross_fee_net_mismatch")
            parse_error = ",".join(errs)

        rows.append(
            {
                "import_row_index": import_row_index,
                "date": row_date,
                "description": desc or batch_ref or "",
                "batch_reference": batch_ref,
                "gross_amount": gross or 0.0,
                "fee_amount": fee,
                "net_amount": net or 0.0,
                "currency": currency,
                "raw_line_text": _raw_line_from_row(row),
                "parsed_successfully": parsed_ok,
                "parse_error": parse_error,
                "status": "parse_error" if not parsed_ok else "staging",
            }
        )
    return rows


__all__ = [
    "SETTLEMENT_FIELDS",
    "mapping_to_json",
    "parse_settlement_statement",
    "read_tabular_preview",
    "suggest_settlement_mapping",
]
