"""New company provisioning — Phase 14D-D."""

from __future__ import annotations

import datetime
import re

from models import Company, CompanySetting, CompanyUser
from registry.categories_seed import seed_default_categories_for_company
from registry.coa_seed import seed_chart_of_accounts_for_company

_SETTINGS_DEFAULTS = {
    "currency": "TRY",
    "tax_rate": "0.0",
    "financial_year": str(datetime.date.today().year),
    "company_address": "",
    "company_tax_number": "",
    "company_logo_url": "",
}


def slugify_company_name(name: str) -> str:
    """Convert a display name to a URL-safe slug."""
    base = name.strip().lower()
    base = re.sub(r"[^a-z0-9]+", "_", base)
    base = base.strip("_") or "company"
    return base[:40]


def unique_company_slug(session, name: str) -> str:
    """Return a slug unique in companies.slug."""
    base = slugify_company_name(name)
    candidate = base
    n = 2
    while session.query(Company).filter_by(slug=candidate).first():
        suffix = f"_{n}"
        candidate = f"{base[: max(1, 40 - len(suffix))]}{suffix}"
        n += 1
    return candidate


def seed_company_settings(
    session,
    company_id: int,
    *,
    company_name: str,
) -> None:
    """Seed default CompanySetting rows for a new company."""
    rows = {
        **_SETTINGS_DEFAULTS,
        "company_name": company_name,
        "setup.wizard_completed": "false",
        "setup.vertical_template": "general",
        "policy.accounting_mode": "flexible",
        "company.document_language": "en",
    }
    for key, value in rows.items():
        existing = (
            session.query(CompanySetting)
            .filter_by(company_id=company_id, key=key)
            .first()
        )
        if existing:
            continue
        session.add(
            CompanySetting(company_id=company_id, key=key, value=str(value))
        )


def create_company(
    session,
    *,
    name: str,
    full_name: str = "",
    email: str = "",
    phone: str = "",
    created_by_user_id: int,
) -> Company:
    """Create a company, owner membership, settings, COA, and categories."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Company name is required.")

    slug = unique_company_slug(session, name)
    now = datetime.datetime.now(datetime.timezone.utc)

    company = Company(
        name=name,
        slug=slug,
        full_name=(full_name or "").strip() or None,
        email=(email or "").strip() or None,
        phone=(phone or "").strip() or None,
        is_active=True,
        created_at=now,
        created_by_user_id=created_by_user_id,
    )
    session.add(company)
    session.flush()

    session.add(
        CompanyUser(
            company_id=company.id,
            user_id=created_by_user_id,
            role="owner",
            is_active=True,
            created_at=now,
            invited_by_id=None,
        )
    )

    seed_company_settings(session, company.id, company_name=name)
    session.commit()

    seed_chart_of_accounts_for_company(session, company.id)
    seed_default_categories_for_company(session, company.id)

    return company
