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
class PartnerAccountBreakdown:
    """Capital / current / advances balances and derived net position."""

    capital: float
    current: float
    advances: float
    net_position: float


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
    company_id: int | None = None


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


def partner_account_breakdown(
    capital: float, current: float, advances: float
) -> PartnerAccountBreakdown:
    """Build labeled account balances with net position derived from the formula."""
    cap = round(capital, 2)
    cur = round(current, 2)
    adv = round(advances, 2)
    return PartnerAccountBreakdown(
        capital=cap,
        current=cur,
        advances=adv,
        net_position=partner_position_from_balances(cap, cur, adv),
    )


def check_partner_account_breakdown(
    capital: float,
    current: float,
    advances: float,
    position: float,
    tolerance: float = _POSITION_TOLERANCE,
) -> bool:
    """True when capital + current − advances equals the stored position."""
    return (
        abs(partner_position_from_balances(capital, current, advances) - position)
        <= tolerance
    )


def partner_statement_opening_breakdown(stmt: PartnerStatementData) -> PartnerAccountBreakdown:
    return partner_account_breakdown(
        stmt.opening_capital, stmt.opening_current, stmt.opening_advances
    )


def partner_statement_closing_breakdown(stmt: PartnerStatementData) -> PartnerAccountBreakdown:
    return partner_account_breakdown(
        stmt.closing_capital, stmt.closing_current, stmt.closing_advances
    )


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
    session,
    partner_id: int,
    from_date: datetime.date,
    to_date: datetime.date,
    *,
    company_id: int | None = None,
):
    q = (
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
    )
    if company_id is not None:
        q = q.filter(
            PartnerProfitAllocation.company_id == company_id,
            FiscalPeriod.company_id == company_id,
        )
    return q.all()


def _collect_detail_events(
    session,
    partner_id: int,
    from_date: datetime.date,
    to_date: datetime.date,
    *,
    company_id: int | None = None,
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

    for line, alloc, fp in _allocation_lines_in_range(
        session, partner_id, from_date, to_date, company_id=company_id
    ):
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


def partner_statement_account_breakdown_export_rows(
    stmt: PartnerStatementData,
) -> list[dict[str, object]]:
    """Opening/closing account balances for export (stable English keys for tests)."""
    return [
        {"Section": "Opening accounts", "Line": "Capital", "Amount": stmt.opening_capital},
        {
            "Section": "Opening accounts",
            "Line": "Current account",
            "Amount": stmt.opening_current,
        },
        {"Section": "Opening accounts", "Line": "Advances", "Amount": stmt.opening_advances},
        {
            "Section": "Opening accounts",
            "Line": "Net partner position",
            "Amount": stmt.opening_position,
        },
        {"Section": "Closing accounts", "Line": "Capital", "Amount": stmt.closing_capital},
        {
            "Section": "Closing accounts",
            "Line": "Current account",
            "Amount": stmt.closing_current,
        },
        {"Section": "Closing accounts", "Line": "Advances", "Amount": stmt.closing_advances},
        {
            "Section": "Closing accounts",
            "Line": "Net partner position",
            "Amount": stmt.closing_position,
        },
    ]


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
    """Single-sheet export: summary, account breakdown, blank, then detail lines."""
    summary = partner_statement_summary_export_rows(stmt)
    breakdown = partner_statement_account_breakdown_export_rows(stmt)
    detail = partner_statement_detail_export_rows(stmt.detail_lines)
    df_summary = pd.DataFrame(summary)
    df_breakdown = pd.DataFrame(breakdown)
    blank = pd.DataFrame([{"Section": "", "Line": "", "Amount": ""}])
    breakdown_header = pd.DataFrame(
        [{"Section": "— Account balances —", "Line": "", "Amount": ""}]
    )
    detail_header = pd.DataFrame(
        [{"Section": "— Detail lines —", "Line": "", "Amount": ""}]
    )
    parts = [df_summary, blank, breakdown_header, df_breakdown]
    if detail:
        df_detail = pd.DataFrame(detail)
        parts.extend([blank, detail_header, df_detail])
    return pd.concat(parts, ignore_index=True)


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
        "account_breakdown_rows": partner_statement_account_breakdown_export_rows(stmt),
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
    session,
    partner_id: int,
    from_date: datetime.date,
    to_date: datetime.date,
    *,
    company_id: int | None = None,
) -> tuple[float, float]:
    """Profit/loss allocated by fiscal period end_date in range (not JE posting date)."""
    profit, loss = 0.0, 0.0
    q = (
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
    )
    if company_id is not None:
        q = q.filter(
            PartnerProfitAllocation.company_id == company_id,
            FiscalPeriod.company_id == company_id,
        )
    rows = q.all()
    for line, _fp in rows:
        amt = round(line.amount, 2)
        if amt > 0:
            profit += amt
        elif amt < 0:
            loss += abs(amt)
    return round(profit, 2), round(loss, 2)


def _closed_periods_without_allocation(
    session,
    from_date: datetime.date,
    to_date: datetime.date,
    *,
    company_id: int | None = None,
) -> list[FiscalPeriod]:
    missing: list[FiscalPeriod] = []
    q = (
        session.query(FiscalPeriod)
        .filter(
            FiscalPeriod.is_closed == True,
            FiscalPeriod.end_date >= from_date,
            FiscalPeriod.end_date <= to_date,
        )
    )
    if company_id is not None:
        q = q.filter(FiscalPeriod.company_id == company_id)
    periods = q.order_by(FiscalPeriod.end_date).all()
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
    *,
    company_id: int | None = None,
) -> PartnerStatementData | None:
    partner = session.get(Partner, partner_id)
    if not partner:
        return None
    if company_id is not None and partner.company_id != company_id:
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
    profit_alloc, loss_alloc = _allocation_totals(
        session, partner_id, from_date, to_date, company_id=company_id
    )

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
    for fp in _closed_periods_without_allocation(
        session, from_date, to_date, company_id=company_id
    ):
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

    events = _collect_detail_events(
        session, partner_id, from_date, to_date, company_id=company_id
    )
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
        company_id=company_id,
    )


@dataclass
class AllPartnersSettlementRow:
    partner_id: int
    partner_name: str
    partner_is_active: bool
    profit_share_pct: float
    opening_position: float
    capital_contributions: float
    profit_allocated: float
    repayments: float
    drawings: float
    salary: float
    advances_taken: float
    loss_allocated: float
    advance_offsets: float
    net_position_change: float
    closing_position: float
    settlement_status: str
    status_amount: float
    closing_advances: float
    warning_flags: list[str]
    reconciliation_ok: bool


@dataclass
class AllPartnersSettlementFooter:
    total_opening_position: float
    total_capital_contributions: float
    total_profit_allocated: float
    total_repayments: float
    total_drawings: float
    total_salary: float
    total_advances_taken: float
    total_loss_allocated: float
    total_advance_offsets: float
    total_net_position_change: float
    total_closing_position: float
    total_outstanding_advances: float
    count_settled: int
    count_company_owes: int
    count_partner_owes: int
    count_with_warnings: int


@dataclass
class AllPartnersSettlementSummary:
    from_date: datetime.date
    to_date: datetime.date
    rows: list[AllPartnersSettlementRow]
    footer: AllPartnersSettlementFooter
    statements_by_partner_id: dict[int, PartnerStatementData]
    company_id: int | None = None


def _warning_flags_from_statement(stmt: PartnerStatementData) -> list[str]:
    flags: list[str] = []
    if not stmt.reconciliation_ok:
        flags.append("reconciliation")
    if stmt.closing_advances > _POSITION_TOLERANCE:
        flags.append("outstanding_advance")
    for warn in stmt.warnings:
        if warn.key == "partner.stmt.warn_closed_period_no_alloc":
            flags.append("closed_period_no_alloc")
            break
    return flags


def _is_fully_settled_statement(stmt: PartnerStatementData) -> bool:
    if abs(stmt.closing_position) > _POSITION_TOLERANCE:
        return False
    if abs(stmt.net_position_change) > _POSITION_TOLERANCE:
        return False
    activity = (
        stmt.capital_contributions
        + stmt.profit_allocated
        + stmt.repayments
        + stmt.drawings
        + stmt.salary
        + stmt.advances_taken
        + stmt.loss_allocated
        + stmt.advance_offsets
    )
    return abs(activity) <= _POSITION_TOLERANCE


def _row_from_partner_statement(
    stmt: PartnerStatementData, *, profit_share_pct: float
) -> AllPartnersSettlementRow:
    return AllPartnersSettlementRow(
        partner_id=stmt.partner_id,
        partner_name=stmt.partner_name,
        partner_is_active=stmt.partner_is_active,
        profit_share_pct=profit_share_pct,
        opening_position=stmt.opening_position,
        capital_contributions=stmt.capital_contributions,
        profit_allocated=stmt.profit_allocated,
        repayments=stmt.repayments,
        drawings=stmt.drawings,
        salary=stmt.salary,
        advances_taken=stmt.advances_taken,
        loss_allocated=stmt.loss_allocated,
        advance_offsets=stmt.advance_offsets,
        net_position_change=stmt.net_position_change,
        closing_position=stmt.closing_position,
        settlement_status=stmt.status,
        status_amount=stmt.status_amount,
        closing_advances=stmt.closing_advances,
        warning_flags=_warning_flags_from_statement(stmt),
        reconciliation_ok=stmt.reconciliation_ok,
    )


def _footer_from_rows(rows: list[AllPartnersSettlementRow]) -> AllPartnersSettlementFooter:
    return AllPartnersSettlementFooter(
        total_opening_position=round(sum(r.opening_position for r in rows), 2),
        total_capital_contributions=round(
            sum(r.capital_contributions for r in rows), 2
        ),
        total_profit_allocated=round(sum(r.profit_allocated for r in rows), 2),
        total_repayments=round(sum(r.repayments for r in rows), 2),
        total_drawings=round(sum(r.drawings for r in rows), 2),
        total_salary=round(sum(r.salary for r in rows), 2),
        total_advances_taken=round(sum(r.advances_taken for r in rows), 2),
        total_loss_allocated=round(sum(r.loss_allocated for r in rows), 2),
        total_advance_offsets=round(sum(r.advance_offsets for r in rows), 2),
        total_net_position_change=round(sum(r.net_position_change for r in rows), 2),
        total_closing_position=round(sum(r.closing_position for r in rows), 2),
        total_outstanding_advances=round(sum(r.closing_advances for r in rows), 2),
        count_settled=sum(1 for r in rows if r.settlement_status == "settled"),
        count_company_owes=sum(
            1 for r in rows if r.settlement_status == "company_owes"
        ),
        count_partner_owes=sum(
            1 for r in rows if r.settlement_status == "partner_owes"
        ),
        count_with_warnings=sum(1 for r in rows if r.warning_flags),
    )


def build_all_partners_settlement_summary(
    session,
    from_date: datetime.date,
    to_date: datetime.date,
    balance_for_period: BalanceForPeriodFn,
    *,
    company_id: int | None = None,
    include_inactive: bool = True,
    hide_settled: bool = False,
) -> AllPartnersSettlementSummary | None:
    """P4 rollup — one build_partner_statement call per partner (no parallel math)."""
    q = session.query(Partner).order_by(
        Partner.is_active.desc(), Partner.name, Partner.id
    )
    if company_id is not None:
        q = q.filter(Partner.company_id == company_id)
    partners = q.all()
    if not partners:
        return None

    statements_by_partner_id: dict[int, PartnerStatementData] = {}
    all_rows: list[AllPartnersSettlementRow] = []

    for partner in partners:
        stmt = build_partner_statement(
            session,
            partner.id,
            from_date,
            to_date,
            balance_for_period,
            company_id=company_id,
        )
        if not stmt:
            continue
        statements_by_partner_id[partner.id] = stmt
        if not include_inactive and not partner.is_active:
            continue
        if hide_settled and _is_fully_settled_statement(stmt):
            continue
        all_rows.append(
            _row_from_partner_statement(stmt, profit_share_pct=partner.profit_share_pct)
        )

    footer = _footer_from_rows(all_rows)
    return AllPartnersSettlementSummary(
        from_date=from_date,
        to_date=to_date,
        rows=all_rows,
        footer=footer,
        statements_by_partner_id=statements_by_partner_id,
        company_id=company_id,
    )


def all_partners_settlement_export_rows(
    summary: AllPartnersSettlementSummary,
) -> list[dict[str, object]]:
    """Stable English keys for Excel/CSV export (P4)."""
    rows: list[dict[str, object]] = []
    for r in summary.rows:
        rows.append(
            {
                "Partner": r.partner_name,
                "Active": "Yes" if r.partner_is_active else "No",
                "Share %": r.profit_share_pct,
                "Opening position": r.opening_position,
                "Capital contributions": r.capital_contributions,
                "Profit allocated": r.profit_allocated,
                "Repayments": r.repayments,
                "Drawings": r.drawings,
                "Salary / takeout": r.salary,
                "Advances taken": r.advances_taken,
                "Loss allocated": r.loss_allocated,
                "Advance offsets": r.advance_offsets,
                "Net position change": r.net_position_change,
                "Closing position": r.closing_position,
                "Settlement status": r.settlement_status,
                "Status amount": r.status_amount,
                "Outstanding advances": r.closing_advances,
                "Warnings": ", ".join(r.warning_flags) if r.warning_flags else "",
            }
        )
    f = summary.footer
    rows.append(
        {
            "Partner": "Totals",
            "Active": "",
            "Share %": "",
            "Opening position": f.total_opening_position,
            "Capital contributions": f.total_capital_contributions,
            "Profit allocated": f.total_profit_allocated,
            "Repayments": f.total_repayments,
            "Drawings": f.total_drawings,
            "Salary / takeout": f.total_salary,
            "Advances taken": f.total_advances_taken,
            "Loss allocated": f.total_loss_allocated,
            "Advance offsets": f.total_advance_offsets,
            "Net position change": f.total_net_position_change,
            "Closing position": f.total_closing_position,
            "Settlement status": (
                f"{f.count_settled} settled · {f.count_company_owes} company owes · "
                f"{f.count_partner_owes} partner owes"
            ),
            "Status amount": "",
            "Outstanding advances": f.total_outstanding_advances,
            "Warnings": f"{f.count_with_warnings} with warnings",
        }
    )
    return rows


def all_partners_settlement_to_export_df(
    summary: AllPartnersSettlementSummary,
) -> pd.DataFrame:
    return pd.DataFrame(all_partners_settlement_export_rows(summary))


def all_partners_settlement_pdf_payload(
    summary: AllPartnersSettlementSummary,
    *,
    company_name: str,
    currency: str,
    generated_date: datetime.date | None = None,
) -> dict[str, object]:
    """Structured payload for consolidated all-partners PDF (P4)."""
    table_rows = []
    for r in summary.rows:
        table_rows.append(
            {
                "partner": r.partner_name,
                "share_pct": r.profit_share_pct,
                "opening": r.opening_position,
                "net_change": r.net_position_change,
                "closing": r.closing_position,
                "status": r.settlement_status,
                "status_amount": r.status_amount,
                "advances": r.closing_advances,
                "warnings": ", ".join(r.warning_flags) if r.warning_flags else "—",
            }
        )
    f = summary.footer
    return {
        "company_name": company_name,
        "currency": currency,
        "from_date": summary.from_date,
        "to_date": summary.to_date,
        "generated_date": generated_date or datetime.date.today(),
        "table_rows": table_rows,
        "footer": {
            "opening": f.total_opening_position,
            "net_change": f.total_net_position_change,
            "closing": f.total_closing_position,
            "advances": f.total_outstanding_advances,
            "status_summary": (
                f"{f.count_settled} settled · {f.count_company_owes} company owes · "
                f"{f.count_partner_owes} partner owes"
            ),
        },
    }
