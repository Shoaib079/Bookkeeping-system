"""P0 — desktop/mobile company switch parity and membership contracts."""

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


def _company(db, name: str, slug: str):
    c = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(c)
    db.flush()
    return c


def _membership(db, user, company, role="owner"):
    m = models.CompanyUser(
        company_id=company.id,
        user_id=user.id,
        role=role,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(m)
    db.flush()
    return m


def test_user_company_memberships_returns_both_companies(db):
    user = _user(db)
    spice = _company(db, "Spice Corner", "spice_corner")
    india = _company(db, "India Gate", "india_gate")
    _membership(db, user, spice, role="owner")
    _membership(db, user, india, role="owner")

    rows = erp._user_company_memberships(db, user.id)

    assert len(rows) == 2
    by_name = {name: (cid, role) for cid, name, role in rows}
    assert "Spice Corner" in by_name
    assert "India Gate" in by_name
    assert by_name["Spice Corner"][1] == "owner"
    assert by_name["India Gate"][1] == "owner"


def test_activate_company_updates_session_keys(db):
    user = _user(db)
    spice = _company(db, "Spice Corner", "spice_corner")
    india = _company(db, "India Gate", "india_gate")
    _membership(db, user, spice, role="owner")
    _membership(db, user, india, role="manager")
    db.commit()

    ok = erp._activate_company_in_session(db, user.id, india.id, membership_count=2)

    assert ok is True
    assert st.session_state["active_company_id"] == india.id
    assert st.session_state["active_company_name"] == "India Gate"
    assert st.session_state["active_company_role"] == "manager"
    assert st.session_state["active_company_membership_count"] == 2


def test_desktop_profile_popover_uses_shared_company_switch_menu():
    src = inspect.getsource(erp._render_hdr_toolbar)
    assert "_render_company_switch_menu" in src
    assert "_legacy_desktop and len(_prof_memberships) > 1" in src
    assert 'key_prefix="hdr_prof_co"' in src
    assert "_user_company_memberships" in src


def test_mobile_header_still_uses_shared_company_switch_menu():
    src = inspect.getsource(erp.render_top_header)
    assert 'key="hdr_mobile_co_switch"' in src
    assert '_render_company_switch_menu(key_prefix="hdr_mco")' in src


def test_single_company_user_skips_desktop_profile_switch_menu():
    src = inspect.getsource(erp._render_hdr_toolbar)
    assert "_legacy_desktop and len(_prof_memberships) > 1" in src
    # Guard must be present — single-company users never enter the switch block.
    toolbar_block = src.split("with st.popover(_initials")[1].split("def _title_case_company_word")[0]
    assert toolbar_block.count("_render_company_switch_menu") == 1
