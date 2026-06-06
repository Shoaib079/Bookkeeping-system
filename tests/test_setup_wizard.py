"""Tests for Phase 14D-G setup wizard."""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from registry.service import get_setting, get_module_state
from registry.setup_wizard import (
    apply_wizard_choices,
    default_modules_for_vertical,
    is_wizard_complete,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as session:
        yield session


def _company(db):
    co = models.Company(
        name="Acme",
        slug="acme",
        is_active=True,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(co)
    db.commit()
    return co


def test_apply_wizard_persists_registry_defaults(db):
    co = _company(db)
    flags = default_modules_for_vertical("retail")
    apply_wizard_choices(
        db,
        co.id,
        vertical="retail",
        accounting_mode="standard",
        module_flags=flags,
    )
    db.commit()
    assert is_wizard_complete(db, co.id)
    assert get_setting(db, "setup.vertical_template", company_id=co.id) == "retail"
    assert get_setting(db, "policy.accounting_mode", company_id=co.id) == "standard"
    assert get_setting(db, "policy.eod_close", company_id=co.id) == "recommended"
    assert flags["inventory"] is True


def test_module_preference_disables_inventory_in_state(db):
    co = _company(db)
    apply_wizard_choices(
        db,
        co.id,
        vertical="services",
        accounting_mode="flexible",
        module_flags={**default_modules_for_vertical("services"), "inventory": False},
    )
    db.commit()
    state = get_module_state("inventory", company_id=co.id, session=db)
    assert state["company_enabled"] is False
    assert state["disabled_reason"] == "disabled_by_company"
