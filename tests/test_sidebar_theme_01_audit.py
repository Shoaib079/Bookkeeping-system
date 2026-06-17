"""SIDEBAR-THEME-01 — contract test for the sidebar theming audit (Option A+ blend).

Doc-only guard: verifies the audit exists, carries the required outputs, records that
the chosen theme is already the token foundation, covers desktop + mobile, defines the
by-reference nav-state tokens (no new colors), and pins the CSS/token-only boundaries.
Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "SIDEBAR_THEME_01_AUDIT.md"

REQUIRED_SECTIONS = (
    "Current sidebar architecture",
    "Gap vs Option A+",
    "Recommended implementation",
    "Implementation slices",
    "Risks",
    "Boundaries",
    "Recommendation",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Sidebar theme audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Sidebar theme audit doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Sidebar theme audit doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_chosen_theme_already_token_foundation(doc_text):
    low = doc_text.lower()
    assert "ui/design_tokens.py" in low, "Must cite the token SSOT"
    assert "--erp-primary-fill" in low and "#2563eb" in low, "Must cite the blue accent token"
    assert "neutral surfaces" in low, "Must note neutral surfaces"
    assert "already" in low and "foundation" in low, "Must state the theme is already the foundation"


def test_desktop_and_mobile_covered(doc_text):
    low = doc_text.lower()
    assert "_render_navigation_tree" in low and "3189" in doc_text, "Desktop sidebar render anchored"
    assert "ui/theme.css" in low, "Desktop CSS owner"
    assert "_mobile_bottom_nav" in low, "Mobile bottom nav covered"
    assert "ui/mobile_shell.css" in low or "mobile_components.css" in low, "Mobile CSS owner"
    assert "parity" in low, "Must require desktop/mobile parity"


def test_by_reference_tokens_no_new_colors(doc_text):
    low = doc_text.lower()
    assert "--erp-nav-active-bg" in low and "--erp-nav-active-bar" in low, "Nav-state tokens defined"
    assert "color-mix" in low, "Tokens are color-mix references"
    assert "no new color" in low, "No new color values (mono + one accent preserved)"


def test_active_grammar_and_section_header(doc_text):
    low = doc_text.lower()
    assert "left accent bar" in low or "accent bar" in low, "Active item gets a left accent bar"
    assert "erp-nav-section-hdr" in low, "Section header class cited"
    assert "uppercase" in low, "Section header is muted uppercase caption"
    assert "active" in low and "focus" in low, "Blue reserved for active + focus"


def test_slices(doc_text):
    low = doc_text.lower()
    for s in ("sidebar-theme-01-s1", "sidebar-theme-01-s2", "sidebar-theme-01-s3", "sidebar-theme-01-s4"):
        assert s in low, f"Slice plan must include {s}"


def test_theme_authority_and_react_contract(doc_text):
    low = doc_text.lower()
    assert "theme-authority-01" in low, "Must route through THEME-AUTHORITY-01 injection"
    assert "react design contract" in low or "react_design_contract" in low or "react design-contract" in low, (
        "Must record tokens in the React design contract"
    )


def test_recommendation_proceed_css_only(doc_text):
    low = doc_text.lower()
    assert "proceed" in low, "Recommendation must be PROCEED"
    assert "css/token-only" in low or "css / token-only" in low or "css-only" in low, (
        "Must be CSS/token-only"
    )


def test_boundaries_protect_nav_and_posting(doc_text):
    low = doc_text.lower()
    assert "never touch" in low, "Must list never-touch boundaries"
    assert "_render_navigation_tree" in low and "registry/navigation.py" in low, (
        "Must protect nav logic + registry"
    )
    assert "services/posting.py" in low, "Must protect posting"


def test_no_change_statement(doc_text):
    low = doc_text.lower()
    assert "audit only" in low, "Must state audit-only"
    assert "no code changes" in low, "Must state no code changes"
    assert "no new color values" in low, "Must state no new color values"
    assert "no nav-structure change" in low or "no nav structure change" in low, (
        "Must state no nav-structure change"
    )
