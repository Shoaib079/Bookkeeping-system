"""P0 — Add Transaction draft must not leak across company switches."""

from __future__ import annotations

import datetime
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    import streamlit as st
else:
    st = sys.modules["streamlit"]
    if not isinstance(getattr(st, "session_state", None), dict):
        st.session_state = {}

import app as erp
import models
from db import Base

_COMPANY_A_DRAFT = {
    "at_amount_display": "1234.56",
    "at_vendor": "Vendor A",
    "at_cust": "Customer A",
    "at_payable_id": 42,
    "at_inv": "INV-A-001",
    "at_cat": "Cat A",
    "at_subcat": "Sub A",
    "mob_at_cat_id": 7,
    "mob_at_subcat_id": 9,
    "at_bank_pay_acct": "Bank A",
    "at_card_bank_acct": "Deposit A",
    "at_cc_card_id": 3,
    "mob_at_picker": "vendor",
    "mob_at_picker_search": "acme",
}


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


def test_clear_company_scoped_session_state_clears_at_draft():
    st.session_state.update(_COMPANY_A_DRAFT)
    erp._clear_company_scoped_session_state()
    for key in erp._COMPANY_SCOPED_AT_KEYS:
        assert key not in st.session_state


def test_activate_company_in_session_clears_at_draft(db):
    user = _user(db)
    spice = _company(db, "Spice Corner", "spice_corner")
    india = _company(db, "India Gate", "india_gate")
    _membership(db, user, spice, role="owner")
    _membership(db, user, india, role="owner")
    db.commit()

    st.session_state.update(_COMPANY_A_DRAFT)
    st.session_state["active_company_id"] = spice.id
    st.session_state["active_company_name"] = spice.name

    ok = erp._activate_company_in_session(db, user.id, india.id, membership_count=2)

    assert ok is True
    assert st.session_state["active_company_id"] == india.id
    assert st.session_state["active_company_name"] == "India Gate"
    for key in _COMPANY_A_DRAFT:
        assert key not in st.session_state


def test_company_a_draft_amount_not_present_after_switch_to_company_b(db):
    """Company A calculator amount must not survive activation of Company B."""
    user = _user(db)
    company_a = _company(db, "Company A", "company_a")
    company_b = _company(db, "Company B", "company_b")
    _membership(db, user, company_a, role="owner")
    _membership(db, user, company_b, role="owner")
    db.commit()

    st.session_state["at_amount_display"] = "9876.54"
    st.session_state["at_vendor"] = "Only In A"
    st.session_state["mob_at_picker"] = "invoice"

    erp._activate_company_in_session(db, user.id, company_b.id, membership_count=2)

    assert st.session_state.get("at_amount_display") is None
    assert st.session_state.get("at_vendor") is None
    assert st.session_state.get("mob_at_picker") is None


def test_activate_helper_is_wired_into_clear(db):
    src = open(erp.__file__, encoding="utf-8").read()
    fn = src.split("def _activate_company_in_session(", 1)[1].split("\ndef ", 1)[0]
    assert "_clear_company_scoped_session_state()" in fn
