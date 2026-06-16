"""Phase 14D-A — Company Management Data Model Tests.

Verifies:
 1.  Company has full_name column (nullable)
 2.  Company has email column (nullable)
 3.  Company has phone column (nullable)
 4.  Company has created_by_user_id column (nullable FK)
 5.  CompanyUser has invited_by_id column (nullable FK)
 6.  New columns accept None without error (existing data compatibility)
 7.  New columns accept values when provided
 8.  created_by_user_id FK resolves to the correct User
 9.  invited_by_id FK resolves to the correct User
10.  Existing company_1 row style (no new fields) still loads correctly
11.  Existing CompanyUser rows without invited_by_id still load correctly
12.  migrate_schema ALTER TABLE entries are idempotent (re-run does not error)
13.  company_id isolation unchanged after model change
"""

import sys
import datetime
from unittest.mock import MagicMock
from sqlalchemy import event as _sa_event, inspect as _sa_inspect

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock
else:
    _st = sys.modules["streamlit"]
    if not isinstance(getattr(_st, "session_state", None), dict):
        _st.session_state = {}

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app

app.DEVELOPMENT_MODE = False


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def db():
    """Fresh in-memory SQLite per test with before_flush stamping."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @_sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        yield s


# ─── Seed helpers ─────────────────────────────────────────────────────────────

def _user(db, username="alice"):
    u = models.User(
        username=username,
        display_name=username.title(),
        password_hash=app._hash_password("pw"),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(u)
    db.flush()
    return u


def _company(db, name="Acme", slug="acme", creator=None):
    c = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
        created_by_user_id=creator.id if creator else None,
    )
    db.add(c)
    db.flush()
    return c


def _membership(db, user, company, role="owner", invited_by=None):
    m = models.CompanyUser(
        company_id=company.id,
        user_id=user.id,
        role=role,
        is_active=True,
        created_at=datetime.datetime.now(),
        invited_by_id=invited_by.id if invited_by else None,
    )
    db.add(m)
    db.flush()
    return m


# ─── 1–5. New column presence on the ORM model ───────────────────────────────

class TestModelColumns:
    def test_company_has_full_name(self):
        assert hasattr(models.Company, "full_name")

    def test_company_has_email(self):
        assert hasattr(models.Company, "email")

    def test_company_has_phone(self):
        assert hasattr(models.Company, "phone")

    def test_company_has_created_by_user_id(self):
        assert hasattr(models.Company, "created_by_user_id")

    def test_company_user_has_invited_by_id(self):
        assert hasattr(models.CompanyUser, "invited_by_id")


# ─── 6. Existing-row compatibility — all new fields accept None ───────────────

class TestNullCompatibility:
    def test_company_created_without_new_fields(self, db):
        """Simulates an existing company_1 row that has no new data."""
        c = models.Company(
            name="Legacy Co",
            slug="legacy_co",
            is_active=True,
            created_at=datetime.datetime.now(),
            # full_name, email, phone, created_by_user_id all absent → None
        )
        db.add(c)
        db.commit()
        reloaded = db.get(models.Company, c.id)
        assert reloaded.full_name is None
        assert reloaded.email is None
        assert reloaded.phone is None
        assert reloaded.created_by_user_id is None

    def test_membership_created_without_invited_by(self, db):
        u = _user(db)
        c = _company(db)
        m = _membership(db, u, c)
        db.commit()
        reloaded = db.get(models.CompanyUser, m.id)
        assert reloaded.invited_by_id is None


# ─── 7. New fields accept values when provided ────────────────────────────────

class TestNewFieldsAcceptValues:
    def test_company_stores_full_name(self, db):
        c = models.Company(
            name="Acme Corp",
            slug="acme_corp",
            is_active=True,
            created_at=datetime.datetime.now(),
            full_name="Acme Corporation Ltd.",
        )
        db.add(c)
        db.commit()
        assert db.get(models.Company, c.id).full_name == "Acme Corporation Ltd."

    def test_company_stores_email(self, db):
        c = models.Company(
            name="Beta Co", slug="beta_co", is_active=True,
            created_at=datetime.datetime.now(),
            email="hello@betaco.example",
        )
        db.add(c)
        db.commit()
        assert db.get(models.Company, c.id).email == "hello@betaco.example"

    def test_company_stores_phone(self, db):
        c = models.Company(
            name="Gamma Inc", slug="gamma_inc", is_active=True,
            created_at=datetime.datetime.now(),
            phone="+90 555 000 0000",
        )
        db.add(c)
        db.commit()
        assert db.get(models.Company, c.id).phone == "+90 555 000 0000"


# ─── 8. created_by_user_id FK resolves correctly ─────────────────────────────

class TestCreatedByFK:
    def test_created_by_user_id_stores_and_resolves(self, db):
        u = _user(db, "bob")
        c = _company(db, creator=u)
        db.commit()
        reloaded = db.get(models.Company, c.id)
        assert reloaded.created_by_user_id == u.id

    def test_created_by_user_id_accepts_none(self, db):
        c = _company(db, creator=None)
        db.commit()
        assert db.get(models.Company, c.id).created_by_user_id is None


# ─── 9. invited_by_id FK resolves correctly ──────────────────────────────────

class TestInvitedByFK:
    def test_invited_by_id_stores_and_resolves(self, db):
        owner = _user(db, "owner_user")
        member = _user(db, "member_user")
        c = _company(db)
        m = _membership(db, member, c, invited_by=owner)
        db.commit()
        reloaded = db.get(models.CompanyUser, m.id)
        assert reloaded.invited_by_id == owner.id

    def test_invited_by_id_accepts_none(self, db):
        u = _user(db)
        c = _company(db)
        m = _membership(db, u, c)
        db.commit()
        assert db.get(models.CompanyUser, m.id).invited_by_id is None


# ─── 10–11. Existing row patterns still work ─────────────────────────────────

class TestExistingDataPreservation:
    def test_existing_company_style_roundtrip(self, db):
        """company_1-style row: name + slug only, no new fields."""
        c = models.Company(
            name="My Company",
            slug="company_1",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        db.add(c)
        db.commit()
        loaded = db.get(models.Company, c.id)
        assert loaded.name == "My Company"
        assert loaded.slug == "company_1"
        assert loaded.is_active is True
        assert loaded.full_name is None
        assert loaded.created_by_user_id is None

    def test_existing_membership_style_roundtrip(self, db):
        """Phase 14A-style membership: no invited_by_id."""
        u = _user(db)
        c = _company(db)
        m = models.CompanyUser(
            company_id=c.id,
            user_id=u.id,
            role="owner",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        db.add(m)
        db.commit()
        loaded = db.get(models.CompanyUser, m.id)
        assert loaded.company_id == c.id
        assert loaded.user_id == u.id
        assert loaded.role == "owner"
        assert loaded.invited_by_id is None


# ─── 12. migrate_schema idempotency ──────────────────────────────────────────

class TestMigrateSchemaIdempotency:
    def test_alter_table_companies_idempotent(self, db):
        """Running migrate_schema twice on the same schema must not raise."""
        with pytest.warns(DeprecationWarning, match=r"migrate_schema\(\) is deprecated"):
            app.migrate_schema(db)
        with pytest.warns(DeprecationWarning, match=r"migrate_schema\(\) is deprecated"):
            app.migrate_schema(db)  # second run must be silent no-op

    def test_new_columns_exist_after_migrate_schema(self, db):
        """migrate_schema adds the Phase 14D-A columns on a fresh schema."""
        with pytest.warns(DeprecationWarning, match=r"migrate_schema\(\) is deprecated"):
            app.migrate_schema(db)
        inspector = _sa_inspect(db.bind)
        company_cols = {c["name"] for c in inspector.get_columns("companies")}
        cu_cols      = {c["name"] for c in inspector.get_columns("company_users")}
        assert "full_name"          in company_cols
        assert "email"              in company_cols
        assert "phone"              in company_cols
        assert "created_by_user_id" in company_cols
        assert "invited_by_id"      in cu_cols


# ─── 13. company_id isolation unchanged ──────────────────────────────────────

class TestIsolationUnchanged:
    def test_company_id_isolation_still_works(self, db):
        """Adding new columns must not break cq() company isolation."""
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        sys.modules["streamlit"].session_state["active_company_id"] = co_a.id
        db.add(models.FiscalPeriod(
            name="A-Jan",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 31),
            is_closed=False,
        ))
        db.flush()

        sys.modules["streamlit"].session_state["active_company_id"] = co_b.id
        db.add(models.FiscalPeriod(
            name="B-Jan",
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 31),
            is_closed=False,
        ))
        db.flush()
        db.commit()

        sys.modules["streamlit"].session_state["active_company_id"] = co_a.id
        periods = app.cq(db, models.FiscalPeriod).all()
        assert len(periods) == 1
        assert periods[0].name == "A-Jan"
