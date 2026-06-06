"""Per-company Chart of Accounts seeding — Phase 14D-C.

Startup-safe: accepts company_id explicitly; never uses cq() or session company context.
"""

from __future__ import annotations

import datetime

from models import ChartOfAccounts, MigrationFlag
from registry.service import get_setting

# (code, name, type, currency) — currency None = reporting / any currency
STANDARD_COA_ACCOUNTS: tuple[tuple[str, str, str, str | None], ...] = (
    ("1000", "Cash", "Asset", "TRY"),
    ("1001", "Cash USD", "Asset", "USD"),
    ("1002", "Cash EUR", "Asset", "EUR"),
    ("1003", "Cash GBP", "Asset", "GBP"),
    ("1010", "Bank", "Asset", "TRY"),
    ("1011", "Bank USD", "Asset", "USD"),
    ("1012", "Bank EUR", "Asset", "EUR"),
    ("1013", "Bank GBP", "Asset", "GBP"),
    ("1200", "Accounts Receivable", "Asset", None),
    ("1250", "Employee Advances", "Asset", None),
    ("1300", "Inventory", "Asset", None),
    ("2000", "Accounts Payable", "Liability", None),
    ("2100", "Loans", "Liability", None),
    ("3000", "Owner Capital", "Equity", None),
    ("3100", "Retained Earnings", "Equity", None),
    ("3200", "Owner Drawings", "Equity", None),
    ("3900", "Opening Balance Equity", "Equity", None),
    ("4000", "Sales Revenue", "Income", None),
    ("4100", "Other Income", "Income", None),
    ("5000", "Rent Expense", "Expense", None),
    ("5100", "Salary Expense", "Expense", None),
    ("5200", "Utility Expense", "Expense", None),
    ("5300", "Advertising Expense", "Expense", None),
    ("5400", "Fuel Expense", "Expense", None),
    ("5500", "Office Expense", "Expense", None),
    ("4200", "FX Gain", "Income", None),
    ("5600", "FX Loss", "Expense", None),
    ("5700", "Cash Over/Short", "Expense", None),
    # Phase 18-MVP-1 — bank reconciliation foundation
    ("1150", "Card Sales Clearing", "Asset", None),
    ("5800", "Bank Charges", "Expense", None),
    # Phase 18-MVP-5 — company credit card liability
    ("2110", "Credit Card Payable", "Liability", None),
)

# Accounts introduced after the initial per-company COA seed; backfilled into
# already-seeded companies by ensure_phase18_accounts() at startup.
PHASE18_ACCOUNTS: tuple[tuple[str, str, str, str | None], ...] = (
    ("1150", "Card Sales Clearing", "Asset", None),
    ("5800", "Bank Charges", "Expense", None),
)

PHASE18_MVP5_ACCOUNTS: tuple[tuple[str, str, str, str | None], ...] = (
    ("2110", "Credit Card Payable", "Liability", None),
)

WORKERS_ACCOUNTS: tuple[tuple[str, str, str, str | None], ...] = (
    ("1250", "Employee Advances", "Asset", None),
)

_COA_TEMPLATES = {
    "standard": STANDARD_COA_ACCOUNTS,
}


def _coa_flag_name(company_id: int) -> str:
    return f"coa_seeded_v1:{company_id}"


def get_coa_accounts(template: str = "standard") -> tuple[tuple[str, str, str, str | None], ...]:
    accounts = _COA_TEMPLATES.get(template)
    if accounts is None:
        raise ValueError(f"Unknown COA template: {template}")
    return accounts


def seed_chart_of_accounts_for_company(
    session,
    company_id: int,
    *,
    template: str = "standard",
) -> dict:
    """Seed default COA rows for one company. Idempotent and startup-safe."""
    if company_id is None:
        raise ValueError("company_id is required")

    flag_name = _coa_flag_name(company_id)
    if session.query(MigrationFlag).filter_by(name=flag_name).first():
        return {"company_id": company_id, "created": 0, "already_seeded": True}

    existing = (
        session.query(ChartOfAccounts)
        .filter_by(company_id=company_id)
        .count()
    )
    if existing > 0:
        session.add(
            MigrationFlag(name=flag_name, applied_at=datetime.date.today())
        )
        session.commit()
        return {"company_id": company_id, "created": 0, "already_seeded": True}

    try:
        template_key = template
        try:
            template_key = get_setting(
                session, "accounting.coa_template", company_id=company_id
            ) or template
        except KeyError:
            template_key = template

        created = 0
        for code, name, acc_type, curr in get_coa_accounts(template_key):
            exists = (
                session.query(ChartOfAccounts)
                .filter_by(company_id=company_id, account_code=code)
                .first()
            )
            if exists:
                continue
            session.add(
                ChartOfAccounts(
                    account_code=code,
                    account_name=name,
                    account_type=acc_type,
                    currency=curr,
                    company_id=company_id,
                )
            )
            created += 1

        session.add(
            MigrationFlag(name=flag_name, applied_at=datetime.date.today())
        )
        session.commit()
        return {"company_id": company_id, "created": created, "already_seeded": False}
    except Exception:
        session.rollback()
        raise


def ensure_accounts_for_company(
    session,
    company_id: int | None,
    accounts: tuple[tuple[str, str, str, str | None], ...] = PHASE18_ACCOUNTS,
) -> int:
    """Insert any of `accounts` missing for one company (or legacy global when
    company_id is None). Does not commit; returns the number created.

    Idempotent: an account already present (matched by code within the same
    company scope) is left untouched.
    """
    created = 0
    for code, name, acc_type, curr in accounts:
        q = session.query(ChartOfAccounts).filter_by(account_code=code)
        q = q.filter_by(company_id=company_id) if company_id is not None else q
        if q.first():
            continue
        session.add(
            ChartOfAccounts(
                account_code=code,
                account_name=name,
                account_type=acc_type,
                currency=curr,
                company_id=company_id,
            )
        )
        created += 1
    return created


def seed_chart_of_accounts_legacy_global(session) -> dict:
    """Pre-multi-company bootstrap: seed COA rows without company_id.

    Used only when company_1 does not exist yet during first startup.
    """
    created = 0
    for code, name, acc_type, curr in STANDARD_COA_ACCOUNTS:
        exists = session.query(ChartOfAccounts).filter_by(account_code=code).first()
        if exists:
            if curr and exists.currency is None:
                exists.currency = curr
            continue
        session.add(
            ChartOfAccounts(
                account_code=code,
                account_name=name,
                account_type=acc_type,
                currency=curr,
            )
        )
        created += 1
    session.commit()
    return {"created": created, "legacy_global": True}
