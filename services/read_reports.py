"""FASTAPI-P0.2-B — read-only financial statement DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import ChartOfAccounts, JournalEntry
from services.money import line_money
from services.read_balances import calculate_account_balance_for_period

_BS_EPOCH = datetime.date(2000, 1, 1)
_PERIOD_CLOSE_EXCL = ["PeriodClose"]
_FINANCING_REFS = frozenset({"BankDeposit", "BankWithdrawal", "BankTransfer"})


@dataclass(frozen=True, slots=True)
class FinancialStatementLine:
    code: str
    account_name: str
    amount: float


@dataclass(frozen=True, slots=True)
class ProfitLossStatement:
    start_date: datetime.date
    end_date: datetime.date
    income_lines: tuple[FinancialStatementLine, ...]
    expense_lines: tuple[FinancialStatementLine, ...]
    total_income: float
    total_expenses: float
    net: float
    margin_pct: float
    is_profit: bool


@dataclass(frozen=True, slots=True)
class BalanceSheetStatement:
    as_of: datetime.date
    asset_lines: tuple[FinancialStatementLine, ...]
    liability_lines: tuple[FinancialStatementLine, ...]
    equity_lines: tuple[FinancialStatementLine, ...]
    net_income: float
    total_assets: float
    total_liabilities: float
    base_equity: float
    total_equity: float
    balanced: bool
    imbalance: float


@dataclass(frozen=True, slots=True)
class CashFlowRow:
    date: datetime.date
    description: str
    type: str
    inflow: float
    outflow: float


@dataclass(frozen=True, slots=True)
class CashFlowStatement:
    start_date: datetime.date
    end_date: datetime.date
    operating_rows: tuple[CashFlowRow, ...]
    financing_rows: tuple[CashFlowRow, ...]
    op_in: float
    op_out: float
    fin_in: float
    fin_out: float
    net_op: float
    net_fin: float
    net_total: float
    has_cash_accounts: bool


def _active_accounts(session: Session, company_id: int) -> list[ChartOfAccounts]:
    return (
        session.query(ChartOfAccounts)
        .filter_by(company_id=company_id, is_active=True)
        .order_by(ChartOfAccounts.account_code)
        .all()
    )


def _account_by_name(session: Session, company_id: int, name: str):
    return (
        session.query(ChartOfAccounts)
        .filter_by(company_id=company_id, account_name=name, is_active=True)
        .first()
    )


def compute_profit_loss(
    session: Session,
    *,
    company_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
) -> ProfitLossStatement:
    accounts = _active_accounts(session, company_id)
    income_lines: list[FinancialStatementLine] = []
    expense_lines: list[FinancialStatementLine] = []
    total_income = 0.0
    total_expenses = 0.0

    for acct in accounts:
        if acct.account_type not in {"Income", "Expense"}:
            continue
        bal = calculate_account_balance_for_period(
            session,
            acct,
            start_date,
            end_date,
            exclude_refs=_PERIOD_CLOSE_EXCL,
            company_id=company_id,
        )
        if bal == 0:
            continue
        line = FinancialStatementLine(
            code=acct.account_code,
            account_name=acct.account_name,
            amount=round(bal, 2),
        )
        if acct.account_type == "Income":
            income_lines.append(line)
            total_income += bal
        else:
            expense_lines.append(line)
            total_expenses += bal

    net = round(total_income - total_expenses, 2)
    margin_pct = (net / total_income * 100) if total_income else 0.0
    return ProfitLossStatement(
        start_date=start_date,
        end_date=end_date,
        income_lines=tuple(income_lines),
        expense_lines=tuple(expense_lines),
        total_income=total_income,
        total_expenses=total_expenses,
        net=net,
        margin_pct=margin_pct,
        is_profit=net >= 0,
    )


def compute_balance_sheet(
    session: Session,
    *,
    company_id: int,
    as_of: datetime.date,
) -> BalanceSheetStatement:
    accounts = _active_accounts(session, company_id)

    def period_bal(acct):
        return calculate_account_balance_for_period(
            session, acct, _BS_EPOCH, as_of, company_id=company_id,
        )

    asset_lines = tuple(
        FinancialStatementLine(
            code=a.account_code,
            account_name=a.account_name,
            amount=round(period_bal(a), 2),
        )
        for a in accounts
        if a.account_type == "Asset"
    )
    liability_lines = tuple(
        FinancialStatementLine(
            code=a.account_code,
            account_name=a.account_name,
            amount=round(period_bal(a), 2),
        )
        for a in accounts
        if a.account_type == "Liability"
    )
    equity_lines = tuple(
        FinancialStatementLine(
            code=a.account_code,
            account_name=a.account_name,
            amount=round(period_bal(a), 2),
        )
        for a in accounts
        if a.account_type == "Equity"
    )

    income_total = sum(
        calculate_account_balance_for_period(
            session, a, _BS_EPOCH, as_of,
            exclude_refs=_PERIOD_CLOSE_EXCL, company_id=company_id,
        )
        for a in accounts
        if a.account_type == "Income"
    )
    expense_total = sum(
        calculate_account_balance_for_period(
            session, a, _BS_EPOCH, as_of,
            exclude_refs=_PERIOD_CLOSE_EXCL, company_id=company_id,
        )
        for a in accounts
        if a.account_type == "Expense"
    )
    net_income = income_total - expense_total

    raw_assets = sum(period_bal(a) for a in accounts if a.account_type == "Asset")
    raw_liabilities = sum(
        period_bal(a) for a in accounts if a.account_type == "Liability"
    )
    raw_equity = sum(period_bal(a) for a in accounts if a.account_type == "Equity")

    total_assets = round(raw_assets, 2)
    total_liabilities = round(raw_liabilities, 2)
    base_equity = round(raw_equity, 2)
    total_equity = round(raw_equity + net_income, 2)
    raw_rhs = raw_liabilities + raw_equity + net_income
    imbalance = abs(raw_assets - raw_rhs)

    return BalanceSheetStatement(
        as_of=as_of,
        asset_lines=asset_lines,
        liability_lines=liability_lines,
        equity_lines=equity_lines,
        net_income=net_income,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        base_equity=base_equity,
        total_equity=total_equity,
        balanced=imbalance < 0.01,
        imbalance=imbalance,
    )


def compute_cash_flow(
    session: Session,
    *,
    company_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
) -> CashFlowStatement:
    cash_acct = _account_by_name(session, company_id, "Cash")
    bank_acct = _account_by_name(session, company_id, "Bank")
    cash_ids = {a.id for a in (cash_acct, bank_acct) if a}

    if not cash_ids:
        return CashFlowStatement(
            start_date=start_date,
            end_date=end_date,
            operating_rows=(),
            financing_rows=(),
            op_in=0.0,
            op_out=0.0,
            fin_in=0.0,
            fin_out=0.0,
            net_op=0.0,
            net_fin=0.0,
            net_total=0.0,
            has_cash_accounts=False,
        )

    entries = (
        session.query(JournalEntry)
        .filter(
            JournalEntry.company_id == company_id,
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
        .order_by(JournalEntry.entry_date)
        .all()
    )

    operating_rows: list[CashFlowRow] = []
    financing_rows: list[CashFlowRow] = []
    for entry in entries:
        for line in entry.lines:
            if line.account_id not in cash_ids:
                continue
            net = round(line_money(line.debit) - line_money(line.credit), 2)
            if net == 0:
                continue
            row = CashFlowRow(
                date=entry.entry_date,
                description=entry.description,
                type=entry.reference_type or "Manual",
                inflow=net if net > 0 else 0.0,
                outflow=round(-net, 2) if net < 0 else 0.0,
            )
            if (entry.reference_type or "") in _FINANCING_REFS:
                financing_rows.append(row)
            else:
                operating_rows.append(row)

    op_in = round(sum(r.inflow for r in operating_rows), 2)
    op_out = round(sum(r.outflow for r in operating_rows), 2)
    fin_in = round(sum(r.inflow for r in financing_rows), 2)
    fin_out = round(sum(r.outflow for r in financing_rows), 2)
    net_op = round(op_in - op_out, 2)
    net_fin = round(fin_in - fin_out, 2)
    net_total = round(net_op + net_fin, 2)

    return CashFlowStatement(
        start_date=start_date,
        end_date=end_date,
        operating_rows=tuple(operating_rows),
        financing_rows=tuple(financing_rows),
        op_in=op_in,
        op_out=op_out,
        fin_in=fin_in,
        fin_out=fin_out,
        net_op=net_op,
        net_fin=net_fin,
        net_total=net_total,
        has_cash_accounts=True,
    )
