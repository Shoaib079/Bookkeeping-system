"""PARTNER-STATEMENT-01 P3 — Partner Statement PDF export."""

from __future__ import annotations

import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _fmt_date(d):
    if isinstance(d, (datetime.date, datetime.datetime)):
        return d.strftime("%d %b %Y")
    if isinstance(d, str) and d:
        try:
            return datetime.date.fromisoformat(d[:10]).strftime("%d %b %Y")
        except ValueError:
            return d
    return str(d) if d else ""


def _fmt_amt(v):
    if v == "" or v is None:
        return ""
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return str(v)


def _stmt_common_styles(accent_hex: str):
    h1 = ParagraphStyle(
        "psh1", fontSize=18, fontName="Helvetica-Bold",
        textColor=colors.HexColor(accent_hex),
    )
    h2 = ParagraphStyle(
        "psh2", fontSize=10, fontName="Helvetica-Bold",
        textColor=colors.HexColor(accent_hex),
    )
    body = ParagraphStyle(
        "psbody", fontSize=8, fontName="Helvetica",
        textColor=colors.HexColor("#374151"),
    )
    muted_s = ParagraphStyle(
        "psmuted", fontSize=7, fontName="Helvetica",
        textColor=colors.HexColor("#9ca3af"),
    )
    right_body = ParagraphStyle(
        "psrb", fontSize=8, fontName="Helvetica",
        alignment=TA_RIGHT, textColor=colors.HexColor("#374151"),
    )
    right_bold = ParagraphStyle(
        "psrbd", fontSize=9, fontName="Helvetica-Bold",
        alignment=TA_RIGHT, textColor=colors.HexColor(accent_hex),
    )
    return h1, h2, body, muted_s, right_body, right_bold


def generate_partner_statement_pdf(payload: dict) -> bytes:
    """Generate a partner settlement statement PDF from partner_statement_pdf_payload."""
    output = BytesIO()
    W = A4[0] - 40 * mm
    accent_hex = "#0f766e"
    h1, h2, body, muted_s, right_body, right_bold = _stmt_common_styles(accent_hex)
    warn_style = ParagraphStyle(
        "pswarn", fontSize=7, fontName="Helvetica",
        textColor=colors.HexColor("#92400e"),
    )
    footer_style = ParagraphStyle(
        "psfooter", fontSize=7, fontName="Helvetica",
        textColor=colors.HexColor("#9ca3af"),
    )

    company_name = str(payload.get("company_name", ""))
    currency = str(payload.get("currency", ""))
    partner_name = str(payload.get("partner_name", ""))
    from_date = payload.get("from_date")
    to_date = payload.get("to_date")
    generated_date = payload.get("generated_date", datetime.date.today())
    opening_position = float(payload.get("opening_position", 0.0))
    closing_position = float(payload.get("closing_position", 0.0))
    summary_rows = payload.get("summary_rows") or []
    detail_rows = payload.get("detail_rows") or []
    status_text = str(payload.get("status_text", "") or "")
    warnings = payload.get("warnings") or []

    header_tbl = Table(
        [[Paragraph(company_name, h1), Paragraph("PARTNER STATEMENT", h1)]],
        colWidths=[W * 0.55, W * 0.45],
        style=TableStyle([
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]),
    )
    meta_tbl = Table(
        [[
            Table(
                [
                    [Paragraph("Partner", muted_s), Paragraph(partner_name, body)],
                    [Paragraph("Period", muted_s),
                     Paragraph(f"{_fmt_date(from_date)} – {_fmt_date(to_date)}", body)],
                    [Paragraph("Generated", muted_s), Paragraph(_fmt_date(generated_date), body)],
                    [Paragraph("Currency", muted_s), Paragraph(currency, body)],
                ],
                colWidths=[22 * mm, W * 0.43],
                style=TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]),
            ),
            Table(
                [
                    [Paragraph("Opening Position", muted_s),
                     Paragraph(f"{currency} {opening_position:,.2f}", right_body)],
                    [Paragraph("Closing Position", muted_s),
                     Paragraph(f"<b>{currency} {closing_position:,.2f}</b>", right_bold)],
                ],
                colWidths=[W * 0.22, W * 0.18],
                style=TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ]),
            ),
        ]],
        colWidths=[W * 0.6, W * 0.4],
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]),
    )

    summary_data = [
        [Paragraph("Section", h2), Paragraph("Line", h2),
         Paragraph(f"Amount ({currency})", h2)],
    ]
    for row in summary_rows:
        summary_data.append([
            Paragraph(str(row.get("Section", "")), body),
            Paragraph(str(row.get("Line", "")), body),
            Paragraph(_fmt_amt(row.get("Amount", "")), right_body),
        ])
    summary_tbl = Table(summary_data, colWidths=[W * 0.22, W * 0.48, W * 0.30])
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecfdf5")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#6ee7b7")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    elements = [
        header_tbl,
        Spacer(1, 4 * mm),
        HRFlowable(width=W, thickness=1.5, color=colors.HexColor(accent_hex)),
        Spacer(1, 4 * mm),
        meta_tbl,
        Spacer(1, 5 * mm),
        HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#e5e7eb")),
        Spacer(1, 3 * mm),
        Paragraph("Summary", h2),
        Spacer(1, 2 * mm),
        summary_tbl,
        Spacer(1, 4 * mm),
    ]

    if status_text:
        elements.extend([
            Paragraph("Status", h2),
            Spacer(1, 2 * mm),
            Paragraph(status_text, body),
            Spacer(1, 3 * mm),
        ])

    if warnings:
        elements.append(Paragraph("Warnings", h2))
        elements.append(Spacer(1, 2 * mm))
        for w in warnings:
            elements.append(Paragraph(f"• {w}", warn_style))
            elements.append(Spacer(1, 1 * mm))
        elements.append(Spacer(1, 2 * mm))

    if detail_rows:
        detail_data = [[
            Paragraph("Date", h2), Paragraph("Section", h2), Paragraph("Type", h2),
            Paragraph("Description", h2), Paragraph("Reference", h2),
            Paragraph("In", h2), Paragraph("Out", h2),
            Paragraph("Net", h2), Paragraph("Running", h2),
        ]]
        for row in detail_rows:
            detail_data.append([
                Paragraph(_fmt_date(row.get("Date", "")), body),
                Paragraph(str(row.get("Section", "")), body),
                Paragraph(str(row.get("Type", "")), body),
                Paragraph(str(row.get("Description", ""))[:60], body),
                Paragraph(str(row.get("Reference", ""))[:40], body),
                Paragraph(_fmt_amt(row.get("Inflow", "")), right_body),
                Paragraph(_fmt_amt(row.get("Outflow", "")), right_body),
                Paragraph(_fmt_amt(row.get("Net Effect", "")), right_body),
                Paragraph(_fmt_amt(row.get("Running Position", "")), right_body),
            ])
        col_w = [W * 0.09, W * 0.10, W * 0.10, W * 0.18, W * 0.14,
                 W * 0.08, W * 0.08, W * 0.08, W * 0.10]
        detail_tbl = Table(detail_data, colWidths=col_w, repeatRows=1)
        detail_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecfdf5")),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#6ee7b7")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ("ALIGN", (5, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
        ]))
        elements.extend([
            HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#e5e7eb")),
            Spacer(1, 3 * mm),
            Paragraph("Detail Lines", h2),
            Spacer(1, 2 * mm),
            detail_tbl,
            Spacer(1, 4 * mm),
        ])

    elements.extend([
        HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#e5e7eb")),
        Spacer(1, 3 * mm),
        Paragraph(
            f"Generated on {_fmt_date(generated_date)}. This document is for reference only.",
            footer_style,
        ),
    ])

    doc = SimpleDocTemplate(
        output, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    doc.build(elements)
    output.seek(0)
    return output.read()
