"""SETUP-01 wizard B3 — map answers to company settings after creation."""

from __future__ import annotations

import datetime
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app as erp
import models
from db import Base
from registry.service import get_company_setting, get_module_state, get_setting
from registry.setup01_wizard import (
    POS_IMMEDIATE,
    POS_LATER,
    POS_NO_CARDS,
    SETUP01_SESSION_STEP,
    apply_setup01_wizard_settings,
    begin_setup01_wizard,
    get_setup01_answers,
    is_setup01_active,
    set_setup01_answers,
    setup01_accounting_mode_from_answers,
    setup01_module_flags_from_answers,
    setup01_registry_settings_from_answers,
)

if "streamlit" not in sys.modules:
    import streamlit as st
else:
    st = sys.modules["streamlit"]
    if not isinstance(getattr(st, "session_state", None), dict):
        st.session_state = {}


@pytest.fixture(autouse=True)
def clear_session():
    st.session_state.clear()
    yield
    st.session_state.clear()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as session:
        yield session


def _company(db, name: str, slug: str):
    co = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(co)
    db.flush()
    return co


def _user(db, username="owner1"):
    u = models.User(
        username=username,
        display_name=username.title(),
        password_hash=erp._hash_password("pw"),
        role="owner",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(u)
    db.flush()
    return u


def _answers(**overrides):
    base = {
        "business": "restaurant",
        "pos": POS_LATER,
        "statements": "yes",
        "company_cc": "no",
        "inventory": "no",
        "currency": "no",
        "controls": "balanced",
    }
    base.update(overrides)
    return base


def test_pos_immediate_sets_settlement_false():
    reg = setup01_registry_settings_from_answers(
        _answers(pos=POS_IMMEDIATE, statements="yes")
    )
    assert reg["banking.card_settlement_enabled"] is False
    assert reg["banking.reconciliation_enabled"] is True


def test_pos_later_sets_settlement_true():
    reg = setup01_registry_settings_from_answers(_answers(pos=POS_LATER, statements="no"))
    assert reg["banking.card_settlement_enabled"] is True
    assert reg["banking.reconciliation_enabled"] is False


def test_no_card_payments_sets_settlement_and_reconciliation_false():
    reg = setup01_registry_settings_from_answers(
        _answers(pos=POS_NO_CARDS, statements="skipped")
    )
    assert reg["banking.card_settlement_enabled"] is False
    assert reg["banking.reconciliation_enabled"] is False


def test_statement_import_yes_sets_reconciliation_true():
    reg = setup01_registry_settings_from_answers(
        _answers(pos=POS_IMMEDIATE, statements="yes")
    )
    assert reg["banking.reconciliation_enabled"] is True


def test_company_credit_card_yes_enables_company_card():
    reg = setup01_registry_settings_from_answers(_answers(company_cc="yes"))
    assert reg["banking.company_card_enabled"] is True
    reg_no = setup01_registry_settings_from_answers(_answers(company_cc="no"))
    assert reg_no["banking.company_card_enabled"] is False


def test_inventory_maps_from_user_choice_not_business_type():
    assert setup01_module_flags_from_answers(
        _answers(business="restaurant", inventory="no")
    )["inventory"] is False
    assert setup01_module_flags_from_answers(
        _answers(business="services", inventory="yes")
    )["inventory"] is True


def test_multi_currency_maps_from_user_choice():
    assert setup01_module_flags_from_answers(_answers(currency="yes"))[
        "foreign_currency"
    ] is True
    assert setup01_module_flags_from_answers(_answers(currency="no"))[
        "foreign_currency"
    ] is False


def test_control_level_maps_to_policy_accounting_mode():
    assert setup01_accounting_mode_from_answers(_answers(controls="relaxed")) == "flexible"
    assert setup01_accounting_mode_from_answers(_answers(controls="balanced")) == "standard"
    assert setup01_accounting_mode_from_answers(_answers(controls="strict")) == "strict"


def test_wizard_completed_true_after_apply(db):
    co = _company(db, "Done Co", "done_co")
    db.commit()
    apply_setup01_wizard_settings(db, co.id, _answers())
    assert get_setting(db, "setup.wizard_completed", company_id=co.id) is True


def test_settings_are_company_scoped(db):
    co_a = _company(db, "Co A", "co_a")
    co_b = _company(db, "Co B", "co_b")
    db.commit()
    apply_setup01_wizard_settings(
        db, co_a.id, _answers(pos=POS_LATER, statements="yes", currency="yes")
    )
    apply_setup01_wizard_settings(
        db, co_b.id, _answers(pos=POS_IMMEDIATE, statements="no", currency="no")
    )
    assert get_setting(db, "banking.card_settlement_enabled", company_id=co_a.id) is True
    assert get_setting(db, "banking.card_settlement_enabled", company_id=co_b.id) is False
    assert get_setting(db, "banking.reconciliation_enabled", company_id=co_a.id) is True
    assert get_setting(db, "banking.reconciliation_enabled", company_id=co_b.id) is False
    assert get_company_setting(db, co_a.id, "module.foreign_currency.enabled") is True
    assert get_company_setting(db, co_b.id, "module.foreign_currency.enabled") is False


def test_apply_persists_vertical_and_modules(db):
    co = _company(db, "Full Co", "full_co")
    db.commit()
    answers = _answers(
        business="retail",
        inventory="yes",
        currency="yes",
        controls="strict",
    )
    apply_setup01_wizard_settings(db, co.id, answers)
    assert get_setting(db, "setup.vertical_template", company_id=co.id) == "retail"
    assert get_setting(db, "policy.accounting_mode", company_id=co.id) == "strict"
    inv = get_module_state("inventory", company_id=co.id, session=db)
    fx = get_module_state("foreign_currency", company_id=co.id, session=db)
    assert inv["company_enabled"] is True
    assert fx["company_enabled"] is True


def test_settings_apply_failure_preserves_wizard(db, monkeypatch):
    user = _user(db)
    db.commit()
    begin_setup01_wizard()
    set_setup01_answers(
        company_name="Settings Fail Co",
        business="restaurant",
        pos=POS_LATER,
        statements="yes",
    )
    st.session_state[SETUP01_SESSION_STEP] = "summary"

    def _boom(_session, _cid, _answers):
        raise RuntimeError("settings write failed")

    monkeypatch.setattr(erp, "apply_setup01_wizard_settings", _boom)

    ok, err = erp._submit_setup01_create_company(db, user.id)

    assert ok is False
    assert err == "setup01.settings_failed"
    assert is_setup01_active()
    assert st.session_state[SETUP01_SESSION_STEP] == "summary"
    assert get_setup01_answers()["company_name"] == "Settings Fail Co"
    assert "active_company_id" not in st.session_state
    assert db.query(models.Company).filter_by(name="Settings Fail Co").count() == 1


def test_b2_creation_flow_still_works_with_settings(db):
    user = _user(db)
    db.commit()
    begin_setup01_wizard()
    set_setup01_answers(
        company_name="B2+B3 Co",
        business="restaurant",
        pos=POS_LATER,
        statements="yes",
        company_cc="no",
        inventory="no",
        currency="yes",
        controls="balanced",
    )
    st.session_state[SETUP01_SESSION_STEP] = "summary"

    ok, name = erp._submit_setup01_create_company(db, user.id)

    assert ok is True
    assert name == "B2+B3 Co"
    assert not is_setup01_active()
    co = db.query(models.Company).filter_by(name="B2+B3 Co").one()
    assert get_setting(db, "banking.card_settlement_enabled", company_id=co.id) is True
    assert get_setting(db, "banking.reconciliation_enabled", company_id=co.id) is True
    assert get_setting(db, "banking.company_card_enabled", company_id=co.id) is False
    assert get_company_setting(db, co.id, "module.inventory.enabled") is False
    assert get_company_setting(db, co.id, "module.foreign_currency.enabled") is True
    assert get_setting(db, "setup.wizard_completed", company_id=co.id) is True
    assert st.session_state["active_company_id"] == co.id
