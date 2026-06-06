"""Manual match & post for bank statement rows — Phase 18-MVP-3."""

from __future__ import annotations

import datetime
import json
from typing import Any

from models import (
    BankAccount,
    BankStatementImport,
    BankStatementRow,
    BankTransaction,
    ChartOfAccounts,
    ExpenseRecord,
    JournalEntry,
    Partner,
    PartnerMovement,
    Worker,
    WorkerMovement,
    Payable,
    SettlementStatementImport,
    SettlementStatementRow,
    Vendor,
)

_PARTNER_REF_TYPES = {
    "CapitalContribution": "PartnerCapital",
    "Drawing": "PartnerDrawing",
    "Salary": "PartnerSalary",
    "Advance": "PartnerAdvance",
    "Repayment": "PartnerRepayment",
}

_WITHDRAWAL_PARTNER_TYPES = ("Drawing", "Salary", "Advance")
_DEPOSIT_PARTNER_TYPES = ("CapitalContribution", "Repayment")


class MatchPostError(Exception):
    """Raised when match/post cannot proceed."""


def _app():
    import app as app_module

    return app_module


def _row_context(session, row_id: int, company_id: int) -> tuple[BankStatementRow, BankStatementImport]:
    row = session.get(BankStatementRow, row_id)
    if not row:
        raise MatchPostError("Statement row not found")
    imp = session.get(BankStatementImport, row.bank_statement_import_id)
    if not imp or imp.company_id != company_id:
        raise MatchPostError("Import not found for this company")
    if row.status == "posted":
        raise MatchPostError("This row is already posted")
    if row.status in ("skipped", "parse_error"):
        raise MatchPostError("Cannot post a skipped or parse-error row")
    if not row.parsed_successfully:
        raise MatchPostError("Row did not parse successfully")
    return row, imp


def _create_bank_txn(
    session,
    *,
    bank_account_id: int,
    row: BankStatementRow,
    company_id: int,
    txn_type: str,
) -> BankTransaction:
    ba = session.get(BankAccount, bank_account_id)
    if not ba:
        raise MatchPostError("Bank account not found")
    amt = round(float(row.amount), 2)
    btxn = BankTransaction(
        account_id=bank_account_id,
        date=row.date,
        amount=amt,
        type=txn_type,
        description=(row.description or "")[:500],
        company_id=company_id,
        is_reconciled=True,
        statement_ref=f"bsr:{row.id}",
    )
    session.add(btxn)
    session.flush()
    from reconciliation.company_card import apply_account_balance_delta

    apply_account_balance_delta(ba, txn_type, amt)
    session.add(ba)
    return btxn


def _finalize_row(
    session,
    row: BankStatementRow,
    *,
    match_type: str,
    journal_entry_id: int,
    bank_transaction_id: int,
    user_id: int | None,
    clearing_sale_ids: list[int] | None = None,
    vendor_id: int | None = None,
    payable_id: int | None = None,
    expense_record_id: int | None = None,
    partner_movement_id: int | None = None,
    worker_movement_id: int | None = None,
) -> None:
    now = datetime.datetime.now()
    row.status = "posted"
    row.match_type = match_type
    row.posted_journal_entry_id = journal_entry_id
    row.bank_transaction_id = bank_transaction_id
    row.posted_at = now
    row.posted_by_user_id = user_id
    row.vendor_id = vendor_id
    row.payable_id = payable_id
    row.expense_record_id = expense_record_id
    row.partner_movement_id = partner_movement_id
    row.worker_movement_id = worker_movement_id
    if clearing_sale_ids:
        row.clearing_sale_ids_json = json.dumps(clearing_sale_ids)
    session.add(row)


def _bank_charges_enabled(session, company_id: int) -> bool:
    from registry.service import get_setting

    return bool(get_setting(session, "banking.bank_charges_enabled", company_id=company_id))


def _resolve_settlement_fee(
    session,
    *,
    company_id: int,
    deposit_amt: float,
    clearing_total: float,
    settlement_row_id: int | None,
    confirm_inferred_fee: bool,
) -> tuple[float, str | None, SettlementStatementRow | None]:
    """Return (fee_amount, fee_source, linked settlement row). fee_source is
    'settlement' | 'inferred' | None."""
    fee_amt = 0.0
    fee_source: str | None = None
    settlement_row: SettlementStatementRow | None = None

    if settlement_row_id:
        settlement_row = session.get(SettlementStatementRow, settlement_row_id)
        if not settlement_row or settlement_row.status != "staging":
            raise MatchPostError("Settlement batch not found or already used")
        imp = session.get(SettlementStatementImport, settlement_row.settlement_statement_import_id)
        if not imp or imp.company_id != company_id:
            raise MatchPostError("Settlement batch belongs to another company")
        if not settlement_row.parsed_successfully:
            raise MatchPostError("Settlement batch did not parse successfully")
        gross = round(float(settlement_row.gross_amount), 2)
        net = round(float(settlement_row.net_amount), 2)
        fee = round(float(settlement_row.fee_amount), 2)
        if abs(gross - clearing_total) > 0.01:
            raise MatchPostError(
                f"Settlement gross ({gross:,.2f}) must equal clearing total ({clearing_total:,.2f})"
            )
        if abs(net - deposit_amt) > 0.01:
            raise MatchPostError(
                f"Settlement net ({net:,.2f}) must equal bank deposit ({deposit_amt:,.2f})"
            )
        if abs(gross - fee - net) > 0.02:
            raise MatchPostError("Settlement gross, fee, and net do not balance")
        fee_amt = fee
        fee_source = "settlement"
        return fee_amt, fee_source, settlement_row

    if abs(deposit_amt - clearing_total) <= 0.01:
        return 0.0, None, None

    if deposit_amt > clearing_total:
        raise MatchPostError(
            f"Deposit ({deposit_amt:,.2f}) exceeds clearing total ({clearing_total:,.2f}). "
            "Handle refunds or chargebacks manually."
        )

    fee_amt = round(clearing_total - deposit_amt, 2)
    if not _bank_charges_enabled(session, company_id):
        raise MatchPostError(
            f"Deposit ({deposit_amt:,.2f}) is less than clearing ({clearing_total:,.2f}). "
            "Enable **Bank charges** in Company Setup to book the processor fee."
        )
    if not confirm_inferred_fee:
        raise MatchPostError(
            f"Processor fee of {fee_amt:,.2f} will post to Bank Charges. "
            "Confirm the fee before posting."
        )
    return fee_amt, "inferred", None


def post_deposit_clearing_match(
    session,
    *,
    row_id: int,
    company_id: int,
    sale_ids: list[int],
    user_id: int | None,
    settlement_row_id: int | None = None,
    confirm_inferred_fee: bool = False,
) -> dict[str, Any]:
    """Match a bank deposit to card sales in clearing and post settlement JE."""
    app = _app()
    row, imp = _row_context(session, row_id, company_id)
    if not row.credit_amount and row.debit_amount:
        raise MatchPostError("This row is a withdrawal, not a deposit")
    if not sale_ids:
        raise MatchPostError("Select at least one card sale to match")

    from reconciliation.clearing import get_unsettled_card_sales

    window_start = row.date - datetime.timedelta(days=7) if row.date else imp.start_date
    window_end = row.date + datetime.timedelta(days=7) if row.date else imp.end_date
    candidates = {
        c["sale_id"]: c
        for c in get_unsettled_card_sales(
            session,
            company_id,
            date_from=window_start or row.date,
            date_to=window_end or row.date,
            get_account_by_name=app.get_account_by_name,
        )
    }
    selected: list[dict] = []
    clearing_total = 0.0
    for sid in sale_ids:
        if sid not in candidates:
            raise MatchPostError(f"Card sale #{sid} is not available for settlement")
        selected.append(candidates[sid])
        clearing_total += candidates[sid]["amount"]

    deposit_amt = round(float(row.amount), 2)
    clearing_total = round(clearing_total, 2)
    fee_amt, fee_source, settlement_row = _resolve_settlement_fee(
        session,
        company_id=company_id,
        deposit_amt=deposit_amt,
        clearing_total=clearing_total,
        settlement_row_id=settlement_row_id,
        confirm_inferred_fee=confirm_inferred_fee,
    )

    bank_gl = app.get_account_by_name(session, "Bank", currency=imp.currency)
    clearing_gl = app.get_account_by_name(session, "Card Sales Clearing")
    if not bank_gl or not clearing_gl:
        raise MatchPostError("Bank or Card Sales Clearing GL account missing")

    charges_gl = None
    if fee_amt > 0.01:
        charges_gl = app.get_account_by_name(session, "Bank Charges")
        if not charges_gl:
            raise MatchPostError("Bank Charges GL account missing")

    btxn = _create_bank_txn(
        session,
        bank_account_id=imp.bank_account_id,
        row=row,
        company_id=company_id,
        txn_type="deposit",
    )
    if fee_amt > 0.01:
        btxn.charge_subtype = "card_settlement_fee"

    je_lines = [(bank_gl.id, deposit_amt, 0)]
    if fee_amt > 0.01 and charges_gl:
        je_lines.append((charges_gl.id, fee_amt, 0))
    je_lines.append((clearing_gl.id, 0, clearing_total))

    fee_note = f" · fee {fee_amt:,.2f}" if fee_amt > 0.01 else ""
    je = app.create_journal_entry(
        session,
        row.date,
        f"Card settlement — stmt row {row.import_row_index}{fee_note}",
        "BankStmtSettlement",
        row.id,
        je_lines,
        currency=imp.currency,
    )
    row.settlement_row_id = settlement_row.id if settlement_row else None
    _finalize_row(
        session,
        row,
        match_type="deposit_clearing",
        journal_entry_id=je.id,
        bank_transaction_id=btxn.id,
        user_id=user_id,
        clearing_sale_ids=sale_ids,
    )
    if settlement_row:
        settlement_row.status = "posted"
        settlement_row.bank_statement_row_id = row.id
        settlement_row.posted_journal_entry_id = je.id
        settlement_row.posted_at = datetime.datetime.now()
        settlement_row.posted_by_user_id = user_id
        session.add(settlement_row)

    session.commit()
    return {
        "journal_entry_id": je.id,
        "bank_transaction_id": btxn.id,
        "amount": deposit_amt,
        "fee_amount": fee_amt,
        "fee_source": fee_source,
        "sale_ids": sale_ids,
        "settlement_row_id": settlement_row.id if settlement_row else None,
    }


def post_generic_deposit(
    session,
    *,
    row_id: int,
    company_id: int,
    credit_account_name: str,
    user_id: int | None,
) -> dict[str, Any]:
    """Post a deposit to Bank with user-selected credit GL (non-clearing)."""
    app = _app()
    row, imp = _row_context(session, row_id, company_id)
    if row.debit_amount and not row.credit_amount:
        raise MatchPostError("This row is a withdrawal, not a deposit")

    amt = round(float(row.amount), 2)
    bank_gl = app.get_account_by_name(session, "Bank", currency=imp.currency)
    credit_gl = app.get_account_by_name(session, credit_account_name, currency=imp.currency)
    if not bank_gl or not credit_gl:
        raise MatchPostError("GL accounts not found for deposit posting")

    btxn = _create_bank_txn(
        session,
        bank_account_id=imp.bank_account_id,
        row=row,
        company_id=company_id,
        txn_type="deposit",
    )
    je = app.create_journal_entry(
        session,
        row.date,
        f"Bank deposit — stmt row {row.import_row_index}",
        "BankStmtDeposit",
        row.id,
        [(bank_gl.id, amt, 0), (credit_gl.id, 0, amt)],
        currency=imp.currency,
    )
    _finalize_row(
        session,
        row,
        match_type="other_deposit",
        journal_entry_id=je.id,
        bank_transaction_id=btxn.id,
        user_id=user_id,
    )
    session.commit()
    return {"journal_entry_id": je.id, "bank_transaction_id": btxn.id, "amount": amt}


def _partner_gl_accounts(session, partner: Partner) -> tuple[ChartOfAccounts, ChartOfAccounts, ChartOfAccounts]:
    cap = session.get(ChartOfAccounts, partner.capital_account_id)
    cur = session.get(ChartOfAccounts, partner.current_account_id)
    adv = session.get(ChartOfAccounts, partner.advance_account_id)
    if not all([cap, cur, adv]):
        raise MatchPostError("Partner GL accounts missing — check Partner Accounts setup.")
    return cap, cur, adv


def post_partner_statement_match(
    session,
    *,
    row_id: int,
    company_id: int,
    partner_id: int,
    movement_type: str,
    user_id: int | None,
) -> dict[str, Any]:
    """Post a bank statement line as a partner movement (salary, drawing, advance, etc.)."""
    app = _app()
    row, imp = _row_context(session, row_id, company_id)
    if movement_type not in _PARTNER_REF_TYPES:
        raise MatchPostError(f"Unknown partner movement type: {movement_type}")
    if movement_type == "AdvanceOffset":
        raise MatchPostError("Advance offset has no bank movement — use Partner Accounts.")

    is_deposit = bool(row.credit_amount and not row.debit_amount)
    is_withdrawal = bool(row.debit_amount and not row.credit_amount)
    if movement_type in _WITHDRAWAL_PARTNER_TYPES:
        if not is_withdrawal:
            raise MatchPostError("This partner movement requires a bank withdrawal line.")
        txn_type = "withdrawal"
    elif movement_type in _DEPOSIT_PARTNER_TYPES:
        if not is_deposit:
            raise MatchPostError("This partner movement requires a bank deposit line.")
        txn_type = "deposit"
    else:
        raise MatchPostError("Unsupported partner movement for bank statement import.")

    partner = session.get(Partner, partner_id)
    if not partner or not partner.is_active or partner.company_id != company_id:
        raise MatchPostError("Partner not found or inactive.")

    cap_acct, cur_acct, adv_acct = _partner_gl_accounts(session, partner)
    amt = round(float(row.amount), 2)
    if amt <= 0:
        raise MatchPostError("Amount must be positive.")

    bank_gl = app.get_account_by_name(session, "Bank", currency=imp.currency)
    if not bank_gl:
        raise MatchPostError("Bank GL account not found")

    btxn = _create_bank_txn(
        session,
        bank_account_id=imp.bank_account_id,
        row=row,
        company_id=company_id,
        txn_type=txn_type,
    )
    btxn.description = (
        f"Partner {movement_type} — stmt row {row.import_row_index} "
        f"({partner.name})"
    )
    session.add(btxn)

    movement = PartnerMovement(
        partner_id=partner_id,
        movement_type=movement_type,
        amount=amt,
        date=row.date,
        bank_transaction_id=btxn.id,
        notes=(row.description or "")[:500] or None,
        is_void=False,
        created_by_id=user_id,
        created_at=datetime.datetime.now(),
        company_id=company_id,
    )
    session.add(movement)
    session.flush()

    if movement_type == "CapitalContribution":
        lines = [(bank_gl.id, amt, 0), (cap_acct.id, 0, amt)]
    elif movement_type in ("Drawing", "Salary"):
        lines = [(cur_acct.id, amt, 0), (bank_gl.id, 0, amt)]
    elif movement_type == "Advance":
        lines = [(adv_acct.id, amt, 0), (bank_gl.id, 0, amt)]
    else:  # Repayment
        lines = [(bank_gl.id, amt, 0), (adv_acct.id, 0, amt)]

    desc = f"Partner {movement_type}: {partner.name} — stmt row {row.import_row_index}"
    je = app.create_journal_entry(
        session,
        row.date,
        desc,
        _PARTNER_REF_TYPES[movement_type],
        movement.id,
        lines,
        currency=imp.currency,
    )
    movement.journal_entry_id = je.id
    session.add(movement)

    _finalize_row(
        session,
        row,
        match_type=f"partner_{movement_type.lower()}",
        journal_entry_id=je.id,
        bank_transaction_id=btxn.id,
        user_id=user_id,
        partner_movement_id=movement.id,
    )
    session.commit()
    return {
        "journal_entry_id": je.id,
        "bank_transaction_id": btxn.id,
        "partner_movement_id": movement.id,
        "amount": amt,
        "match_type": f"partner_{movement_type.lower()}",
    }


_WORKER_STMT_REF_TYPES = {
    "Salary": "WorkerSalary",
    "Advance": "WorkerAdvance",
}


def post_worker_statement_match(
    session,
    *,
    row_id: int,
    company_id: int,
    worker_id: int,
    movement_type: str,
    user_id: int | None,
    gross_salary: float | None = None,
    deductions: float = 0,
    advance_recovery: float = 0,
    pay_period: str | None = None,
) -> dict[str, Any]:
    """Post a bank withdrawal as worker salary or advance."""
    app = _app()
    row, imp = _row_context(session, row_id, company_id)
    if not (row.debit_amount and not row.credit_amount):
        raise MatchPostError("Worker payroll requires a bank withdrawal line.")

    if movement_type not in _WORKER_STMT_REF_TYPES:
        raise MatchPostError(f"Unknown worker movement type: {movement_type}")

    worker = session.get(Worker, worker_id)
    if not worker or not worker.is_active or worker.company_id != company_id:
        raise MatchPostError("Worker not found or inactive.")

    salary_exp = app.get_account_by_name(session, "Salary Expense")
    adv_acct = app.get_account_by_name(session, "Employee Advances")
    bank_gl = app.get_account_by_name(session, "Bank", currency=imp.currency)
    if not bank_gl:
        raise MatchPostError("Bank GL account not found")
    if movement_type == "Salary" and not salary_exp:
        raise MatchPostError("Salary Expense account missing")
    if not adv_acct:
        raise MatchPostError("Employee Advances account missing")

    bank_paid = round(float(row.amount), 2)
    if bank_paid <= 0:
        raise MatchPostError("Amount must be positive.")

    deductions = round(float(deductions or 0.0), 2)
    advance_recovery = round(float(advance_recovery or 0.0), 2)
    gross_salary = round(float(gross_salary or bank_paid), 2)
    net_salary = 0.0
    net_paid = 0.0
    mv_amount = 0.0

    if movement_type == "Salary":
        if gross_salary <= 0:
            raise MatchPostError("Gross salary must be greater than zero.")
        if deductions < 0 or advance_recovery < 0:
            raise MatchPostError("Deductions and advance recovery cannot be negative.")
        net_salary = round(gross_salary - deductions, 2)
        if net_salary <= 0:
            raise MatchPostError("Net salary after deductions must be greater than zero.")
        net_paid = round(net_salary - advance_recovery, 2)
        if abs(net_paid - bank_paid) > 0.01:
            raise MatchPostError(
                f"Bank withdrawal ({bank_paid:,.2f}) must equal net pay "
                f"(gross − deductions − advance recovery = {net_paid:,.2f})."
            )
        if advance_recovery > 0:
            adv_bal = app.get_worker_advance_balance(session, worker_id)
            if advance_recovery > adv_bal + 0.01:
                raise MatchPostError(
                    f"Advance recovery {advance_recovery:,.2f} exceeds outstanding "
                    f"advance {adv_bal:,.2f}."
                )
        mv_amount = net_salary
        lines = [(salary_exp.id, net_salary, 0)]
        if advance_recovery > 0.01:
            lines.append((adv_acct.id, 0, advance_recovery))
        if net_paid > 0.01:
            lines.append((bank_gl.id, 0, net_paid))
        match_type = "worker_salary"
    else:
        mv_amount = bank_paid
        net_paid = bank_paid
        lines = [(adv_acct.id, mv_amount, 0), (bank_gl.id, 0, mv_amount)]
        match_type = "worker_advance"

    btxn = _create_bank_txn(
        session,
        bank_account_id=imp.bank_account_id,
        row=row,
        company_id=company_id,
        txn_type="withdrawal",
    )
    btxn.description = (
        f"Worker {movement_type} — stmt row {row.import_row_index} ({worker.name})"
    )
    session.add(btxn)

    movement = WorkerMovement(
        worker_id=worker_id,
        movement_type=movement_type,
        amount=mv_amount,
        date=row.date,
        pay_period=pay_period.strip() if pay_period else None,
        gross_salary=gross_salary if movement_type == "Salary" else 0.0,
        deductions=deductions if movement_type == "Salary" else 0.0,
        advance_recovery=advance_recovery if movement_type == "Salary" else 0.0,
        net_paid=net_paid if movement_type == "Salary" else 0.0,
        bank_transaction_id=btxn.id,
        notes=(row.description or "")[:500] or None,
        is_void=False,
        created_by_id=user_id,
        created_at=datetime.datetime.now(),
        company_id=company_id,
    )
    session.add(movement)
    session.flush()

    desc = (
        f"Worker {movement_type}: {worker.name} — stmt row {row.import_row_index}"
    )
    je = app.create_journal_entry(
        session,
        row.date,
        desc,
        _WORKER_STMT_REF_TYPES[movement_type],
        movement.id,
        lines,
        currency=imp.currency,
    )
    movement.journal_entry_id = je.id
    session.add(movement)

    _finalize_row(
        session,
        row,
        match_type=match_type,
        journal_entry_id=je.id,
        bank_transaction_id=btxn.id,
        user_id=user_id,
        worker_movement_id=movement.id,
    )
    session.commit()
    return {
        "journal_entry_id": je.id,
        "bank_transaction_id": btxn.id,
        "worker_movement_id": movement.id,
        "amount": mv_amount,
        "match_type": match_type,
    }


def post_equity_statement_match(
    session,
    *,
    row_id: int,
    company_id: int,
    equity_kind: str,
    user_id: int | None,
) -> dict[str, Any]:
    """Post owner drawing/capital or company loan payment/receipt from a statement line."""
    app = _app()
    row, imp = _row_context(session, row_id, company_id)
    amt = round(float(row.amount), 2)
    if amt <= 0:
        raise MatchPostError("Amount must be positive")

    bank_gl = app.get_account_by_name(session, "Bank", currency=imp.currency)
    if not bank_gl:
        raise MatchPostError("Bank GL account not found")

    is_deposit = bool(row.credit_amount and not row.debit_amount)
    is_withdrawal = bool(row.debit_amount and not row.credit_amount)

    ref_type = ""
    desc = ""
    lines: list[tuple[int, float, float]] = []
    txn_type = ""

    if equity_kind == "owner_drawing":
        if not is_withdrawal:
            raise MatchPostError("Owner drawing requires a bank withdrawal line.")
        draw_gl = app.get_account_by_name(session, "Owner Drawings")
        if not draw_gl:
            raise MatchPostError("Owner Drawings account missing")
        lines = [(draw_gl.id, amt, 0), (bank_gl.id, 0, amt)]
        ref_type = "BankStmtOwnerDrawing"
        desc = f"Owner drawing — stmt row {row.import_row_index}"
        txn_type = "withdrawal"
        match_type = "owner_drawing"
    elif equity_kind == "owner_capital":
        if not is_deposit:
            raise MatchPostError("Capital contribution requires a bank deposit line.")
        cap_gl = app.get_account_by_name(session, "Owner Capital")
        if not cap_gl:
            raise MatchPostError("Owner Capital account missing")
        lines = [(bank_gl.id, amt, 0), (cap_gl.id, 0, amt)]
        ref_type = "BankStmtOwnerCapital"
        desc = f"Owner capital contribution — stmt row {row.import_row_index}"
        txn_type = "deposit"
        match_type = "owner_capital"
    elif equity_kind == "loan_payment":
        if not is_withdrawal:
            raise MatchPostError("Loan payment requires a bank withdrawal line.")
        loan_gl = app.get_account_by_name(session, "Loans")
        if not loan_gl:
            raise MatchPostError("Loans account missing")
        lines = [(loan_gl.id, amt, 0), (bank_gl.id, 0, amt)]
        ref_type = "BankStmtLoanPayment"
        desc = f"Loan repayment — stmt row {row.import_row_index}"
        txn_type = "withdrawal"
        match_type = "loan_payment"
    elif equity_kind == "loan_receipt":
        if not is_deposit:
            raise MatchPostError("Loan receipt requires a bank deposit line.")
        loan_gl = app.get_account_by_name(session, "Loans")
        if not loan_gl:
            raise MatchPostError("Loans account missing")
        lines = [(bank_gl.id, amt, 0), (loan_gl.id, 0, amt)]
        ref_type = "BankStmtLoanReceipt"
        desc = f"Loan proceeds — stmt row {row.import_row_index}"
        txn_type = "deposit"
        match_type = "loan_receipt"
    else:
        raise MatchPostError(f"Unknown equity/loan kind: {equity_kind}")

    btxn = _create_bank_txn(
        session,
        bank_account_id=imp.bank_account_id,
        row=row,
        company_id=company_id,
        txn_type=txn_type,
    )
    je = app.create_journal_entry(
        session,
        row.date,
        desc,
        ref_type,
        row.id,
        lines,
        currency=imp.currency,
    )
    _finalize_row(
        session,
        row,
        match_type=match_type,
        journal_entry_id=je.id,
        bank_transaction_id=btxn.id,
        user_id=user_id,
    )
    session.commit()
    return {
        "journal_entry_id": je.id,
        "bank_transaction_id": btxn.id,
        "amount": amt,
        "match_type": match_type,
    }


def post_vendor_outflow(
    session,
    *,
    row_id: int,
    company_id: int,
    vendor_id: int,
    user_id: int | None,
    payable_id: int | None = None,
    expense_category: str = "Office Expense",
    create_expense: bool = False,
) -> dict[str, Any]:
    """Post a bank withdrawal against a payable or as ad-hoc expense."""
    app = _app()
    row, imp = _row_context(session, row_id, company_id)
    if row.credit_amount and not row.debit_amount:
        raise MatchPostError("This row is a deposit, not a withdrawal")

    vendor = session.get(Vendor, vendor_id)
    if not vendor or vendor.company_id != company_id:
        raise MatchPostError("Vendor not found")

    amt = round(float(row.amount), 2)
    bank_gl = app.get_account_by_name(session, "Bank", currency=imp.currency)
    if not bank_gl:
        raise MatchPostError("Bank GL account not found")

    expense_id = None
    paid_payable_id = None

    if payable_id:
        payable = session.get(Payable, payable_id)
        if not payable or payable.vendor_id != vendor_id or payable.is_void:
            raise MatchPostError("Payable not found for this vendor")
        if payable.paid:
            raise MatchPostError("Payable is already paid")
        ap_gl = app.get_account_by_name(session, "Accounts Payable")
        if not ap_gl:
            raise MatchPostError("Accounts Payable GL missing")
        pay_amt = min(amt, round(float(payable.balance or payable.amount), 2))
        btxn = _create_bank_txn(
            session,
            bank_account_id=imp.bank_account_id,
            row=row,
            company_id=company_id,
            txn_type="withdrawal",
        )
        je = app.create_journal_entry(
            session,
            row.date,
            f"Payable payment — stmt row {row.import_row_index} · {vendor.name}",
            "BankStmtPayable",
            row.id,
            [(ap_gl.id, pay_amt, 0), (bank_gl.id, 0, pay_amt)],
            currency=imp.currency,
        )
        payable.paid_amount = round((payable.paid_amount or 0) + pay_amt, 2)
        payable.balance = round(float(payable.amount) - payable.paid_amount, 2)
        if payable.balance <= 0.01:
            payable.paid = True
            payable.balance = 0.0
        session.add(payable)
        paid_payable_id = payable.id
        match_type = "vendor_payable"
    elif create_expense:
        expense = ExpenseRecord(
            date=row.date,
            expense_type="Expense",
            category=expense_category,
            description=row.description or f"Bank payment — {vendor.name}",
            amount=amt,
            payment_method="Bank",
            company_id=company_id,
            created_by_id=user_id,
            currency=imp.currency,
        )
        session.add(expense)
        session.flush()
        expense_id = expense.id
        btxn = _create_bank_txn(
            session,
            bank_account_id=imp.bank_account_id,
            row=row,
            company_id=company_id,
            txn_type="withdrawal",
        )
        app.post_expense(
            session,
            expense.id,
            amt,
            row.date,
            expense_category,
            payment_method="Bank",
            currency=imp.currency,
        )
        je = (
            session.query(JournalEntry)
            .filter_by(reference_type="Expense", reference_id=expense.id)
            .order_by(JournalEntry.id.desc())
            .first()
        )
        if not je:
            raise MatchPostError("Expense journal entry was not created")
        match_type = "adhoc_expense"
    else:
        raise MatchPostError("Select a payable or choose ad-hoc expense")

    _finalize_row(
        session,
        row,
        match_type=match_type,
        journal_entry_id=je.id,
        bank_transaction_id=btxn.id,
        user_id=user_id,
        vendor_id=vendor_id,
        payable_id=paid_payable_id,
        expense_record_id=expense_id,
    )
    session.commit()
    return {
        "journal_entry_id": je.id,
        "bank_transaction_id": btxn.id,
        "amount": amt,
        "match_type": match_type,
    }


# Wording varies by bank (e.g. İş Bankası: "ÜYE İŞYERİ ÜCRETİ", others: KOMİSYON, POS…).
_COMMISSION_KEYWORDS = (
    "komisyon",
    "commission",
    "bsmv",
    "pos ucret",
    "kart komisyon",
    "tahsilat komisyon",
    "kart tahsilat",
    "uye isyeri",
    "isyeri ucret",
    "merchant fee",
    "merchant",
    "sanal pos",
    "vpos",
    "taksit komisyon",
    "kk tahsilat",
)

# Card-sales deposits — banks rarely say "kart tahsilat"; labels vary (peşin satış, net satış tutarı…).
_GROSS_CARD_DEPOSIT_KEYWORDS = (
    "pesin satis",
    "peşin satış",
    "brut satis",
    "brüt satış",
    "gross sales",
)

_NET_CARD_DEPOSIT_KEYWORDS = (
    "net satis tutari",
    "net satış tutarı",
    "net satis",
    "net satış",
)

_GENERIC_CARD_DEPOSIT_KEYWORDS = (
    "pos yatirma",
    "pos yatırma",
    "kk bloke",
    "sanal pos",
    "kart satis",
    "kart satış",
)

_INTEREST_KEYWORDS = (
    "faiz",
    "gecikme faiz",
    "gecikme",
    "geciken",
    "late interest",
    "interest charge",
    "late fee",
    "late payment",
)

_CREDIT_CARD_ACCOUNT_FEE_KEYWORDS = (
    "yillik ucret",
    "yillik aidat",
    "kart aidat",
    "kk yillik",
    "kredi karti yillik",
    "annual fee",
    "card annual",
    "yillik kart",
)

_CREDIT_CARD_BILL_PAYMENT_KEYWORDS = (
    "kk odeme",
    "kart odeme",
    "kredi karti odeme",
    "kredi kart odeme",
    "kart borcu",
    "kart ekstre",
    "card payment",
    "otomatik odeme",
    "asgari odeme",
    "min odeme",
)

_TRANSFER_FEE_KEYWORDS = (
    "havale",
    "eft",
    "wire",
    "transfer fee",
    "swift",
    "islem ucret",
    "banka masraf",
    "eft masraf",
    "havale masraf",
    "havale ucret",
)


def _fold_tr(text: str) -> str:
    """ASCII-fold Turkish for bank-export description matching."""
    s = text
    for src, dst in (
        ("İ", "i"),
        ("I", "i"),
        ("ı", "i"),
        ("Ş", "s"),
        ("ş", "s"),
        ("Ğ", "g"),
        ("ğ", "g"),
        ("Ü", "u"),
        ("ü", "u"),
        ("Ö", "o"),
        ("ö", "o"),
        ("Ç", "c"),
        ("ç", "c"),
    ):
        s = s.replace(src, dst)
    return s.lower()


def looks_like_interest(description: str) -> bool:
    """Late credit-card or loan interest (faiz) on a bank statement line."""
    folded = _fold_tr(description or "")
    return any(kw in folded for kw in _INTEREST_KEYWORDS)


def looks_like_credit_card_account_fee(description: str) -> bool:
    """Credit-card **yearly** account fee debited from the bank (not monthly routine)."""
    folded = _fold_tr(description or "")
    if looks_like_interest(description):
        return False
    if any(kw in folded for kw in _CREDIT_CARD_BILL_PAYMENT_KEYWORDS):
        return False
    return any(kw in folded for kw in _CREDIT_CARD_ACCOUNT_FEE_KEYWORDS)


def looks_like_credit_card_bill_payment(description: str) -> bool:
    """Paying the card bill from the bank (full or partial — not faiz or annual fee)."""
    folded = _fold_tr(description or "")
    if looks_like_interest(description):
        return False
    if any(kw in folded for kw in _CREDIT_CARD_ACCOUNT_FEE_KEYWORDS):
        return False
    return any(kw in folded for kw in _CREDIT_CARD_BILL_PAYMENT_KEYWORDS)


def looks_like_commission(description: str) -> bool:
    """Heuristic: bank statement line is likely a card/POS merchant commission debit."""
    if looks_like_interest(description) or looks_like_credit_card_account_fee(description):
        return False
    folded = _fold_tr(description or "")
    return any(kw in folded for kw in _COMMISSION_KEYWORDS)


def looks_like_transfer_fee(description: str) -> bool:
    """Heuristic: separate bank transfer / EFT fee line (not POS commission)."""
    if (
        looks_like_commission(description)
        or looks_like_interest(description)
        or looks_like_credit_card_account_fee(description)
    ):
        return False
    folded = _fold_tr(description or "")
    return any(kw in folded for kw in _TRANSFER_FEE_KEYWORDS)


def card_deposit_style(description: str) -> str | None:
    """How the bank labels a card-sales deposit: gross | net | card | None."""
    folded = _fold_tr(description or "")
    if any(kw in folded for kw in _NET_CARD_DEPOSIT_KEYWORDS):
        return "net"
    if any(kw in folded for kw in _GROSS_CARD_DEPOSIT_KEYWORDS):
        return "gross"
    if any(kw in folded for kw in _GENERIC_CARD_DEPOSIT_KEYWORDS):
        return "card"
    return None


def looks_like_statement_bank_fee(description: str) -> bool:
    """Any bank-statement line that is a fee/charge rather than a vendor payment."""
    return (
        looks_like_commission(description)
        or looks_like_interest(description)
        or looks_like_credit_card_account_fee(description)
        or looks_like_transfer_fee(description)
    )


def infer_bank_charge_subtype(description: str) -> str:
    """Tag for Bank Charges reporting (wording varies by bank)."""
    if looks_like_interest(description):
        return "interest"
    if looks_like_credit_card_account_fee(description):
        return "credit_card_fee"
    if looks_like_commission(description):
        return "card_settlement_fee"
    return "transfer_fee"


def bank_charge_fee_label(subtype: str) -> str:
    labels = {
        "interest": "interest",
        "credit_card_fee": "credit card fee",
        "card_settlement_fee": "POS commission",
        "transfer_fee": "transfer fee",
    }
    return labels.get(subtype, "bank charge")


def suggest_deposit_match_kind(
    description: str,
    *,
    card_settlement_on: bool,
) -> str:
    """Default deposit posting path: card_clearing | equity_loan | other_income."""
    if card_settlement_on and card_deposit_style(description):
        return "card_clearing"
    return "other_income"


_WORKER_PAYROLL_KEYWORDS = (
    "maas",
    "maaş",
    "salary",
    "bordro",
    "ucret",
    "ücret",
    "personel",
    "isci",
    "işçi",
    "calisan",
    "çalışan",
    "wage",
    "payroll",
)


def looks_like_worker_payroll(description: str) -> bool:
    """Heuristic: bank withdrawal likely staff salary or wage."""
    folded = _fold_tr(description or "")
    return any(kw in folded for kw in _WORKER_PAYROLL_KEYWORDS)


def suggest_withdrawal_match_kind(
    description: str,
    *,
    company_card_on: bool,
    bank_charges_on: bool,
    has_workers: bool = False,
) -> str:
    """Default withdrawal posting path: cc_bill | bank_fee | worker_payroll | vendor."""
    if company_card_on and looks_like_credit_card_bill_payment(description):
        return "cc_bill"
    if bank_charges_on and looks_like_statement_bank_fee(description):
        return "bank_fee"
    if has_workers and looks_like_worker_payroll(description):
        return "worker_payroll"
    return "vendor"


def get_same_day_deposit_rows(
    session, row_id: int, company_id: int
) -> list[BankStatementRow]:
    """Other postable deposit lines on the same import date (gross+commission pairing)."""
    row = session.get(BankStatementRow, row_id)
    if not row or not row.date:
        return []
    imp = session.get(BankStatementImport, row.bank_statement_import_id)
    if not imp or imp.company_id != company_id:
        return []
    return (
        session.query(BankStatementRow)
        .filter(
            BankStatementRow.bank_statement_import_id == imp.id,
            BankStatementRow.id != row.id,
            BankStatementRow.date == row.date,
            BankStatementRow.credit_amount.isnot(None),
            BankStatementRow.credit_amount > 0,
            BankStatementRow.status.in_(("staging", "duplicate_flagged")),
            BankStatementRow.parsed_successfully == True,  # noqa: E712
        )
        .order_by(BankStatementRow.import_row_index)
        .all()
    )


def post_bank_charge_outflow(
    session,
    *,
    row_id: int,
    company_id: int,
    user_id: int | None,
    charge_subtype: str | None = None,
) -> dict[str, Any]:
    """Post a bank fee withdrawal to Bank Charges (POS commission or transfer fee)."""
    app = _app()
    row, imp = _row_context(session, row_id, company_id)
    if row.credit_amount and not row.debit_amount:
        raise MatchPostError("This row is a deposit, not a bank charge")
    if not _bank_charges_enabled(session, company_id):
        raise MatchPostError(
            "Enable **Bank charges** in Company Setup to post bank fee lines."
        )

    amt = round(float(row.amount), 2)
    if amt <= 0:
        raise MatchPostError("Bank charge amount must be positive")

    subtype = charge_subtype or infer_bank_charge_subtype(row.description or "")
    fee_label = bank_charge_fee_label(subtype)

    charges_gl = app.get_account_by_name(session, "Bank Charges")
    bank_gl = app.get_account_by_name(session, "Bank", currency=imp.currency)
    if not charges_gl or not bank_gl:
        raise MatchPostError("Bank Charges or Bank GL account missing")

    btxn = _create_bank_txn(
        session,
        bank_account_id=imp.bank_account_id,
        row=row,
        company_id=company_id,
        txn_type="withdrawal",
    )
    btxn.charge_subtype = subtype
    session.add(btxn)

    je = app.create_journal_entry(
        session,
        row.date,
        f"Bank {fee_label} — stmt row {row.import_row_index} ({(row.description or '')[:50]})",
        "BankStmtBankCharge",
        row.id,
        [(charges_gl.id, amt, 0), (bank_gl.id, 0, amt)],
        currency=imp.currency,
    )
    _finalize_row(
        session,
        row,
        match_type="bank_charge",
        journal_entry_id=je.id,
        bank_transaction_id=btxn.id,
        user_id=user_id,
    )
    session.commit()
    return {
        "journal_entry_id": je.id,
        "bank_transaction_id": btxn.id,
        "amount": amt,
        "match_type": "bank_charge",
        "charge_subtype": subtype,
    }


def get_postable_rows(session, company_id: int) -> list[BankStatementRow]:
    """Staging rows ready for match & post."""
    return (
        session.query(BankStatementRow)
        .join(BankStatementImport)
        .filter(
            BankStatementImport.company_id == company_id,
            BankStatementRow.status.in_(("staging", "duplicate_flagged")),
            BankStatementRow.parsed_successfully == True,  # noqa: E712
        )
        .order_by(BankStatementRow.date, BankStatementRow.import_row_index)
        .all()
    )
