import datetime
import datetime as _dt
import pandas as pd
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph, HRFlowable


def df_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output.read()


def df_to_pdf_bytes(df: pd.DataFrame, title: str = "Export") -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Heading2"]), Spacer(1, 12)]

    if df.empty:
        elements.append(Paragraph("No records available.", styles["BodyText"]))
    else:
        data = [list(df.columns)] + df.astype(str).values.tolist()
        table = Table(data, repeatRows=1, hAlign="LEFT")
        table_style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
        table.setStyle(table_style)
        elements.append(table)

    doc.build(elements)
    output.seek(0)
    return output.read()


def generate_invoice_pdf(
    invoice_number: str,
    invoice_date,
    due_date,
    customer_name: str,
    description: str,
    amount: float,
    paid_amount: float,
    status: str,
    currency: str = "TRY",
    company_name: str = "My Company",
) -> bytes:
    """Generate a clean one-page invoice PDF for a credit sale.

    Returns the PDF as bytes suitable for st.download_button.
    """
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    W = A4[0] - 40 * mm  # usable width

    h1 = ParagraphStyle("h1", fontSize=22, fontName="Helvetica-Bold", textColor=colors.HexColor("#1e3a8a"))
    h2 = ParagraphStyle("h2", fontSize=11, fontName="Helvetica-Bold", textColor=colors.HexColor("#1e40af"))
    body = ParagraphStyle("body", fontSize=9, fontName="Helvetica", textColor=colors.HexColor("#374151"))
    muted = ParagraphStyle("muted", fontSize=8, fontName="Helvetica", textColor=colors.HexColor("#9ca3af"))
    right = ParagraphStyle("right", fontSize=9, fontName="Helvetica", alignment=TA_RIGHT)
    big_right = ParagraphStyle("big_right", fontSize=14, fontName="Helvetica-Bold",
                                textColor=colors.HexColor("#1e3a8a"), alignment=TA_RIGHT)

    balance = max(round(amount - paid_amount, 2), 0.0)
    status_color = {
        "Paid": colors.HexColor("#065f46"),
        "Partial": colors.HexColor("#92400e"),
        "Overdue": colors.HexColor("#991b1b"),
    }.get(status, colors.HexColor("#1e40af"))

    # Format date safely
    def fmt(d):
        if isinstance(d, (datetime.date, datetime.datetime)):
            return d.strftime("%d %b %Y")
        return str(d) if d else "—"

    elements = [
        # Header row: company name left, INVOICE right
        Table(
            [[Paragraph(company_name, h1), Paragraph("INVOICE", h1)]],
            colWidths=[W * 0.6, W * 0.4],
            style=TableStyle([
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]),
        ),
        Spacer(1, 4 * mm),
        HRFlowable(width=W, thickness=1.5, color=colors.HexColor("#1e40af")),
        Spacer(1, 5 * mm),

        # Invoice meta + bill-to
        Table(
            [[
                Table(
                    [
                        [Paragraph("Invoice No.", muted), Paragraph(invoice_number, body)],
                        [Paragraph("Date", muted),        Paragraph(fmt(invoice_date), body)],
                        [Paragraph("Due Date", muted),    Paragraph(fmt(due_date), body)],
                        [Paragraph("Status", muted),
                         Paragraph(f'<font color="#{status_color.hexval()[2:]}"><b>{status}</b></font>', body)],
                    ],
                    colWidths=[22 * mm, W * 0.35],
                    style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]),
                ),
                Table(
                    [
                        [Paragraph("Bill To", h2)],
                        [Paragraph(customer_name, body)],
                    ],
                    colWidths=[W * 0.4],
                    style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]),
                ),
            ]],
            colWidths=[W * 0.55, W * 0.45],
            style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]),
        ),
        Spacer(1, 7 * mm),
        HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#e5e7eb")),
        Spacer(1, 4 * mm),

        # Line items table
        Table(
            [
                [Paragraph("Description", h2), Paragraph("Amount", h2)],
                [Paragraph(description or "Services / Goods", body),
                 Paragraph(f"{currency} {amount:,.2f}", right)],
            ],
            colWidths=[W * 0.7, W * 0.3],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#bfdbfe")),
                ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]),
        ),
        Spacer(1, 3 * mm),

        # Totals block (right-aligned)
        Table(
            [
                ["", Paragraph("Subtotal", right),    Paragraph(f"{currency} {amount:,.2f}", right)],
                ["", Paragraph("Paid", right),         Paragraph(f"{currency} {paid_amount:,.2f}", right)],
                ["", Paragraph("<b>Balance Due</b>", big_right),
                 Paragraph(f"<b>{currency} {balance:,.2f}</b>", big_right)],
            ],
            colWidths=[W * 0.45, W * 0.3, W * 0.25],
            style=TableStyle([
                ("LINEABOVE", (1, 2), (-1, 2), 1, colors.HexColor("#1e40af")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]),
        ),
        Spacer(1, 10 * mm),
        HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#e5e7eb")),
        Spacer(1, 3 * mm),
        Paragraph("Thank you for your business.", muted),
    ]

    doc.build(elements)
    output.seek(0)
    return output.read()


def generate_receipt_pdf(
    receipt_number: str,
    receipt_date,
    customer_name: str,
    description: str,
    amount: float,
    payment_method: str,
    currency: str = "TRY",
    company_name: str = "My Company",
) -> bytes:
    """Generate a one-page receipt PDF for a Cash or Card sale.

    Returns bytes suitable for st.download_button.
    Distinct from the invoice: no balance due, no due date — payment was received in full.
    """
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    W = A4[0] - 40 * mm

    h1        = ParagraphStyle("h1r",       fontSize=22, fontName="Helvetica-Bold",
                                textColor=colors.HexColor("#065f46"))
    h2        = ParagraphStyle("h2r",       fontSize=11, fontName="Helvetica-Bold",
                                textColor=colors.HexColor("#064e3b"))
    body      = ParagraphStyle("bodyr",     fontSize=9,  fontName="Helvetica",
                                textColor=colors.HexColor("#374151"))
    muted_r   = ParagraphStyle("mutedr",    fontSize=8,  fontName="Helvetica",
                                textColor=colors.HexColor("#9ca3af"))
    right_r   = ParagraphStyle("rightr",    fontSize=9,  fontName="Helvetica",
                                alignment=TA_RIGHT)
    big_right_r = ParagraphStyle("big_rightr", fontSize=14, fontName="Helvetica-Bold",
                                  textColor=colors.HexColor("#065f46"), alignment=TA_RIGHT)

    def fmt(d):
        if isinstance(d, (datetime.date, datetime.datetime)):
            return d.strftime("%d %b %Y")
        return str(d) if d else "—"

    elements = [
        Table(
            [[Paragraph(company_name, h1), Paragraph("RECEIPT", h1)]],
            colWidths=[W * 0.6, W * 0.4],
            style=TableStyle([
                ("ALIGN",  (1, 0), (1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]),
        ),
        Spacer(1, 4 * mm),
        HRFlowable(width=W, thickness=1.5, color=colors.HexColor("#065f46")),
        Spacer(1, 5 * mm),
        Table(
            [[
                Table(
                    [
                        [Paragraph("Receipt No.", muted_r), Paragraph(receipt_number, body)],
                        [Paragraph("Date",        muted_r), Paragraph(fmt(receipt_date), body)],
                        [Paragraph("Payment",     muted_r), Paragraph(payment_method, body)],
                    ],
                    colWidths=[22 * mm, W * 0.35],
                    style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]),
                ),
                Table(
                    [
                        [Paragraph("Received From", h2)],
                        [Paragraph(customer_name or "Walk-in Customer", body)],
                    ],
                    colWidths=[W * 0.4],
                    style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                      ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]),
                ),
            ]],
            colWidths=[W * 0.55, W * 0.45],
            style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]),
        ),
        Spacer(1, 7 * mm),
        HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#e5e7eb")),
        Spacer(1, 4 * mm),
        Table(
            [
                [Paragraph("Description", h2), Paragraph("Amount", h2)],
                [Paragraph(description or "Goods / Services", body),
                 Paragraph(f"{currency} {amount:,.2f}", right_r)],
            ],
            colWidths=[W * 0.7, W * 0.3],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecfdf5")),
                ("LINEBELOW",  (0, 0), (-1, 0), 0.5, colors.HexColor("#6ee7b7")),
                ("LINEBELOW",  (0, 1), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("ALIGN",      (1, 0), (1, -1), "RIGHT"),
                ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]),
        ),
        Spacer(1, 3 * mm),
        Table(
            [["", Paragraph("<b>Amount Paid</b>", big_right_r),
              Paragraph(f"<b>{currency} {amount:,.2f}</b>", big_right_r)]],
            colWidths=[W * 0.45, W * 0.3, W * 0.25],
            style=TableStyle([
                ("LINEABOVE",     (1, 0), (-1, 0), 1, colors.HexColor("#065f46")),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]),
        ),
        Spacer(1, 10 * mm),
        HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#e5e7eb")),
        Spacer(1, 3 * mm),
        Paragraph("Payment received in full — thank you.", muted_r),
    ]

    doc.build(elements)
    output.seek(0)
    return output.read()


def _fmt_date(d):
    """Format a date for statement PDFs."""
    if isinstance(d, (datetime.date, datetime.datetime)):
        return d.strftime("%d %b %Y")
    return str(d) if d else ""


def _fmt_amt(v):
    """Format a numeric amount for statement PDFs, returning '' for blank cells."""
    if v == "" or v is None:
        return ""
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return str(v)


def _stmt_common_styles(accent_hex: str):
    """Return (h1, h2, body, muted, right_body, right_bold) for statement PDFs."""
    h1 = ParagraphStyle("stmh1", fontSize=18, fontName="Helvetica-Bold",
                         textColor=colors.HexColor(accent_hex))
    h2 = ParagraphStyle("stmh2", fontSize=10, fontName="Helvetica-Bold",
                         textColor=colors.HexColor(accent_hex))
    body       = ParagraphStyle("stmbody", fontSize=8, fontName="Helvetica",
                                 textColor=colors.HexColor("#374151"))
    muted_s    = ParagraphStyle("stmmuted", fontSize=7, fontName="Helvetica",
                                 textColor=colors.HexColor("#9ca3af"))
    right_body = ParagraphStyle("stmrb", fontSize=8, fontName="Helvetica",
                                 alignment=TA_RIGHT, textColor=colors.HexColor("#374151"))
    right_bold = ParagraphStyle("stmrbd", fontSize=9, fontName="Helvetica-Bold",
                                 alignment=TA_RIGHT, textColor=colors.HexColor(accent_hex))
    return h1, h2, body, muted_s, right_body, right_bold


def _build_statement_doc(
    output, W, accent_hex, bg_hex, border_hex,
    header_label, name_label, name_value,
    start_date, end_date, opening_balance, closing_balance,
    currency, company_name, col_headers, lines,
):
    """Internal builder shared by customer and vendor statement PDFs."""
    h1, h2, body, muted_s, right_body, right_bold = _stmt_common_styles(accent_hex)

    header_tbl = Table(
        [[Paragraph(company_name, h1), Paragraph(header_label, h1)]],
        colWidths=[W * 0.55, W * 0.45],
        style=TableStyle([("ALIGN", (1, 0), (1, 0), "RIGHT"),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]),
    )
    meta_tbl = Table(
        [[
            Table(
                [
                    [Paragraph(name_label, muted_s), Paragraph(name_value, body)],
                    [Paragraph("Period", muted_s),
                     Paragraph(f"{_fmt_date(start_date)} – {_fmt_date(end_date)}", body)],
                    [Paragraph("Currency", muted_s), Paragraph(currency, body)],
                ],
                colWidths=[20 * mm, W * 0.45],
                style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]),
            ),
            Table(
                [
                    [Paragraph("Opening Balance", muted_s),
                     Paragraph(f"{currency} {opening_balance:,.2f}", right_body)],
                    [Paragraph("Closing Balance", muted_s),
                     Paragraph(f"<b>{currency} {closing_balance:,.2f}</b>", right_bold)],
                ],
                colWidths=[W * 0.22, W * 0.18],
                style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                                   ("ALIGN", (1, 0), (1, -1), "RIGHT")]),
            ),
        ]],
        colWidths=[W * 0.6, W * 0.4],
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]),
    )

    col_w = [W * 0.13, W * 0.13, W * 0.22, W * 0.17, W * 0.17, W * 0.18]
    debit_key, credit_key = col_headers  # e.g. ("Invoice", "Payment") or ("Purchases", "Payments")
    tbl_data = [
        [Paragraph("Date", h2), Paragraph("Type", h2), Paragraph("Reference", h2),
         Paragraph(f"{debit_key} ({currency})", h2),
         Paragraph(f"{credit_key} ({currency})", h2),
         Paragraph(f"Balance ({currency})", h2)],
        [Paragraph("Opening", body), Paragraph("Balance", body),
         Paragraph("", body), Paragraph("", body), Paragraph("", body),
         Paragraph(f"{opening_balance:,.2f}", right_body)],
    ]
    for ln in lines:
        dr  = ln.get(debit_key, "")
        cr  = ln.get(credit_key, "")
        bal = ln.get("Balance", "")
        tbl_data.append([
            Paragraph(_fmt_date(ln.get("Date", "")), body),
            Paragraph(str(ln.get("Type", "")), body),
            Paragraph(str(ln.get("Reference", "")), body),
            Paragraph(_fmt_amt(dr) if dr != "" else "", right_body),
            Paragraph(_fmt_amt(cr) if cr != "" else "", right_body),
            Paragraph(_fmt_amt(bal) if bal != "" else "", right_body),
        ])
    tbl_data.append([
        Paragraph("Closing", body), Paragraph("Balance", body),
        Paragraph("", body), Paragraph("", body), Paragraph("", body),
        Paragraph(f"<b>{closing_balance:,.2f}</b>", right_bold),
    ])

    txn_tbl = Table(tbl_data, colWidths=col_w, repeatRows=1)
    txn_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(bg_hex)),
        ("LINEBELOW",  (0, 0), (-1, 0), 0.5, colors.HexColor(border_hex)),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f9fafb")),
        ("LINEABOVE",  (0, -1), (-1, -1), 0.5, colors.HexColor(accent_hex)),
        ("GRID",       (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("ALIGN",      (3, 0), (-1, -1), "RIGHT"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
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
        txn_tbl,
        Spacer(1, 5 * mm),
        HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#e5e7eb")),
        Spacer(1, 3 * mm),
        ParagraphStyle  # placeholder — replaced below
    ]
    elements[-1] = Paragraph(
        f"Generated on {datetime.date.today().strftime('%d %b %Y')}. "
        "This document is for reference only.",
        ParagraphStyle("stmfooter", fontSize=7, fontName="Helvetica",
                       textColor=colors.HexColor("#9ca3af")),
    )

    from reportlab.platypus import SimpleDocTemplate as _SDT
    doc_obj = _SDT(output, pagesize=A4,
                   leftMargin=20 * mm, rightMargin=20 * mm,
                   topMargin=18 * mm, bottomMargin=18 * mm)
    doc_obj.build(elements)


def generate_customer_statement_pdf(
    customer_name: str,
    start_date,
    end_date,
    opening_balance: float,
    closing_balance: float,
    lines: list,
    currency: str = "TRY",
    company_name: str = "My Company",
) -> bytes:
    """Generate a customer AR statement PDF.

    lines: list of dicts with keys: Date, Type, Reference, Invoice, Payment, Balance.
    Invoice and Payment may be numeric or "" for empty cells.
    Returns bytes suitable for st.download_button.
    """
    output = BytesIO()
    W = A4[0] - 40 * mm
    _build_statement_doc(
        output, W,
        accent_hex="#1e40af", bg_hex="#eff6ff", border_hex="#bfdbfe",
        header_label="CUSTOMER STATEMENT",
        name_label="Customer", name_value=customer_name,
        start_date=start_date, end_date=end_date,
        opening_balance=opening_balance, closing_balance=closing_balance,
        currency=currency, company_name=company_name,
        col_headers=("Invoice", "Payment"),
        lines=lines,
    )
    output.seek(0)
    return output.read()


def generate_vendor_statement_pdf(
    vendor_name: str,
    start_date,
    end_date,
    opening_balance: float,
    closing_balance: float,
    lines: list,
    currency: str = "TRY",
    company_name: str = "My Company",
) -> bytes:
    """Generate a vendor AP statement PDF.

    lines: list of dicts with keys: Date, Type, Reference, Purchases, Payments, Balance.
    Purchases and Payments may be numeric or "" for empty cells.
    Returns bytes suitable for st.download_button.
    """
    output = BytesIO()
    W = A4[0] - 40 * mm
    _build_statement_doc(
        output, W,
        accent_hex="#7c3aed", bg_hex="#f5f3ff", border_hex="#ddd6fe",
        header_label="VENDOR STATEMENT",
        name_label="Vendor", name_value=vendor_name,
        start_date=start_date, end_date=end_date,
        opening_balance=opening_balance, closing_balance=closing_balance,
        currency=currency, company_name=company_name,
        col_headers=("Purchases", "Payments"),
        lines=lines,
    )
    output.seek(0)
    return output.read()
