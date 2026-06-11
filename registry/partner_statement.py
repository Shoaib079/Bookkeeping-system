"""PARTNER-STATEMENT-01 — read-only partner settlement statement helpers."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from models import (
    ChartOfAccounts,
    FiscalPeriod,
    Partner,
    PartnerMovement,
    PartnerProfitAllocation,
    PartnerProfitAllocationLine,
)

_PARTNER_STMT_EPOCH = datetime.date(1900, 1, 1)
_POSITION_TOLERANCE = 0.01

_INFLOW_MOVEMENTS = frozenset({"CapitalContribution", "Repayment"})
_OUTFLOW_MOVEMENTS = frozenset({"Drawing", "Salary", "Advance"})
_SETTLEMENT_MOVEMENTS = frozenset({"AdvanceOffset"})

_MOVEMENT_SECTION: dict[str, str] = {
    "CapitalContribution": "money_in",
    "Repayment": "money_in",
    "Drawing": "money_out",
    "Salary": "money_out",
    "Advance": "money_out",
    "AdvanceOffset": "settlements",
}

_SECTION_SORT = {"opening": 0, "money_in": 1, "money_out": 2, "settlements": 3, "closing": 4}

_TYPE_SORT = {
    "opening": 0,
    "CapitalContribution": 1,
    "ProfitAllocated": 2,
    "Repayment": 3,
    "Drawing": 4,
    "Salary": 5,
    "Advance": 6,
    "LossAllocated": 7,
    "AdvanceOffset": 8,
    "closing": 9,
}

BalanceForPeriodFn = Callable[
    ["object", ChartOfAccounts, datetime.date, datetime.date], float
]


@dataclass
class PartnerStatementWarning:
    key: str
    kwargs: dict = field(default_factory=dict)


@dataclass
class PartnerStatementDetailLine:
    line_date: datetime.date | None
    section_key: str
    type_key: str
    description: str
    reference: str
    gross_amount: float
    inflow: float
    outflow: float
    signed_amount: float
    net_effect: float
    running_position: float
    source_id: int | None = None


@dataclass
class PartnerStatementData:
    partner_id: int
    partner_name: str
    partner_is_active: bool
    from_date: datetime.date
    to_date: datetime.date
    opening_position: float
    opening_capital: float
    opening_current: float
    opening_advances: float
    capital_contributions: float
    profit_allocated: float
    repayments: float
    drawings: float
    salary: float
    advances_taken: float
    loss_allocated: float
    advance_offsets: float
    closing_position: float
    closing_capital: float
    closing_current: float
    closing_advances: float
    net_position_change: float
    status: str
    status_amount: float
    warnings: list[PartnerStatementWarning] = field(default_factory=list)
    reconciliation_ok: bool = True
    detail_lines: list[PartnerStatementDetailLine] = field(default_factory=list)


def partner_statement_preset_range(
    preset: str, today: datetime.date
) -> tuple[datetime.date, datetime.date] | tuple[None, None]:
    """Return (from_date, to_date) for month/quarter/year presets; (None, None) for custom."""
    if preset == "month":
        return today.replace(day=1), today
    if preset == "quarter":
        q_month = ((today.month - 1) // 3) * 3 + 1
        return datetime.date(today.year, q_month, 1), today
    if preset == "year":
        return datetime.date(today.year, 1, 1), today
    return None, None


def partner_position_from_balances(
    capital: float, current: float, advances: float
) -> float:
    """Position = capital + current − advances (advances reduce net partner claim)."""
    return round(capital + current - advances, 2)


def partner_position_status(position: float) -> tuple[str, float]:
    """Return (status_key, display_amount). Keys: company_owes | partner_owes | settled."""
    if position > _POSITION_TOLERANCE:
        return "company_owes", round(position, 2)
    if position < -_POSITION_TOLERANCE:
        return "partner_owes", round(abs(position), 2)
    return "settled", 0.0


def partner_statement_net_change(
    *,
    capital_contributions: float = 0.0,
    profit_allocated: float = 0.0,
    repayments: float = 0.0,
    drawings: float = 0.0,
    salary: float = 0.0,
    advances_taken: float = 0.0,
    loss_allocated: float = 0.0,
) -> float:
    """Net position delta for period activity (AdvanceOffset excluded — zero effect)."""
    return round(
        capital_contributions
        + profit_allocated
        + repayments
        - drawings
        - salary
        - advances_taken
        - loss_allocated,
        2,
    )


def advance_offset_position_delta(_amount: float) -> float:
    """AdvanceOffset: Dr Current / Cr Advances — net position unchanged."""
    return 0.0


def movement_net_position_effect(movement_type: str, amount: float) -> float:
    """Signed net position delta for a partner movement."""
    if movement_type == "CapitalContribution":
        return round(amount, 2)
    if movement_type == "Repayment":
        return round(amount, 2)
    if movement_type in ("Drawing", "Salary", "Advance"):
        return round(-amount, 2)
    if movement_type == "AdvanceOffset":
        return 0.0
    return 0.0


def _line_flow_amounts(gross_amount: float, net_effect: float) -> tuple[float, float, float]:
    gross = round(abs(gross_amount), 2)
    signed = round(net_effect, 2)
    if signed > 0:
        return gross, round(signed, 2), 0.0
    if signed < 0:
        return gross, 0.0, round(abs(signed), 2)
    return gross, 0.0, 0.0


def _allocation_lines_in_range(
    session, partner_id: int, from_date: datetime.date, to_date: datetime.date
):
    return (
        session.query(PartnerProfitAllocationLine, PartnerProfitAllocation, FiscalPeriod)
        .join(
            PartnerProfitAllocation,
            PartnerProfitAllocation.id == PartnerProfitAllocationLine.allocation_id,
        )
        .join(FiscalPeriod, FiscalPeriod.id == PartnerProfitAllocation.fiscal_period_id)
        .filter(
            PartnerProfitAllocationLine.partner_id == partner_id,
            PartnerProfitAllocation.is_void == False,
            FiscalPeriod.end_date >= from_date,
            FiscalPeriod.end_date <= to_date,
        )
        .all()
    )


def _collect_detail_events(
    session, partner_id: int, from_date: datetime.date, to_date: datetime.date
) -> list[dict]:
    events: list[dict] = []
    movements = (
        session.query(PartnerMovement)
        .filter(
            PartnerMovement.partner_id == partner_id,
            PartnerMovement.is_void == False,
            PartnerMovement.date >= from_date,
            PartnerMovement.date <= to_date,
        )
        .order_by(PartnerMovement.date, PartnerMovement.id)
        .all()
    )
    for mv in movements:
        net = movement_net_position_effect(mv.movement_type, mv.amount)
        ref_parts = [f"PartnerMovement #{mv.id}"]
        if mv.journal_entry_id:
            ref_parts.append(f"JE #{mv.journal_entry_id}")
        events.append(
            {
                "line_date": mv.date,
                "section_key": _MOVEMENT_SECTION.get(mv.movement_type, "money_out"),
                "type_key": mv.movement_type,
                "description": (mv.notes or "").strip() or mv.movement_type,
                "reference": " / ".join(ref_parts),
                "gross_amount": mv.amount,
                "net_effect": net,
                "source_id": mv.id,
            }
        )

    for line, alloc, fp in _allocation_lines_in_range(session, partner_id, from_date, to_date):
        amt = round(line.amount, 2)
        if amt > 0:
            type_key = "ProfitAllocated"
            section_key = "money_in"
        elif amt < 0:
            type_key = "LossAllocated"
            section_key = "money_out"
        else:
            continue
        ref_parts = [f"ProfitAllocation #{alloc.id}", fp.name]
        if alloc.journal_entry_id:
            ref_parts.append(f"JE #{alloc.journal_entry_id}")
        desc = f"Profit Allocation: {fp.name}"
        if alloc.notes and alloc.notes.strip():
            desc += f" — {alloc.notes.strip()}"
        events.append(
            {
                "line_date": fp.end_date,
                "section_key": section_key,
                "type_key": type_key,
                "description": desc,
                "reference": " / ".join(ref_parts),
                "gross_amount": abs(amt),
                "net_effect": amt,
                "source_id": line.id,
            }
        )
    return events


def build_partner_statement_detail_lines(
    opening_position: float,
    closing_position: float,
    opening_as_of: datetime.date,
    events: list[dict],
) -> list[PartnerStatementDetailLine]:
    """Build ordered detail lines with running position from opening through activity."""
    gross, inflow, outflow = _line_flow_amounts(0.0, 0.0)
    lines: list[PartnerStatementDetailLine] = [
        PartnerStatementDetailLine(
            line_date=opening_as_of,
            section_key="opening",
            type_key="opening",
            description="Opening position",
            reference="",
            gross_amount=gross,
            inflow=inflow,
            outflow=outflow,
            signed_amount=0.0,
            net_effect=0.0,
            running_position=round(opening_position, 2),
        )
    ]

    running = round(opening_position, 2)
    sorted_events = sorted(
        events,
        key=lambda e: (
            e["line_date"],
            _SECTION_SORT.get(e["section_key"], 9),
            _TYPE_SORT.get(e["type_key"], 99),
            e.get("source_id") or 0,
        ),
    )
    for ev in sorted_events:
        gross, inflow, outflow = _line_flow_amounts(ev["gross_amount"], ev["net_effect"])
        running = round(running + ev["net_effect"], 2)
        lines.append(
            PartnerStatementDetailLine(
                line_date=ev["line_date"],
                section_key=ev["section_key"],
                type_key=ev["type_key"],
                description=ev["description"],
                reference=ev["reference"],
                gross_amount=gross,
                inflow=inflow,
                outflow=outflow,
                signed_amount=round(ev["net_effect"], 2),
                net_effect=round(ev["net_effect"], 2),
                running_position=running,
                source_id=ev.get("source_id"),
            )
        )

    gross, inflow, outflow = _line_flow_amounts(0.0, 0.0)
    lines.append(
        PartnerStatementDetailLine(
            line_date=None,
            section_key="closing",
            type_key="closing",
            description="Closing position",
            reference="",
            gross_amount=gross,
            inflow=inflow,
            outflow=outflow,
            signed_amount=0.0,
            net_effect=0.0,
            running_position=round(closing_position, 2),
        )
    )
    return lines


def partner_statement_summary_export_rows(stmt: PartnerStatementData) -> list[dict[str, object]]:
    """Summary rows for Excel export (stable English keys for tests)."""
    return [
        {"Section": "Opening", "Line": "Opening position", "Amount": stmt.opening_position},
        {"Section": "Money in", "Line": "Capital Contributions", "Amount": stmt.capital_contributions},
        {"Section": "Money in", "Line": "Profit Allocated", "Amount": stmt.profit_allocated},
        {"Section": "Money in", "Line": "Repayments", "Amount": stmt.repayments},
        {"Section": "Money out", "Line": "Drawings", "Amount": stmt.drawings},
        {"Section": "Money out", "Line": "Salary / Partner Takeout", "Amount": stmt.salary},
        {"Section": "Money out", "Line": "Advances Taken", "Amount": stmt.advances_taken},
        {"Section": "Money out", "Line": "Loss Allocated", "Amount": stmt.loss_allocated},
        {"Section": "Settlements", "Line": "Advance Offsets", "Amount": stmt.advance_offsets},
        {"Section": "Closing", "Line": "Closing position", "Amount": stmt.closing_position},
    ]


def partner_statement_detail_export_rows(
    detail_lines: list[PartnerStatementDetailLine],
) -> list[dict[str, object]]:
    """Detail rows for Excel export (stable English keys for tests)."""
    rows: list[dict[str, object]] = []
    for ln in detail_lines:
        rows.append(
            {
                "Date": ln.line_date.isoformat() if ln.line_date else "",
                "Section": ln.section_key,
                "Type": ln.type_key,
                "Description": ln.description,
                "Reference": ln.reference,
                "Inflow": ln.inflow,
                "Outflow": ln.outflow,
                "Signed Amount": ln.signed_amount,
                "Net Effect": ln.net_effect,
                "Running Position": ln.running_position,
            }
        )
    return rows


def partner_statement_to_export_df(stmt: PartnerStatementData) -> pd.DataFrame:
    """Single-sheet export: summary block, blank row, then detail lines."""
    summary = partner_statement_summary_export_rows(stmt)
    detail = partner_statement_detail_export_rows(stmt.detail_lines)
    df_summary = pd.DataFrame(summary)
    df_detail = pd.DataFrame(detail)
    if df_detail.empty:
        return df_summary
    blank = pd.DataFrame([{"Section": "", "Line": "", "Amount": ""}])
    detail_header = pd.DataFrame(
        [{"Section": "— Detail lines —", "Line": "", "Amount": ""}]
    )
    return pd.concat([df_summary, blank, detail_header, df_detail], ignore_index=True)


def partner_statement_pdf_payload(
    stmt: PartnerStatementData,
    *,
    company_name: str,
    currency: str,
    generated_date: datetime.date | None = None,
    status_text: str = "",
    warning_texts: list[str] | None = None,
) -> dict[str, object]:
    """Structured payload for generate_partner_statement_pdf (P3)."""
    return {
        "company_name": company_name,
        "currency": currency,
        "partner_name": stmt.partner_name,
        "from_date": stmt.from_date,
        "to_date": stmt.to_date,
        "generated_date": generated_date or datetime.date.today(),
        "opening_position": stmt.opening_position,
        "closing_position": stmt.closing_position,
        "summary_rows": partner_statement_summary_export_rows(stmt),
        "status_text": status_text,
        "warnings": list(warning_texts or []),
        "detail_rows": partner_statement_detail_export_rows(stmt.detail_lines),
    }


def check_partner_statement_reconciliation(
    opening_position: float,
    net_change: float,
    closing_position: float,
    tolerance: float = _POSITION_TOLERANCE,
) -> bool:
    return abs(opening_position + net_change - closing_position) <= tolerance


def _partner_balances_as_of(
    session,
    partner: Partner,
    as_of: datetime.date,
    balance_for_period: BalanceForPeriodFn,
) -> tuple[float, float, float]:
    cap_acct = (
        session.get(ChartOfAccounts, partner.capital_account_id)
        if partner.capital_account_id
        else None
    )
    cur_acct = (
        session.get(ChartOfAccounts, partner.current_account_id)
        if partner.current_account_id
        else None
    )
    adv_acct = (
        session.get(ChartOfAccounts, partner.advance_account_id)
        if partner.advance_account_id
        else None
    )
    cap = (
        balance_for_period(session, cap_acct, _PARTNER_STMT_EPOCH, as_of)
        if cap_acct
        else 0.0
    )
    cur = (
        balance_for_period(session, cur_acct, _PARTNER_STMT_EPOCH, as_of)
        if cur_acct
        else 0.0
    )
    adv = (
        balance_for_period(session, adv_acct, _PARTNER_STMT_EPOCH, as_of)
        if adv_acct
        else 0.0
    )
    return round(cap, 2), round(cur, 2), round(adv, 2)


def _movement_totals(session, partner_id: int, from_date: datetime.date, to_date: datetime.date):
    totals = {
        "CapitalContribution": 0.0,
        "Drawing": 0.0,
        "Salary": 0.0,
        "Advance": 0.0,
        "Repayment": 0.0,
        "AdvanceOffset": 0.0,
    }
    movements = (
        session.query(PartnerMovement)
        .filter(
            PartnerMovement.partner_id == partner_id,
            PartnerMovement.is_void == False,
            PartnerMovement.date >= from_date,
            PartnerMovement.date <= to_date,
        )
        .all()
    )
    for mv in movements:
        if mv.movement_type in totals:
            totals[mv.movement_type] += mv.amount
    return {k: round(v, 2) for k, v in totals.items()}


def _allocation_totals(
    session, partner_id: int, from_date: datetime.date, to_date: datetime.date
) -> tuple[float, float]:
    """Profit/loss allocated by fiscal period end_date in range (not JE posting date)."""
    profit, loss = 0.0, 0.0
    rows = (
        session.query(PartnerProfitAllocationLine, FiscalPeriod)
        .join(
            PartnerProfitAllocation,
            PartnerProfitAllocation.id == PartnerProfitAllocationLine.allocation_id,
        )
        .join(FiscalPeriod, FiscalPeriod.id == PartnerProfitAllocation.fiscal_period_id)
        .filter(
            PartnerProfitAllocationLine.partner_id == partner_id,
            PartnerProfitAllocation.is_void == False,
            FiscalPeriod.end_date >= from_date,
            FiscalPeriod.end_date <= to_date,
        )
        .all()
    )
    for line, _fp in rows:
        amt = round(line.amount, 2)
        if amt > 0:
            profit += amt
        elif amt < 0:
            loss += abs(amt)
    return round(profit, 2), round(loss, 2)


def _closed_periods_without_allocation(
    session, from_date: datetime.date, to_date: datetime.date
) -> list[FiscalPeriod]:
    missing: list[FiscalPeriod] = []
    periods = (
        session.query(FiscalPeriod)
        .filter(
            FiscalPeriod.is_closed == True,
            FiscalPeriod.end_date >= from_date,
            FiscalPeriod.end_date <= to_date,
        )
        .order_by(FiscalPeriod.end_date)
        .all()
    )
    for fp in periods:
        alloc = (
            session.query(PartnerProfitAllocation)
            .filter_by(fiscal_period_id=fp.id, is_void=False)
            .first()
        )
        if not alloc:
            missing.append(fp)
    return missing


def build_partner_statement(
    session,
    partner_id: int,
    from_date: datetime.date,
    to_date: datetime.date,
    balance_for_period: BalanceForPeriodFn,
) -> PartnerStatementData | None:
    partner = session.get(Partner, partner_id)
    if not partner:
        return None

    opening_as_of = from_date - datetime.timedelta(days=1)
    o_cap, o_cur, o_adv = _partner_balances_as_of(
        session, partner, opening_as_of, balance_for_period
    )
    opening_pos = partner_position_from_balances(o_cap, o_cur, o_adv)

    c_cap, c_cur, c_adv = _partner_balances_as_of(
        session, partner, to_date, balance_for_period
    )
    closing_pos = partner_position_from_balances(c_cap, c_cur, c_adv)

    mv = _movement_totals(session, partner_id, from_date, to_date)
    profit_alloc, loss_alloc = _allocation_totals(session, partner_id, from_date, to_date)

    net_change = partner_statement_net_change(
        capital_contributions=mv["CapitalContribution"],
        profit_allocated=profit_alloc,
        repayments=mv["Repayment"],
        drawings=mv["Drawing"],
        salary=mv["Salary"],
        advances_taken=mv["Advance"],
        loss_allocated=loss_alloc,
    )

    status, status_amt = partner_position_status(closing_pos)
    recon_ok = check_partner_statement_reconciliation(opening_pos, net_change, closing_pos)

    warnings: list[PartnerStatementWarning] = []
    if c_adv > _POSITION_TOLERANCE:
        warnings.append(
            PartnerStatementWarning(
                "partner.stmt.warn_outstanding_advance",
                {"amount": c_adv},
            )
        )
    for fp in _closed_periods_without_allocation(session, from_date, to_date):
        warnings.append(
            PartnerStatementWarning(
                "partner.stmt.warn_closed_period_no_alloc",
                {"period": fp.name},
            )
        )
    if not recon_ok:
        warnings.append(
            PartnerStatementWarning(
                "partner.stmt.warn_reconciliation",
                {
                    "opening": opening_pos,
                    "change": net_change,
                    "closing": closing_pos,
                },
            )
        )

    events = _collect_detail_events(session, partner_id, from_date, to_date)
    detail_lines = build_partner_statement_detail_lines(
        opening_pos, closing_pos, opening_as_of, events
    )

    return PartnerStatementData(
        partner_id=partner.id,
        partner_name=partner.name,
        partner_is_active=partner.is_active,
        from_date=from_date,
        to_date=to_date,
        opening_position=opening_pos,
        opening_capital=o_cap,
        opening_current=o_cur,
        opening_advances=o_adv,
        capital_contributions=mv["CapitalContribution"],
        profit_allocated=profit_alloc,
        repayments=mv["Repayment"],
        drawings=mv["Drawing"],
        salary=mv["Salary"],
        advances_taken=mv["Advance"],
        loss_allocated=loss_alloc,
        advance_offsets=mv["AdvanceOffset"],
        closing_position=closing_pos,
        closing_capital=c_cap,
        closing_current=c_cur,
        closing_advances=c_adv,
        net_position_change=net_change,
        status=status,
        status_amount=status_amt,
        warnings=warnings,
        reconciliation_ok=recon_ok,
        detail_lines=detail_lines,
    )
