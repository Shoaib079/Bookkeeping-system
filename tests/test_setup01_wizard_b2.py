"""SETUP-01 wizard B2 — Summary creates company, activates, clears wizard."""

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
from registry.company_provision import create_company as real_create_company
from registry.setup01_wizard import (
    SETUP01_SESSION_ANSWERS,
    SETUP01_SESSION_CREATING,
    SETUP01_SESSION_STEP,
    begin_setup01_wizard,
    company_create_kwargs_from_answers,
    discard_setup01_wizard,
    get_setup01_answers,
    is_setup01_active,
    set_setup01_answers,
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


def _prime_summary_answers(*, name: str = "B2 Test Co") -> None:
    begin_setup01_wizard(return_to="picker")
    set_setup01_answers(
        company_name=name,
        company_legal="B2 Test Co Ltd",
        company_email="owner@b2.test",
        company_phone="+90 555 0100",
        business="retail",
        pos="immediate",
        statements="no",
        company_cc="yes",
        inventory="no",
        currency="no",
        controls="strict",
    )
    st.session_state[SETUP01_SESSION_STEP] = "summary"


def test_company_create_kwargs_from_step0_fields():
    kwargs = company_create_kwargs_from_answers(
        {
            "company_name": "  Spice Corner  ",
            "company_legal": "Spice Corner Ltd",
            "company_email": "a@b.com",
            "company_phone": "99",
        }
    )
    assert kwargs == {
        "name": "Spice Corner",
        "full_name": "Spice Corner Ltd",
        "email": "a@b.com",
        "phone": "99",
    }


def test_summary_creates_company_successfully(db):
    user = _user(db)
    db.commit()
    _prime_summary_answers()

    ok, name = erp._submit_setup01_create_company(db, user.id)

    assert ok is True
    assert name == "B2 Test Co"
    row = db.query(models.Company).filter_by(name="B2 Test Co").one()
    assert row.full_name == "B2 Test Co Ltd"
    assert row.email == "owner@b2.test"
    assert row.phone == "+90 555 0100"
    membership = (
        db.query(models.CompanyUser)
        .filter_by(company_id=row.id, user_id=user.id, role="owner")
        .one()
    )
    assert membership.is_active is True


def test_company_activated_after_creation(db):
    user = _user(db)
    db.commit()
    _prime_summary_answers(name="Activated Co")

    erp._submit_setup01_create_company(db, user.id)

    assert st.session_state["active_company_name"] == "Activated Co"
    assert st.session_state["active_company_role"] == "owner"
    assert st.session_state.get("active_company_id") is not None
    assert st.session_state.get("active_company_membership_count") == 1


def test_wizard_state_cleared_and_navigates_home(db):
    user = _user(db)
    db.commit()
    _prime_summary_answers(name="Home Nav Co")

    erp._submit_setup01_create_company(db, user.id)

    assert not is_setup01_active()
    assert SETUP01_SESSION_ANSWERS not in st.session_state
    assert st.session_state["nav_selection"] == "🏠 Home"


def test_creation_failure_preserves_answers(db, monkeypatch):
    user = _user(db)
    db.commit()
    _prime_summary_answers(name="Fail Co")

    def _boom(*_args, **_kwargs):
        raise ValueError("database unavailable")

    monkeypatch.setattr(erp, "create_company", _boom)

    ok, err = erp._submit_setup01_create_company(db, user.id)

    assert ok is False
    assert err == "picker.create_failed"
    assert is_setup01_active()
    assert st.session_state[SETUP01_SESSION_STEP] == "summary"
    assert get_setup01_answers()["company_name"] == "Fail Co"
    assert get_setup01_answers()["business"] == "retail"
    assert SETUP01_SESSION_CREATING not in st.session_state
    assert db.query(models.Company).filter_by(name="Fail Co").count() == 0


def test_double_submit_protection(db, monkeypatch):
    user = _user(db)
    db.commit()
    _prime_summary_answers(name="Double Co")

    calls: list[str] = []

    def _tracked_create(session, **kwargs):
        calls.append(kwargs["name"])
        return real_create_company(session, **kwargs)

    monkeypatch.setattr(erp, "create_company", _tracked_create)
    st.session_state[SETUP01_SESSION_CREATING] = True

    ok, err = erp._submit_setup01_create_company(db, user.id)

    assert ok is False
    assert err == "setup01.create.in_progress"
    assert calls == []
    assert is_setup01_active()


def test_all_entry_points_converge_on_setup01_wizard():
    picker_src = inspect.getsource(erp.render_company_picker)
    main_src = inspect.getsource(erp.main)
    header_src = inspect.getsource(erp._render_hdr_profile_panel_content)
    confirm_src = inspect.getsource(erp._render_company_switch_confirm)

    assert "_start_create_company_wizard" in picker_src
    assert "_start_create_company_wizard" in main_src
    assert "_start_create_company_wizard" in header_src or "_hdr_open_create_after_picker" in confirm_src


def test_no_legacy_create_company_route_remains():
    assert not hasattr(erp, "_render_create_company_form")

    app_src = inspect.getsource(erp)
    assert "_render_create_company_form" not in app_src
    assert "picker_create_company_btn" not in app_src
    assert "picker_new_co_name" not in app_src

    picker_src = inspect.getsource(erp.render_company_picker)
    assert "create_company(" not in picker_src
