"""Phase 14D-C — Chart of Accounts and categories per company."""

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
    sys.modules["streamlit"].session_state = {}

from db import Base
import models
from registry.categories_seed import seed_default_categories_for_company
from registry.coa_seed import STANDARD_COA_ACCOUNTS, seed_chart_of_accounts_for_company


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as session:
        yield session


def _company(db, name="Alpha", slug="alpha"):
    co = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(co)
    db.flush()
    return co


class TestCoaPerCompany:
    def test_new_company_gets_full_coa(self, db):
        co = _company(db)
        result = seed_chart_of_accounts_for_company(db, co.id)
        assert result["already_seeded"] is False
        assert result["created"] == len(STANDARD_COA_ACCOUNTS)

        codes = {
            a.account_code
            for a in db.query(models.ChartOfAccounts)
            .filter_by(company_id=co.id)
            .all()
        }
        assert codes == {row[0] for row in STANDARD_COA_ACCOUNTS}

    def test_double_seed_creates_no_duplicates(self, db):
        co = _company(db)
        seed_chart_of_accounts_for_company(db, co.id)
        second = seed_chart_of_accounts_for_company(db, co.id)
        assert second["already_seeded"] is True
        count = db.query(models.ChartOfAccounts).filter_by(company_id=co.id).count()
        assert count == len(STANDARD_COA_ACCOUNTS)

    def test_same_account_codes_across_companies(self, db):
        a = _company(db, "A", "a")
        b = _company(db, "B", "b")
        seed_chart_of_accounts_for_company(db, a.id)
        seed_chart_of_accounts_for_company(db, b.id)

        a_codes = {
            x.account_code
            for x in db.query(models.ChartOfAccounts).filter_by(company_id=a.id).all()
        }
        b_codes = {
            x.account_code
            for x in db.query(models.ChartOfAccounts).filter_by(company_id=b.id).all()
        }
        assert a_codes == b_codes == {row[0] for row in STANDARD_COA_ACCOUNTS}

    def test_company_one_legacy_accounts_not_duplicated(self, db):
        co = _company(db, "Legacy Co", "legacy")
        db.add(
            models.ChartOfAccounts(
                account_code="1000",
                account_name="Cash",
                account_type="Asset",
                company_id=co.id,
            )
        )
        db.commit()

        result = seed_chart_of_accounts_for_company(db, co.id)
        assert result["already_seeded"] is True
        count = db.query(models.ChartOfAccounts).filter_by(company_id=co.id).count()
        assert count == 1


class TestCategoriesPerCompany:
    def test_new_company_gets_categories(self, db):
        co = _company(db)
        result = seed_default_categories_for_company(db, co.id)
        assert result["already_seeded"] is False
        assert result["created_categories"] > 0

        cats = db.query(models.TransactionCategory).filter_by(company_id=co.id).all()
        assert len(cats) >= 3
        assert all(c.company_id == co.id for c in cats)

    def test_double_seed_categories_idempotent(self, db):
        co = _company(db)
        seed_default_categories_for_company(db, co.id)
        second = seed_default_categories_for_company(db, co.id)
        assert second["already_seeded"] is True
        count = db.query(models.TransactionCategory).filter_by(company_id=co.id).count()
        first_count = count
        seed_default_categories_for_company(db, co.id)
        assert db.query(models.TransactionCategory).filter_by(company_id=co.id).count() == first_count

    def test_same_category_names_across_companies(self, db):
        a = _company(db, "A2", "a2")
        b = _company(db, "B2", "b2")
        seed_default_categories_for_company(db, a.id)
        seed_default_categories_for_company(db, b.id)

        a_names = {
            c.name
            for c in db.query(models.TransactionCategory).filter_by(company_id=a.id).all()
        }
        b_names = {
            c.name
            for c in db.query(models.TransactionCategory).filter_by(company_id=b.id).all()
        }
        assert a_names == b_names
