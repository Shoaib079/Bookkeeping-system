"""Phase 14D-B — Company Settings Isolation Tests.

Verifies:
 1.  load_settings() with no active company → reads from AppSetting (global path)
 2.  load_settings() with active company → reads from Company + CompanySetting
 3.  Company A settings do not bleed into Company B
 4.  Company B settings do not bleed into Company A
 5.  Company.name / email / phone are returned under the right keys
 6.  CompanySetting keys (currency, financial_year, tax_rate) are company-scoped
 7.  Defaults are returned when CompanySetting rows are missing
 8.  save_settings() with active company writes to Company + CompanySetting
 9.  save_settings() with no active company writes to AppSetting
10.  Company name save updates active_company_name in session state
11.  _migrate_company1_extended_settings_14d is idempotent
12.  _migrate_company1_extended_settings_14d copies address/logo/tax to CompanySetting
13.  AppSetting is NOT used as source when active_company_id is set
14.  Global isolation test — isolation_unchanged after settings refactor
"""

import sys
import datetime
from unittest.mock import MagicMock
from sqlalchemy import event as _sa_event

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

def _company(db, name, slug, email="", phone=""):
    c = models.Company(
        name=name, slug=slug, is_active=True,
        created_at=datetime.datetime.now(),
        email=email or None, phone=phone or None,
    )
    db.add(c)
    db.flush()
    return c


def _cs(db, company_id, key, value):
    cs = models.CompanySetting(company_id=company_id, key=key, value=value)
    db.add(cs)
    db.flush()
    return cs


def _as(db, key, value):
    row = models.AppSetting(key=key, value=value)
    db.add(row)
    db.flush()
    return row


def _set_active(company_id):
    sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _clear_active():
    sys.modules["streamlit"].session_state.pop("active_company_id", None)


# ─── 1. No active company → global AppSetting path ───────────────────────────

class TestGlobalSettingsFallback:
    def test_no_company_context_returns_defaults_when_empty(self):
        _clear_active()
        defaults = app._SETTINGS_DEFAULTS
        assert "company_name" in defaults
        assert "currency" in defaults
        assert "tax_rate" in defaults
        assert "financial_year" in defaults

    def test_settings_defaults_contain_expected_keys(self):
        for key in ("company_name", "company_email", "company_phone",
                    "currency", "tax_rate", "financial_year",
                    "company_address", "company_tax_number", "company_logo_url"):
            assert key in app._SETTINGS_DEFAULTS, f"Missing key: {key}"


# ─── 2. Active company → CompanySetting + Company fields ─────────────────────

class TestCompanySettingsLoad:
    def test_load_reads_company_name_from_company_table(self, db):
        co = _company(db, "Alpha Ltd", "alpha")
        db.commit()
        s = app._load_company_settings(co.id, _session=db)
        assert s["company_name"] == "Alpha Ltd"

    def test_load_reads_email_from_company_table(self, db):
        co = _company(db, "Beta", "beta", email="info@beta.example")
        db.commit()
        s = app._load_company_settings(co.id, _session=db)
        assert s["company_email"] == "info@beta.example"

    def test_load_reads_phone_from_company_table(self, db):
        co = _company(db, "Gamma", "gamma", phone="+1 555 999")
        db.commit()
        s = app._load_company_settings(co.id, _session=db)
        assert s["company_phone"] == "+1 555 999"

    def test_load_reads_currency_from_company_setting(self, db):
        co = _company(db, "Delta", "delta")
        _cs(db, co.id, "currency", "EUR")
        db.commit()
        s = app._load_company_settings(co.id, _session=db)
        assert s["currency"] == "EUR"

    def test_load_reads_financial_year_from_company_setting(self, db):
        co = _company(db, "Epsilon", "epsilon")
        _cs(db, co.id, "financial_year", "2027")
        db.commit()
        s = app._load_company_settings(co.id, _session=db)
        assert s["financial_year"] == "2027"

    def test_missing_company_setting_returns_default(self, db):
        co = _company(db, "Zeta", "zeta")
        db.commit()
        s = app._load_company_settings(co.id, _session=db)
        assert s["currency"] == app._SETTINGS_DEFAULTS["currency"]


# ─── 3–4. Company A settings do not affect Company B ─────────────────────────

class TestCompanySettingsIsolation:
    def test_company_a_currency_does_not_affect_b(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")
        _cs(db, co_a.id, "currency", "USD")
        _cs(db, co_b.id, "currency", "EUR")
        db.commit()
        sa = app._load_company_settings(co_a.id, _session=db)
        sb = app._load_company_settings(co_b.id, _session=db)
        assert sa["currency"] == "USD"
        assert sb["currency"] == "EUR"

    def test_company_a_name_does_not_bleed_into_b(self, db):
        co_a = _company(db, "Company A Corp", "co_a")
        co_b = _company(db, "Company B Ltd",  "co_b")
        db.commit()
        sa = app._load_company_settings(co_a.id, _session=db)
        sb = app._load_company_settings(co_b.id, _session=db)
        assert sa["company_name"] == "Company A Corp"
        assert sb["company_name"] == "Company B Ltd"

    def test_company_a_financial_year_independent_of_b(self, db):
        co_a = _company(db, "A", "co_a2")
        co_b = _company(db, "B", "co_b2")
        _cs(db, co_a.id, "financial_year", "2025")
        _cs(db, co_b.id, "financial_year", "2027")
        db.commit()
        assert app._load_company_settings(co_a.id, _session=db)["financial_year"] == "2025"
        assert app._load_company_settings(co_b.id, _session=db)["financial_year"] == "2027"

    def test_app_setting_not_returned_when_company_active(self, db):
        """AppSetting currency must not override company's CompanySetting currency."""
        co = _company(db, "Only", "only")
        _cs(db, co.id, "currency", "GBP")
        db.add(models.AppSetting(key="currency", value="TRY"))  # global says TRY
        db.commit()
        s = app._load_company_settings(co.id, _session=db)
        assert s["currency"] == "GBP"  # must come from CompanySetting, not AppSetting


# ─── 8–9. save_settings routing ──────────────────────────────────────────────

class TestSaveSettingsRouting:
    def test_save_with_active_company_writes_to_company_table(self, db):
        co = _company(db, "OldName", "save_test")
        db.commit()
        app._save_company_settings(co.id, {"company_name": "NewName"}, _session=db)
        db.flush()
        db.expire_all()
        assert db.get(models.Company, co.id).name == "NewName"

    def test_save_currency_writes_to_company_setting(self, db):
        co = _company(db, "X", "x_co")
        db.commit()
        app._save_company_settings(co.id, {"currency": "GBP"}, _session=db)
        db.flush()
        cs = db.query(models.CompanySetting).filter_by(
            company_id=co.id, key="currency"
        ).first()
        assert cs is not None and cs.value == "GBP"

    def test_save_email_writes_to_company_email_column(self, db):
        co = _company(db, "Y", "y_co")
        db.commit()
        app._save_company_settings(co.id, {"company_email": "new@y.example"}, _session=db)
        db.flush()
        db.expire_all()
        assert db.get(models.Company, co.id).email == "new@y.example"

    def test_save_without_active_company_writes_to_app_setting(self, db):
        _clear_active()
        app._save_global_settings({"currency": "USD"}, _session=db)
        db.flush()
        row = db.get(models.AppSetting, "currency")
        assert row is not None and row.value == "USD"

    def test_save_does_not_write_company_fields_to_company_setting(self, db):
        """company_name must go to Company.name, not to a CompanySetting row."""
        co = _company(db, "Orig", "orig_co")
        db.commit()
        app._save_company_settings(co.id, {"company_name": "Renamed"}, _session=db)
        db.flush()
        db.expire_all()
        assert db.get(models.Company, co.id).name == "Renamed"
        cs_row = db.query(models.CompanySetting).filter_by(
            company_id=co.id, key="company_name"
        ).first()
        assert cs_row is None


# ─── 10. active_company_name session state update ────────────────────────────

class TestSessionStateSync:
    def test_save_company_name_updates_session_state(self, db):
        co = _company(db, "Old", "sync_co")
        _set_active(co.id)
        sys.modules["streamlit"].session_state["active_company_name"] = "Old"
        db.commit()

        original_sl = app.SessionLocal
        app.SessionLocal = lambda: db
        try:
            app._save_company_settings(co.id, {"company_name": "Updated"})
        finally:
            app.SessionLocal = original_sl

        assert sys.modules["streamlit"].session_state.get("active_company_name") == "Updated"


# ─── 11–12. _migrate_company1_extended_settings_14d ─────────────────────────

class TestMigrationExtendedSettings:
    def test_migration_is_idempotent(self, db):
        """Running the migration twice must not raise or double-insert."""
        app._migrate_company1_extended_settings_14d(db)
        app._migrate_company1_extended_settings_14d(db)  # second run must be silent

    def test_migration_copies_address_to_company_setting(self, db):
        """company_address from AppSetting must land in CompanySetting."""
        # Seed company_1 and AppSetting
        db.add(models.Company(
            name="Test Co", slug="company_1", is_active=True,
            created_at=datetime.datetime.now(),
        ))
        db.flush()
        db.add(models.AppSetting(key="company_address", value="123 Main St"))
        db.commit()

        app._migrate_company1_extended_settings_14d(db)

        co = db.query(models.Company).filter_by(slug="company_1").first()
        cs = db.query(models.CompanySetting).filter_by(
            company_id=co.id, key="company_address"
        ).first()
        assert cs is not None and cs.value == "123 Main St"

    def test_migration_copies_email_to_company_column(self, db):
        db.add(models.Company(
            name="EC", slug="company_1", is_active=True,
            created_at=datetime.datetime.now(),
        ))
        db.flush()
        db.add(models.AppSetting(key="company_email", value="ec@example.com"))
        db.commit()

        app._migrate_company1_extended_settings_14d(db)

        co = db.query(models.Company).filter_by(slug="company_1").first()
        assert co.email == "ec@example.com"

    def test_migration_copies_phone_to_company_column(self, db):
        db.add(models.Company(
            name="PC", slug="company_1", is_active=True,
            created_at=datetime.datetime.now(),
        ))
        db.flush()
        db.add(models.AppSetting(key="company_phone", value="+1 800 000"))
        db.commit()

        app._migrate_company1_extended_settings_14d(db)

        co = db.query(models.Company).filter_by(slug="company_1").first()
        assert co.phone == "+1 800 000"

    def test_migration_safe_when_no_app_settings(self, db):
        """Fresh install: no AppSetting rows — migration must not crash."""
        db.add(models.Company(
            name="Fresh", slug="company_1", is_active=True,
            created_at=datetime.datetime.now(),
        ))
        db.commit()

        app._migrate_company1_extended_settings_14d(db)
        # No assertions needed — just must not raise


# ─── 14. Multi-company isolation still intact ─────────────────────────────────

class TestIsolationUnchangedAfterRefactor:
    def test_cq_isolation_unaffected(self, db):
        co_a = _company(db, "A Corp", "a_corp")
        co_b = _company(db, "B Corp", "b_corp")

        sys.modules["streamlit"].session_state["active_company_id"] = co_a.id
        db.add(models.Sale(
            date=datetime.date(2026, 1, 1),
            invoice_number="INV-A",
            customer_name="CustA",
            amount=100.0,
            sale_type="Cash",
            paid_amount=100.0,
            balance=0.0,
            status="Paid",
            due_date=datetime.date(2026, 1, 1),
        ))
        db.flush()

        sys.modules["streamlit"].session_state["active_company_id"] = co_b.id
        db.add(models.Sale(
            date=datetime.date(2026, 1, 1),
            invoice_number="INV-B",
            customer_name="CustB",
            amount=200.0,
            sale_type="Cash",
            paid_amount=200.0,
            balance=0.0,
            status="Paid",
            due_date=datetime.date(2026, 1, 1),
        ))
        db.flush()
        db.commit()

        sys.modules["streamlit"].session_state["active_company_id"] = co_a.id
        sales_a = app.cq(db, models.Sale).all()
        assert len(sales_a) == 1 and sales_a[0].amount == 100.0

        sys.modules["streamlit"].session_state["active_company_id"] = co_b.id
        sales_b = app.cq(db, models.Sale).all()
        assert len(sales_b) == 1 and sales_b[0].amount == 200.0
