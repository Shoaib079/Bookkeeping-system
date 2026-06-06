"""Per-company transaction category seeding — Phase 14D-C."""

from __future__ import annotations

import datetime

from models import MigrationFlag, TransactionCategory, TransactionSubcategory

DEFAULT_CATEGORIES: dict[str, dict[str, list[str]]] = {
    "Expense": {
        "Utilities": ["Electricity", "Water", "Gas"],
        "Payroll": ["Salary", "Bonus"],
        "Cleaning": ["Cleaning Supplies", "Cleaning Service"],
        "Maintenance": ["Equipment Repair", "Building Repair"],
        "Office": ["Office Supplies", "Other"],
    },
    "Purchase": {
        "Inventory": ["General Stock"],
        "Equipment": ["Equipment Purchase"],
        "Supplies": ["General Supplies"],
    },
    "Sale": {
        "General Sales": ["Cash Sale", "Card Sale", "Credit Sale"],
    },
}


def _categories_flag_name(company_id: int) -> str:
    return f"categories_seeded_v1:{company_id}"


def seed_default_categories_for_company(session, company_id: int) -> dict:
    """Seed default categories/subcategories for one company. Idempotent."""
    if company_id is None:
        raise ValueError("company_id is required")

    flag_name = _categories_flag_name(company_id)
    if session.query(MigrationFlag).filter_by(name=flag_name).first():
        return {"company_id": company_id, "created_categories": 0, "already_seeded": True}

    existing = (
        session.query(TransactionCategory)
        .filter_by(company_id=company_id)
        .count()
    )
    if existing > 0:
        session.add(
            MigrationFlag(name=flag_name, applied_at=datetime.date.today())
        )
        session.commit()
        return {"company_id": company_id, "created_categories": 0, "already_seeded": True}

    try:
        created_categories = 0
        created_subcategories = 0
        for txn_type, cats_dict in DEFAULT_CATEGORIES.items():
            for cat_name, subcat_names in cats_dict.items():
                cat = (
                    session.query(TransactionCategory)
                    .filter_by(
                        company_id=company_id,
                        transaction_type=txn_type,
                        name=cat_name,
                    )
                    .first()
                )
                if not cat:
                    cat = TransactionCategory(
                        transaction_type=txn_type,
                        name=cat_name,
                        is_active=True,
                        company_id=company_id,
                    )
                    session.add(cat)
                    session.flush()
                    created_categories += 1

                for sub_name in subcat_names:
                    exists = (
                        session.query(TransactionSubcategory)
                        .filter_by(category_id=cat.id, name=sub_name)
                        .first()
                    )
                    if not exists:
                        session.add(
                            TransactionSubcategory(
                                category_id=cat.id,
                                name=sub_name,
                                is_active=True,
                                company_id=company_id,
                            )
                        )
                        created_subcategories += 1

        session.add(
            MigrationFlag(name=flag_name, applied_at=datetime.date.today())
        )
        session.commit()
        return {
            "company_id": company_id,
            "created_categories": created_categories,
            "created_subcategories": created_subcategories,
            "already_seeded": False,
        }
    except Exception:
        session.rollback()
        raise


def seed_categories_legacy_global(session) -> dict:
    """Pre-multi-company bootstrap without company_id."""
    created_categories = 0
    for txn_type, cats_dict in DEFAULT_CATEGORIES.items():
        for cat_name, subcat_names in cats_dict.items():
            cat = (
                session.query(TransactionCategory)
                .filter_by(transaction_type=txn_type, name=cat_name)
                .first()
            )
            if not cat:
                cat = TransactionCategory(
                    transaction_type=txn_type,
                    name=cat_name,
                    is_active=True,
                )
                session.add(cat)
                session.flush()
                created_categories += 1

            for sub_name in subcat_names:
                exists = (
                    session.query(TransactionSubcategory)
                    .filter_by(category_id=cat.id, name=sub_name)
                    .first()
                )
                if not exists:
                    session.add(
                        TransactionSubcategory(
                            category_id=cat.id,
                            name=sub_name,
                            is_active=True,
                        )
                    )
    session.commit()
    return {"created_categories": created_categories, "legacy_global": True}
