"""Phase 14D-B2a — Settings / Module Registry Foundation tests."""

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
from registry.loader import (
    get_module_def,
    get_setting_def,
    list_modules,
    list_settings,
    validate_registry,
)
from registry.service import (
    SettingLockError,
    evaluate_lock,
    get_company_milestones,
    get_effective_config,
    get_module_state,
    get_setting,
    save_company_settings_batch,
    set_setting,
)
from registry.settings_catalog import LEGACY_COMPANY_DIRECT_KEYS, LEGACY_COMPANY_SETTING_KEYS


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as session:
        yield session


def _seed_company(db, *, currency="TRY", tax_rate="18.0", financial_year="2026"):
    co = models.Company(
        name="Acme Ltd",
        slug="acme",
        full_name="Acme Legal Ltd",
        email="a@acme.test",
        phone="+90 555",
        is_active=True,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(co)
    db.flush()
    for key, value in [
        ("currency", currency),
        ("tax_rate", tax_rate),
        ("financial_year", financial_year),
        ("company_address", "Istanbul"),
    ]:
        db.add(models.CompanySetting(company_id=co.id, key=key, value=value))
    db.commit()
    return co


class TestRegistryLoader:
    def test_validate_registry_passes(self):
        validate_registry()

    def test_setting_keys_unique(self):
        keys = [s.key for s in list_settings()]
        assert len(keys) == len(set(keys))

    def test_module_ids_unique(self):
        ids = [m.id for m in list_modules()]
        assert len(ids) == len(set(ids))

    def test_critical_settings_have_lock_metadata(self):
        for key in (
            "accounting.base_currency",
            "accounting.fiscal_year_start_month",
            "accounting.multi_currency_enabled",
            "policy.vat_enabled",
        ):
            defn = get_setting_def(key)
            assert defn is not None
            assert defn.lock is not None

    def test_legacy_company_setting_keys_fully_mapped(self):
        mapped = {
            s.legacy_key
            for s in list_settings()
            if s.storage == "company_setting" and s.legacy_key
        }
        assert mapped == LEGACY_COMPANY_SETTING_KEYS

    def test_legacy_company_direct_keys_fully_mapped(self):
        mapped = {
            s.legacy_key
            for s in list_settings()
            if s.storage == "company_column" and s.legacy_key
        }
        assert mapped == LEGACY_COMPANY_DIRECT_KEYS

    def test_planned_modules_marked(self):
        planned = [m for m in list_modules() if m.planned]
        assert {m.id for m in planned} >= {
            "foreign_currency",
            "credit_cards",
            "bank_statement_import",
            "vat_tax",
        }


class TestRegistryService:
    def test_get_setting_reads_live_storage(self, db):
        co = _seed_company(db)
        assert get_setting(db, "accounting.base_currency", company_id=co.id) == "TRY"
        assert get_setting(db, "accounting.default_tax_rate", company_id=co.id) == 18.0
        assert get_setting(db, "company.display_name", company_id=co.id) == "Acme Ltd"
        assert get_setting(db, "company.legal_name", company_id=co.id) == "Acme Legal Ltd"
        assert get_setting(db, "company.email", company_id=co.id) == "a@acme.test"

    def test_get_setting_virtual_returns_default(self, db):
        co = _seed_company(db)
        assert get_setting(db, "accounting.coa_template", company_id=co.id) == "standard"
        assert get_setting(db, "policy.eod_close", company_id=co.id) == "recommended"

    def test_get_effective_config_shape(self, db):
        co = _seed_company(db)
        cfg = get_effective_config(db, co.id, user_id=1)
        assert cfg["company_id"] == co.id
        assert "settings" in cfg
        assert "modules" in cfg
        assert cfg["settings"]["accounting.base_currency"] == "TRY"
        assert any(m["module_id"] == "sales" for m in cfg["modules"])

    def test_get_module_state_defaults(self, db):
        co = _seed_company(db)
        sales = get_module_state("sales", company_id=co.id)
        assert sales["company_enabled"] is True
        assert sales["user_nav_hidden"] is False
        assert sales["locked_disabled"] is False

        fx = get_module_state("foreign_currency", company_id=co.id)
        assert fx["planned"] is True
        assert fx["locked_disabled"] is True
        assert fx["disabled_reason"] == "planned"

    def test_evaluate_lock_blocks_currency_after_first_post(self):
        result = evaluate_lock(
            "accounting.base_currency",
            milestones={"first_posted_at": datetime.datetime.utcnow()},
        )
        assert result["allowed"] is False
        assert result["level"] == "block"

    def test_evaluate_lock_allows_currency_before_first_post(self):
        result = evaluate_lock("accounting.base_currency", milestones={})
        assert result["allowed"] is True

    def test_unknown_setting_raises(self, db):
        co = _seed_company(db)
        with pytest.raises(KeyError):
            get_setting(db, "not.a.real.key", company_id=co.id)

    def test_get_company_milestones_empty_without_journal(self, db):
        co = _seed_company(db)
        ms = get_company_milestones(db, co.id)
        assert ms["first_posted_at"] is None

    def test_get_company_milestones_from_journal_entry_date(self, db):
        co = _seed_company(db)
        db.add(
            models.JournalEntry(
                entry_date=datetime.date(2026, 3, 15),
                description="Opening",
                company_id=co.id,
            )
        )
        db.commit()
        ms = get_company_milestones(db, co.id)
        assert ms["first_posted_at"] is not None
        assert ms["first_posted_at"].date() == datetime.date(2026, 3, 15)

    def test_set_setting_blocks_currency_after_first_post(self, db):
        co = _seed_company(db)
        db.add(
            models.JournalEntry(
                entry_date=datetime.date.today(),
                description="Sale",
                company_id=co.id,
            )
        )
        db.commit()
        with pytest.raises(SettingLockError) as exc_info:
            set_setting(db, "accounting.base_currency", "USD", company_id=co.id)
        assert exc_info.value.level == "block"
        assert exc_info.value.key == "accounting.base_currency"
        assert get_setting(db, "accounting.base_currency", company_id=co.id) == "TRY"

    def test_set_setting_allows_tax_rate_after_first_post(self, db):
        co = _seed_company(db)
        db.add(
            models.JournalEntry(
                entry_date=datetime.date.today(),
                description="Sale",
                company_id=co.id,
            )
        )
        db.commit()
        lock = evaluate_lock(
            "accounting.default_tax_rate",
            milestones=get_company_milestones(db, co.id),
        )
        assert lock["level"] == "warn"
        assert lock["allowed"] is True
        set_setting(db, "accounting.default_tax_rate", 20.0, company_id=co.id)
        db.commit()
        assert get_setting(db, "accounting.default_tax_rate", company_id=co.id) == 20.0

    def test_save_company_settings_batch_blocks_currency(self, db):
        co = _seed_company(db)
        db.add(
            models.JournalEntry(
                entry_date=datetime.date.today(),
                description="Sale",
                company_id=co.id,
            )
        )
        db.commit()
        with pytest.raises(SettingLockError):
            save_company_settings_batch(
                db,
                co.id,
                {"accounting.base_currency": "EUR"},
            )

    def test_get_effective_config_includes_milestones(self, db):
        co = _seed_company(db)
        db.add(
            models.JournalEntry(
                entry_date=datetime.date.today(),
                description="Sale",
                company_id=co.id,
            )
        )
        db.commit()
        cfg = get_effective_config(db, co.id)
        assert cfg["milestones"]["first_posted_at"] is not None


class TestRegistryIntegration:
    def test_app_import_validates_registry(self):
        """Importing app triggers registry validation without breaking startup."""
        import importlib
        import app as erp_app

        importlib.reload(erp_app)
        assert erp_app is not None

    def test_get_module_def_sales(self):
        mod = get_module_def("sales")
        assert mod is not None
        assert mod.nav_page == "💼 Sales"
