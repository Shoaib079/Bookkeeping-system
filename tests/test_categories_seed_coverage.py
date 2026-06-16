"""Unit tests for registry/categories_seed.py — default category seeding.

Covers: _categories_flag_name, seed_default_categories_for_company,
seed_categories_legacy_global. Uses an in-memory SQLite database.
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from db import Base
from models import MigrationFlag, TransactionCategory, TransactionSubcategory
from registry.categories_seed import (
    DEFAULT_CATEGORIES,
    _categories_flag_name,
    seed_categories_legacy_global,
    seed_default_categories_for_company,
)


@pytest.fixture()
def db_session():
    """In-memory SQLite session with the required tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# _categories_flag_name
# ---------------------------------------------------------------------------
class TestCategoriesFlagName:
    def test_format(self):
        assert _categories_flag_name(1) == "categories_seeded_v1:1"
        assert _categories_flag_name(42) == "categories_seeded_v1:42"


# ---------------------------------------------------------------------------
# seed_default_categories_for_company
# ---------------------------------------------------------------------------
class TestSeedDefaultCategoriesForCompany:
    def test_seed_creates_categories_and_subcategories(self, db_session):
        result = seed_default_categories_for_company(db_session, company_id=1)
        assert result["company_id"] == 1
        assert result["already_seeded"] is False
        assert result["created_categories"] > 0
        assert result["created_subcategories"] > 0

        cats = db_session.query(TransactionCategory).filter_by(company_id=1).all()
        assert len(cats) == result["created_categories"]

        total_subs = sum(len(subs) for _, cat_dict in DEFAULT_CATEGORIES.items() for _, subs in cat_dict.items())
        assert result["created_subcategories"] == total_subs

    def test_idempotent_second_call(self, db_session):
        seed_default_categories_for_company(db_session, company_id=1)
        result2 = seed_default_categories_for_company(db_session, company_id=1)
        assert result2["already_seeded"] is True
        assert result2["created_categories"] == 0

    def test_none_company_id_raises(self, db_session):
        with pytest.raises(ValueError, match="company_id is required"):
            seed_default_categories_for_company(db_session, company_id=None)

    def test_existing_categories_marks_seeded(self, db_session):
        """If categories exist but no flag, should set flag and return already_seeded."""
        db_session.add(
            TransactionCategory(
                transaction_type="Expense",
                name="Pre-existing",
                is_active=True,
                company_id=2,
            )
        )
        db_session.commit()

        result = seed_default_categories_for_company(db_session, company_id=2)
        assert result["already_seeded"] is True
        assert result["created_categories"] == 0

        flag = db_session.query(MigrationFlag).filter_by(name=_categories_flag_name(2)).first()
        assert flag is not None

    def test_separate_companies_independent(self, db_session):
        r1 = seed_default_categories_for_company(db_session, company_id=10)
        r2 = seed_default_categories_for_company(db_session, company_id=20)
        assert r1["already_seeded"] is False
        assert r2["already_seeded"] is False
        assert r1["created_categories"] == r2["created_categories"]


# ---------------------------------------------------------------------------
# seed_categories_legacy_global
# ---------------------------------------------------------------------------
class TestSeedCategoriesLegacyGlobal:
    def test_creates_categories(self, db_session):
        result = seed_categories_legacy_global(db_session)
        assert result["created_categories"] > 0
        cats = db_session.query(TransactionCategory).all()
        assert len(cats) == result["created_categories"]

    def test_idempotent(self, db_session):
        seed_categories_legacy_global(db_session)
        result2 = seed_categories_legacy_global(db_session)
        assert result2["created_categories"] == 0

    def test_subcategories_created(self, db_session):
        seed_categories_legacy_global(db_session)
        subs = db_session.query(TransactionSubcategory).all()
        total_expected = sum(
            len(subs_list)
            for cat_dict in DEFAULT_CATEGORIES.values()
            for subs_list in cat_dict.values()
        )
        assert len(subs) == total_expected
