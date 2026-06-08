"""P0 — desktop/mobile company switch parity and membership contracts."""

from __future__ import annotations

import datetime
import inspect
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app as erp
import models
from db import Base

ROOT = Path(__file__).resolve().parents[1]

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
    assert "hdr_profile_pop" in src
    assert "show_inline_company_switch=len(_prof_memberships) > 1" in src
    assert 'key_prefix="hdr_prof_co"' in src
    assert "_render_hdr_profile_panel_content" in src


def test_mobile_profile_uses_session_sheet_not_popover():
    src = inspect.getsource(erp._render_hdr_toolbar)
    assert 'key="hdr_mobile_profile_btn"' in src
    assert '_mobile_open_surface("profile")' in src
    mobile_block = src.split("if _is_mobile_ui():")[1].split("else:")[0]
    assert "hdr_profile_pop" not in mobile_block
    sheet_src = inspect.getsource(erp._render_mobile_profile_sheet)
    assert "erp-mobile-profile-host" in sheet_src
    assert "mob_prof_acct" in sheet_src


def test_mobile_header_uses_session_co_switch_sheet_not_popover():
    header_src = inspect.getsource(erp.render_top_header)
    assert 'key="hdr_mobile_co_switch_btn"' in header_src
    assert '_mobile_open_surface("co_switch")' in header_src
    assert 'key="hdr_mobile_co_switch"' not in header_src
    sheet_src = inspect.getsource(erp._render_mobile_co_switch_sheet)
    assert '_render_company_switch_menu(key_prefix="mob_mco")' in sheet_src
    assert "erp-mobile-co-switch-host" in sheet_src


def test_single_company_user_skips_desktop_profile_switch_menu():
    src = inspect.getsource(erp._render_hdr_toolbar)
    assert "show_inline_company_switch=len(_prof_memberships) > 1" in src
    # Guard must be present — single-company users never enter the switch block.
    toolbar_block = src.split("with st.popover(_initials")[1].split("def _title_case_company_word")[0]
    assert toolbar_block.count("_render_company_switch_menu") == 0
    assert "_render_hdr_profile_panel_content" in toolbar_block


def test_company_switch_confirm_uses_mobile_overlay_host():
    src = inspect.getsource(erp._render_company_switch_confirm)
    assert 'key=f"{key_prefix}_confirm_shell"' in src
    assert "erp-co-switch-confirm-host" in src
    assert "st.warning(_warn" in src


def test_company_switch_menu_closes_sheet_before_confirm():
    src = inspect.getsource(erp._render_company_switch_menu)
    assert "_mobile_close_app_surfaces()" in src
    idx_close = src.index("_mobile_close_app_surfaces()")
    idx_confirm = src.index('st.session_state["_confirm_company_switch"] = True')
    assert idx_close < idx_confirm


def test_opening_co_switch_clears_profile_sheet(monkeypatch):
    state = {"_erp_mobile_ui": True, "mob_profile_open": True}
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mobile_open_surface("co_switch")
    assert "mob_profile_open" not in state
    assert state.get("mob_co_switch_open") is True


def test_mobile_company_switch_confirm_css_fixed_above_chrome():
    widgets = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    marker = "/* Company switch confirm — fixed above header"
    assert marker in widgets
    confirm_idx = widgets.index("erp-co-switch-confirm-host")
    assert widgets.rfind("@media (max-width: 968px)", 0, confirm_idx) != -1
    assert "z-index: 10095" in widgets
    assert "z-index: 10090" in widgets
    assert "confirm_shell" in widgets
