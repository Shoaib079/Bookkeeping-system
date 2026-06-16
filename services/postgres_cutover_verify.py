"""PostgreSQL cutover verification — row counts, TB, reports, bank balances."""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from services.money import line_money, money_to_float
from services.pg_sqlite_data_migration import table_row_counts
from services.read_balances import calculate_account_balance
from services.read_reports import compute_balance_sheet, compute_cash_flow, compute_profit_loss


def trial_balance_fingerprint(session: Session, company_id: int) -> dict[str, Any]:
    lines = session.query(models.JournalEntryLine).filter_by(company_id=company_id).all()
    deb = round(sum(line_money(l.debit) for l in lines), 2)
    cred = round(sum(line_money(l.credit) for l in lines), 2)
    return {"debit_total": deb, "credit_total": cred, "balanced": abs(deb - cred) <= 0.01}


def report_fingerprint(session: Session, company_id: int) -> dict[str, Any]:
    today = datetime.date.today()
    start = datetime.date(2000, 1, 1)
    pl = compute_profit_loss(session, company_id=company_id, start_date=start, end_date=today)
    bs = compute_balance_sheet(session, company_id=company_id, as_of=today)
    cf = compute_cash_flow(session, company_id=company_id, start_date=start, end_date=today)
    banks = session.query(models.BankAccount).filter_by(company_id=company_id).all()
    ar = (
        session.query(func.coalesce(func.sum(models.Sale.balance), 0))
        .filter(models.Sale.company_id == company_id, models.Sale.is_void.is_(False))
        .scalar()
    )
    ap = (
        session.query(func.coalesce(func.sum(models.Payable.amount), 0))
        .filter(
            models.Payable.company_id == company_id,
            models.Payable.is_void.is_(False),
            models.Payable.paid.is_(False),
        )
        .scalar()
    )
    allocs = (
        session.query(func.count())
        .select_from(models.PartnerProfitAllocation)
        .filter_by(company_id=company_id)
        .scalar()
        or 0
    )
    re_acct = (
        session.query(models.ChartOfAccounts)
        .filter_by(company_id=company_id, account_name="Retained Earnings")
        .first()
    )
    re_bal = (
        calculate_account_balance(session, re_acct, company_id=company_id) if re_acct else 0.0
    )
    return {
        "pl_net": round(pl.net, 2),
        "pl_total_income": round(pl.total_income, 2),
        "pl_total_expenses": round(pl.total_expenses, 2),
        "bs_total_assets": round(bs.total_assets, 2),
        "bs_total_liabilities": round(bs.total_liabilities, 2),
        "bs_total_equity": round(bs.total_equity, 2),
        "bs_balanced": bs.balanced,
        "cf_net_total": round(cf.net_total, 2),
        "bank_balances": {b.name: money_to_float(b.balance) for b in banks},
        "ar_balance_sum": money_to_float(ar or 0),
        "ap_open_sum": money_to_float(ap or 0),
        "partner_allocation_count": int(allocs),
        "retained_earnings_balance": money_to_float(re_bal),
    }


def company_ids(session: Session) -> list[int]:
    return [c.id for c in session.query(models.Company).order_by(models.Company.id).all()]


def compare_sqlite_postgres_parity(
    *,
    sqlite_session: Session,
    pg_session: Session,
    company_ids_list: list[int] | None = None,
) -> dict[str, Any]:
    ids = company_ids_list or company_ids(sqlite_session)
    sqlite_counts = table_row_counts(sqlite_session)
    pg_counts = table_row_counts(pg_session)
    count_mismatches = {
        t: {"sqlite": sqlite_counts.get(t, 0), "pg": pg_counts.get(t, 0)}
        for t in sorted(set(sqlite_counts) | set(pg_counts))
        if sqlite_counts.get(t, 0) != pg_counts.get(t, 0)
    }
    sqlite_reports = {cid: report_fingerprint(sqlite_session, cid) for cid in ids}
    pg_reports = {cid: report_fingerprint(pg_session, cid) for cid in ids}
    sqlite_tb = {cid: trial_balance_fingerprint(sqlite_session, cid) for cid in ids}
    pg_tb = {cid: trial_balance_fingerprint(pg_session, cid) for cid in ids}
    report_mismatches = {
        str(cid): {"sqlite": sqlite_reports[cid], "pg": pg_reports[cid]}
        for cid in ids
        if sqlite_reports[cid] != pg_reports[cid]
    }
    tb_mismatches = {
        str(cid): {"sqlite": sqlite_tb[cid], "pg": pg_tb[cid]}
        for cid in ids
        if sqlite_tb[cid] != pg_tb[cid]
    }
    return {
        "companies": ids,
        "row_count_mismatches": count_mismatches,
        "trial_balance_mismatches": tb_mismatches,
        "report_mismatches": report_mismatches,
        "parity_ok": not (count_mismatches or report_mismatches or tb_mismatches),
    }


def company_isolation_check(session: Session) -> dict[str, Any]:
    """Ensure journal lines never cross company boundaries on shared accounts."""
    violations: list[dict[str, Any]] = []
    for company in session.query(models.Company).order_by(models.Company.id).all():
        foreign_lines = (
            session.query(models.JournalEntryLine)
            .filter(
                models.JournalEntryLine.company_id == company.id,
                models.JournalEntryLine.account_id.in_(
                    session.query(models.ChartOfAccounts.id).filter(
                        models.ChartOfAccounts.company_id != company.id
                    )
                ),
            )
            .limit(5)
            .all()
        )
        if foreign_lines:
            violations.append(
                {
                    "company_id": company.id,
                    "foreign_line_ids": [line.id for line in foreign_lines],
                }
            )
    return {"company_isolation_ok": not violations, "violations": violations}
