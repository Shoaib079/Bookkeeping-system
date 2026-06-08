"""SETUP-01 wizard B1 — navigation, skip branch, session-only (no DB writes)."""

from __future__ import annotations

import sys

import pytest

if "streamlit" not in sys.modules:
    import streamlit as st
else:
    st = sys.modules["streamlit"]
    if not isinstance(getattr(st, "session_state", None), dict):
        st.session_state = {}

from registry.setup01_wizard import (
    POS_IMMEDIATE,
    POS_LATER,
    POS_NO_CARDS,
    SETUP01_SESSION_ACTIVE,
    SETUP01_SESSION_ANSWERS,
    SETUP01_SESSION_STEP,
    apply_skip_side_effects,
    begin_setup01_wizard,
    default_setup01_answers,
    discard_setup01_wizard,
    is_setup01_active,
    next_setup01_step,
    pos_skips_statement_step,
    prev_setup01_step,
    summary_display_rows,
    validate_setup01_step,
)


@pytest.fixture(autouse=True)
def _clear_st_session():
    st.session_state.clear()
    yield
    st.session_state.clear()


def test_default_answers_shape():
    answers = default_setup01_answers()
    assert answers["business"] == "restaurant"
    assert answers["pos"] == POS_LATER
    assert answers["controls"] == "balanced"
    assert answers["skipped_steps"] == []


def test_begin_and_discard_session_keys():
    begin_setup01_wizard(return_to="picker")
    assert is_setup01_active()
    assert st.session_state[SETUP01_SESSION_STEP] == "details"
    assert st.session_state["setup01_return_to"] == "picker"
    assert st.session_state[SETUP01_SESSION_ANSWERS]["company_name"] == ""
    assert st.session_state["setup01_company_name"] == ""
    discard_setup01_wizard()
    assert not is_setup01_active()
    assert SETUP01_SESSION_ANSWERS not in st.session_state


def test_step_forward_sequence():
    answers = default_setup01_answers()
    assert next_setup01_step("details", answers) == "business"
    assert next_setup01_step("business", answers) == "pos"
    assert next_setup01_step("controls", answers) == "summary"


def test_pos_no_cards_skips_statements():
    answers = {**default_setup01_answers(), "pos": POS_NO_CARDS}
    assert pos_skips_statement_step(answers)
    assert next_setup01_step("pos", answers) == "company_cc"
    assert prev_setup01_step("company_cc", answers) == "pos"


def test_pos_with_cards_includes_statements():
    answers = {**default_setup01_answers(), "pos": POS_LATER}
    assert next_setup01_step("pos", answers) == "statements"
    assert prev_setup01_step("company_cc", answers) == "statements"


def test_apply_skip_side_effects_marks_statements_skipped():
    answers = apply_skip_side_effects({**default_setup01_answers(), "pos": POS_NO_CARDS})
    assert answers["statements"] == "skipped"
    assert "statements" in answers["skipped_steps"]


def test_validate_details_requires_name():
    err = validate_setup01_step("details", default_setup01_answers())
    assert err == "company_name_required"
    assert validate_setup01_step("details", {**default_setup01_answers(), "company_name": "Acme"}) is None


def test_summary_rows_omit_statements_when_no_cards():
    rows = summary_display_rows({**default_setup01_answers(), "pos": POS_NO_CARDS})
    keys = [r[0] for r in rows]
    assert "statements" not in keys
    assert "pos" in keys


def test_summary_rows_include_statements_when_cards():
    rows = summary_display_rows({**default_setup01_answers(), "pos": POS_IMMEDIATE})
    assert "statements" in [r[0] for r in rows]


def test_app_main_gate_checks_setup01_before_company_gate():
    import inspect

    import app as erp

    src = inspect.getsource(erp.main)
    setup_idx = src.index("is_setup01_active()")
    company_idx = src.index("if not _current_company_id()")
    assert setup_idx < company_idx


def test_picker_uses_setup01_start_not_create_company():
    import inspect

    import app as erp

    src = inspect.getsource(erp.render_company_picker)
    assert "_start_create_company_wizard" in src
    assert "_render_create_company_form" not in src


def test_setup01_ui_does_not_call_create_or_settings_directly():
    import pathlib

    text_ui = pathlib.Path("ui/setup01_wizard.py").read_text(encoding="utf-8")
    assert "save_company_settings_batch" not in text_ui
    assert "from registry.company_provision import create_company" not in text_ui
