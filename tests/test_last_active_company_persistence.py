"""P0 — last active company persists across session refresh."""

from __future__ import annotations

import datetime
import inspect
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app as erp
import models
from db import Base

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


def _user(db, username="admin"):
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


def _company(db, name: str, slug: str, *, is_active: bool = True):
    c = models.Company(
        name=name,
        slug=slug,
        is_active=is_active,
        created_at=datetime.datetime.now(),
    )
    db.add(c)
    db.flush()
    return c


def _membership(db, user, company, role="owner", *, is_active: bool = True):
    m = models.CompanyUser(
        company_id=company.id,
        user_id=user.id,
        role=role,
        is_active=is_active,
        created_at=datetime.datetime.now(),
    )
    db.add(m)
    db.flush()
    return m


def _pref_key(user_id: int) -> str:
    return f"user_pref_{user_id}_{erp._USER_PREF_LAST_COMPANY}"


def test_activate_persists_last_active_company(db):
    user = _user(db)
    spice = _company(db, "Spice Corner", "spice_corner")
    india = _company(db, "India Gate", "india_gate")
    _membership(db, user, spice)
    _membership(db, user, india)
    db.commit()

    ok = erp._activate_company_in_session(db, user.id, india.id, membership_count=2)

    assert ok is True
    row = db.get(models.AppSetting, _pref_key(user.id))
    assert row is not None
    assert row.value == str(india.id)


def test_restore_india_gate_after_simulated_refresh(db):
    user = _user(db)
    spice = _company(db, "Spice Corner", "spice_corner")
    india = _company(db, "India Gate", "india_gate")
    _membership(db, user, spice)
    _membership(db, user, india)
    db.commit()

    erp._activate_company_in_session(db, user.id, india.id, membership_count=2)
    st.session_state.clear()

    ok = erp._try_restore_last_active_company(db, user.id)

    assert ok is True
    assert st.session_state["active_company_id"] == india.id
    assert st.session_state["active_company_name"] == "India Gate"
    assert st.session_state["active_company_membership_count"] == 2


def test_restore_spice_corner_after_switch_back(db):
    user = _user(db)
    spice = _company(db, "Spice Corner", "spice_corner")
    india = _company(db, "India Gate", "india_gate")
    _membership(db, user, spice)
    _membership(db, user, india)
    db.commit()

    erp._activate_company_in_session(db, user.id, india.id, membership_count=2)
    erp._activate_company_in_session(db, user.id, spice.id, membership_count=2)
    st.session_state.clear()

    ok = erp._try_restore_last_active_company(db, user.id)

    assert ok is True
    assert st.session_state["active_company_id"] == spice.id
    assert st.session_state["active_company_name"] == "Spice Corner"


def test_restore_fails_when_membership_inactive(db):
    user = _user(db)
    spice = _company(db, "Spice Corner", "spice_corner")
    india = _company(db, "India Gate", "india_gate")
    _membership(db, user, spice)
    _membership(db, user, india, is_active=False)
    db.commit()

    erp._set_user_pref(db, user.id, erp._USER_PREF_LAST_COMPANY, str(india.id))
    db.commit()
    st.session_state.clear()

    ok = erp._try_restore_last_active_company(db, user.id)

    assert ok is False
    assert "active_company_id" not in st.session_state
    row = db.get(models.AppSetting, _pref_key(user.id))
    assert row.value == ""


def test_restore_fails_when_company_inactive(db):
    user = _user(db)
    spice = _company(db, "Spice Corner", "spice_corner")
    india = _company(db, "India Gate", "india_gate", is_active=False)
    _membership(db, user, spice)
    _membership(db, user, india)
    db.commit()

    erp._set_user_pref(db, user.id, erp._USER_PREF_LAST_COMPANY, str(india.id))
    db.commit()
    st.session_state.clear()

    ok = erp._try_restore_last_active_company(db, user.id)

    assert ok is False
    assert "active_company_id" not in st.session_state
    row = db.get(models.AppSetting, _pref_key(user.id))
    assert row.value == ""


def test_switch_still_clears_at_draft(db):
    user = _user(db)
    spice = _company(db, "Spice Corner", "spice_corner")
    india = _company(db, "India Gate", "india_gate")
    _membership(db, user, spice)
    _membership(db, user, india)
    db.commit()

    st.session_state["at_amount_display"] = "555.00"
    st.session_state["at_vendor"] = "Vendor X"
    st.session_state["active_company_id"] = spice.id

    erp._activate_company_in_session(db, user.id, india.id, membership_count=2)

    assert st.session_state["active_company_id"] == india.id
    assert st.session_state.get("at_amount_display") is None
    assert st.session_state.get("at_vendor") is None


def test_main_and_login_use_shared_restore_path():
    main_src = inspect.getsource(erp.main)
    login_src = inspect.getsource(erp._login)
    assert "_try_restore_last_active_company" in main_src
    assert "_try_restore_last_active_company" in login_src


def test_company_picker_uses_activate_helper():
    src = inspect.getsource(erp.render_company_picker)
    assert "_activate_company_in_session" in src
    assert 'st.session_state["active_company_id"]' not in src
