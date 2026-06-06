"""Phase 14D-D — Company creation."""

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
import app
import models
from registry.company_provision import create_company, slugify_company_name, unique_company_slug
from registry.coa_seed import STANDARD_COA_ACCOUNTS
from registry.categories_seed import DEFAULT_CATEGORIES


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as session:
        yield session


def _user(db, username="alice"):
    u = models.User(
        username=username,
        password_hash="x",
        role="cashier",
        is_active=True,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(u)
    db.commit()
    return u


class TestCompanyCreation:
    def test_slugify(self):
        assert slugify_company_name("Spice Corner Ltd") == "spice_corner_ltd"

    def test_unique_slug(self, db):
        db.add(
            models.Company(
                name="Test",
                slug="test",
                is_active=True,
                created_at=datetime.datetime.now(datetime.timezone.utc),
            )
        )
        db.commit()
        assert unique_company_slug(db, "Test") == "test_2"

    def test_create_company_owner_membership(self, db):
        user = _user(db)
        co = create_company(
            db,
            name="New Restaurant",
            full_name="New Restaurant LLC",
            email="r@test.com",
            phone="+1",
            created_by_user_id=user.id,
        )
        assert co.id is not None
        assert co.created_by_user_id == user.id

        membership = (
            db.query(models.CompanyUser)
            .filter_by(company_id=co.id, user_id=user.id)
            .one()
        )
        assert membership.role == "owner"
        assert membership.is_active is True

    def test_create_company_seeds_settings_coa_categories(self, db):
        user = _user(db, "bob")
        co = create_company(
            db,
            name="Beta Co",
            created_by_user_id=user.id,
        )

        settings = (
            db.query(models.CompanySetting)
            .filter_by(company_id=co.id)
            .all()
        )
        keys = {s.key for s in settings}
        assert "currency" in keys
        assert "tax_rate" in keys

        coa_count = db.query(models.ChartOfAccounts).filter_by(company_id=co.id).count()
        assert coa_count == len(STANDARD_COA_ACCOUNTS)

        cat_count = db.query(models.TransactionCategory).filter_by(company_id=co.id).count()
        assert cat_count == sum(len(v) for v in DEFAULT_CATEGORIES.values())

    def test_create_company_isolated_from_existing(self, db):
        user = _user(db, "carol")
        existing = models.Company(
            name="Existing",
            slug="existing",
            is_active=True,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(existing)
        db.flush()
        db.add(
            models.ChartOfAccounts(
                account_code="9999",
                account_name="Existing Only",
                account_type="Asset",
                company_id=existing.id,
            )
        )
        db.commit()

        new_co = create_company(db, name="Fresh Co", created_by_user_id=user.id)
        codes = [
            a.account_code
            for a in db.query(models.ChartOfAccounts).filter_by(company_id=new_co.id).all()
        ]
        assert "9999" not in codes
        assert "1000" in codes

    def test_create_company_requires_name(self, db):
        user = _user(db, "dan")
        with pytest.raises(ValueError):
            create_company(db, name="  ", created_by_user_id=user.id)

    def test_zero_membership_login_then_create_activates_company(self, db):
        """14D-D + picker: new user creates first company and enters it."""
        app.DEVELOPMENT_MODE = False
        st = sys.modules["streamlit"].session_state
        st.clear()
        user = _user(db, "erin")
        user.password_hash = app._hash_password("pw")
        db.commit()

        err = app._login(db, "erin", "pw")
        assert err is None
        assert "active_company_id" not in st

        co = create_company(db, name="Erin Co", created_by_user_id=user.id)
        db.commit()
        ok = app._activate_company_in_session(db, user.id, co.id, membership_count=1)
        assert ok is True
        assert st["active_company_id"] == co.id
        assert st["active_company_role"] == "owner"
        assert st["active_company_name"] == "Erin Co"
        st.clear()
