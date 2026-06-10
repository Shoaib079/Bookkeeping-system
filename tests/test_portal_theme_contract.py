"""PORTAL-THEME-01 — theming contracts for portal-rendered surfaces.

st.popover bodies, st.dialog modals, and BaseWeb calendar popups render OUTSIDE
[data-testid="stMain"], so stMain-scoped rules never reach them. These contracts
pin the unscoped, token-based portal section in widgets.css so the fix cannot
silently regress (e.g. by someone "tidying" the rules under an stMain prefix).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDGETS = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")

_SECTION_START = "PORTAL-THEME-01"
_SECTION_END = "end PORTAL-THEME-01"


def _portal_section() -> str:
    assert _SECTION_START in WIDGETS, "PORTAL-THEME-01 section missing from widgets.css"
    assert _SECTION_END in WIDGETS, "PORTAL-THEME-01 end marker missing"
    sec = WIDGETS.split(_SECTION_START, 1)[1].split(_SECTION_END, 1)[0]
    # Drop the tail of the section-header comment (split lands mid-comment).
    if "*/" in sec:
        sec = sec.split("*/", 1)[1]
    return sec


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _iter_rules(css: str):
    css = _strip_comments(css)
    stack, buf = [], ""
    for ch in css:
        if ch == "{":
            stack.append(buf.strip())
            buf = ""
        elif ch == "}":
            if buf.strip() and stack:
                yield stack[-1], buf
            buf = ""
            if stack:
                stack.pop()
        else:
            buf += ch


def test_portal_popover_text_rules_present_and_tokenised():
    sec = _portal_section()
    assert 'stPopoverBody"] [data-testid="stMarkdownContainer"] p' in sec
    assert 'stPopoverBody"] [data-testid="stCaptionContainer"]' in sec
    assert "var(--theme-text)" in sec
    assert "var(--theme-caption)" in sec


def test_portal_dialog_text_and_input_rules_present():
    sec = _portal_section()
    assert 'stDialog"] [data-testid="stMarkdownContainer"] p' in sec
    assert 'stDialog"] [data-testid="stTextInput"] input' in sec
    assert 'stDialog"] [data-testid="stTextArea"] textarea' in sec
    assert 'stDialog"] [data-testid="stNumberInput"] input' in sec
    assert "::placeholder" in sec and "var(--theme-muted)" in sec


def test_portal_button_rules_use_primary_fill_grammar():
    sec = _portal_section()
    for needle in (
        'stPopoverBody"] [data-testid="stButton"] button[kind="secondary"]',
        'stPopoverBody"] [data-testid="stButton"] button[kind="primary"]',
        'stDialog"] [data-testid="stButton"] button[kind="primary"]',
        "var(--erp-primary-fill)",
        "var(--erp-primary-fill-hover)",
        "var(--erp-on-primary)",
    ):
        assert needle in sec, f"missing portal button rule piece: {needle}"


def test_portal_calendar_rules_present():
    sec = _portal_section()
    assert 'div[data-baseweb="calendar"]' in sec
    assert 'aria-selected="true"' in sec
    assert "var(--erp-primary-fill)" in sec


def test_portal_rules_never_scoped_to_stmain():
    """The regression guard — portal rules under stMain would silently re-break."""
    sec = _portal_section()
    for selector, _body in _iter_rules(sec):
        assert 'data-testid="stMain"' not in selector, (
            f"portal rule scoped to stMain (will never match portaled DOM): {selector[:120]}"
        )


def test_portal_rules_no_literal_hex():
    sec = _strip_comments(_portal_section())
    hexes = re.findall(r"#[0-9a-fA-F]{3,8}\b", sec)
    assert not hexes, f"portal section must be token-only; found literals: {hexes}"


def test_existing_selectbox_dropdown_fix_untouched():
    """The original portal fix (selectbox virtual dropdown) must remain intact."""
    for needle in (
        "stSelectboxVirtualDropdown",
        'div[data-baseweb="popover"] div[data-baseweb="menu"]',
        "stSelectboxVirtualDropdownEmpty",
    ):
        assert needle in WIDGETS, f"selectbox dropdown fix disturbed: {needle}"
