"""FASTAPI-REACT-41 — read-only company settings DTOs and compute."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Company
from registry.service import get_setting
from registry.setup_wizard import is_wizard_complete


@dataclass(frozen=True, slots=True)
class CompanySettingsPage:
    company_id: int
    slug: str
    display_name: str
    legal_name: str | None
    logo_url: str | None
    address: str | None
    phone: str | None
    email: str | None
    tax_number: str | None
    base_currency: str
    tax_rate: float
    fiscal_year_label: str
    document_language: str
    wizard_complete: bool


def _text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def compute_company_settings_page(
    session: Session,
    *,
    company_id: int,
) -> CompanySettingsPage:
    company = session.get(Company, company_id)
    if company is None:
        raise ValueError(f"Company {company_id} not found.")

    display_name = _text(
        get_setting(session, "company.display_name", company_id=company_id)
    ) or (company.name or "My Company")
    legal_name = _text(
        get_setting(session, "company.legal_name", company_id=company_id)
    ) or _text(company.full_name)
    phone = _text(get_setting(session, "company.phone", company_id=company_id)) or _text(
        company.phone
    )
    email = _text(get_setting(session, "company.email", company_id=company_id)) or _text(
        company.email
    )
    tax_rate_raw = get_setting(
        session, "accounting.default_tax_rate", company_id=company_id
    )
    tax_rate = float(tax_rate_raw or 0.0)

    return CompanySettingsPage(
        company_id=company_id,
        slug=company.slug,
        display_name=display_name,
        legal_name=legal_name,
        logo_url=_text(get_setting(session, "company.logo_url", company_id=company_id)),
        address=_text(get_setting(session, "company.address", company_id=company_id)),
        phone=phone,
        email=email,
        tax_number=_text(
            get_setting(session, "company.tax_number", company_id=company_id)
        ),
        base_currency=str(
            get_setting(session, "accounting.base_currency", company_id=company_id)
            or "TRY"
        ),
        tax_rate=tax_rate,
        fiscal_year_label=str(
            get_setting(session, "accounting.fiscal_year_label", company_id=company_id)
            or "2026"
        ),
        document_language=str(
            get_setting(session, "company.document_language", company_id=company_id)
            or "en"
        ),
        wizard_complete=is_wizard_complete(session, company_id),
    )
