"""MONO-THEME-01 — contract test for the Option A+ full theme audit.

Doc-only guard: verifies the audit exists, carries all twelve required outputs, pins the
"one app" diagnosis (duplicated component grammar on shared tokens), the keep/change/
not-change lists, the shared-grammar-token recommendation (no new colors), the slice
plan, and the no-change invariants. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "MONO_THEME_01_AUDIT.md"

REQUIRED_SECTIONS = (
    "Executive verdict",
    "What already exists",
    "What to keep",
    "What to change",
    "What NOT to change",
    "Old vs new",
    "Suggested preview boards",
    "Code owner map",
    "Delete / deprecate plan",
    "Slice plan",
    "Risk matrix",
    "Final recommendation",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"MONO-THEME-01 audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"MONO-THEME-01 audit doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "MONO-THEME-01 audit doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_verdict_proceed(doc_text):
    low = doc_text.lower()
    assert "proceed" in low, "Verdict must be proceed/revise/defer"
    assert "no new color system" in low or "no parallel palette" in low or "no new colors" in low, (
        "Must not build a new color system"
    )


def test_one_app_diagnosis(doc_text):
    low = doc_text.lower()
    assert "two apps" in low, "Must address the 'two apps' feeling"
    assert "duplicated component" in low or "defined twice" in low or "duplicated component grammar" in low, (
        "Root cause = duplicated component grammar"
    )
    assert "same tokens" in low or "shared tokens" in low, "Both surfaces share the same tokens"


def test_token_foundation_exists(doc_text):
    low = doc_text.lower()
    assert "ui/design_tokens.py" in low, "Token SSOT cited"
    assert "#2563eb" in low, "Blue accent cited"
    assert "theme-authority-01" in low, "Injection authority cited"
    assert "shadcn" in low, "shadcn philosophy referenced"


def test_keep_semantic_colors(doc_text):
    low = doc_text.lower()
    assert "semantic" in low, "Must keep semantic colors"
    assert "success" in low and "danger" in low and "warning" in low, "Success/danger/warning kept"
    assert "matched" in low and "review" in low and "mismatch" in low, "Recon states kept"


def test_change_role_hues(doc_text):
    low = doc_text.lower()
    assert "role" in low and ("hue" in low or "rainbow" in low), "Role hues / rainbow flagged"
    assert "deprecated_role_token" in low or "deprecat" in low, "Role hues already deprecated"
    assert "mono avatar" in low or "mono avatars" in low, "Move to mono avatars"


def test_shared_grammar_tokens(doc_text):
    low = doc_text.lower()
    assert "--erp-nav-active" in low, "Shared nav-active token"
    assert "--erp-card-" in low, "Shared card token"
    assert "--erp-chip-" in low, "Shared chip token"
    assert "no new color" in low, "By reference — no new colors"


def test_desktop_and_mobile_owners(doc_text):
    low = doc_text.lower()
    assert "ui/theme.css" in low and "ui/widgets.css" in low, "Desktop owners"
    assert "ui/mobile_shell.css" in low and "ui/mobile_components.css" in low, "Mobile owners"
    assert "parity" in low, "Desktop/mobile parity is the objective"


def test_old_vs_new_previews(doc_text):
    low = doc_text.lower()
    for surface in ("dashboard card", "sidebar item", "mobile bottom nav", "banking status", "p&l table"):
        assert surface in low, f"Old-vs-new preview must include {surface!r}"
    assert "light/dark" in low or "dark" in low, "Light/dark notes present"


def test_preview_boards(doc_text):
    low = doc_text.lower()
    assert "board a" in low and "board d" in low, "Must specify preview boards A..D"
    assert "do not generate" in low, "Must not generate images"


def test_slice_plan(doc_text):
    low = doc_text.lower()
    for s in ("mono-theme-01-s1", "mono-theme-01-s3", "mono-theme-01-s5", "mono-theme-01-s7"):
        assert s in low, f"Slice plan must include {s}"


def test_risk_matrix(doc_text):
    low = doc_text.lower()
    assert "dark" in low and "contrast" in low, "Risk: dark contrast"
    assert "over-flatten" in low or "flatten" in low, "Risk: over-flattening financial meaning"
    assert "divergence" in low, "Risk: mobile/desktop divergence"
    assert "react" in low, "Risk: React drift"


def test_no_change_statement(doc_text):
    low = doc_text.lower()
    assert "audit only" in low, "Must state audit-only"
    assert "no css changes" in low, "Must state no CSS changes"
    assert "no removal of semantic colors" in low or "no removal of semantic" in low, (
        "Must not remove semantic colors"
    )
