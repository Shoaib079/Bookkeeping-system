"""MONO-THEME-02-S0 — Option A+ visual contract (audit-only guard).

Verifies the frozen visual contract doc exists, carries all required sections,
pins mono philosophy (no new palette), semantic color preservation, and the
S1–S5 implementation slice plan. Pure stdlib + design_tokens import; no CSS edits.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ui.design_tokens import (
    COMPONENT_GRAMMAR_TOKENS,
    DARK_COLOR_TOKENS,
    DEPRECATED_ROLE_TOKEN_KEYS,
    LIGHT_COLOR_TOKENS,
    grammar_values_reference_only,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "MONO_THEME_02_VISUAL_CONTRACT.md"
DESIGN_TOKENS_PATH = ROOT / "ui" / "design_tokens.py"

REQUIRED_SECTIONS = (
    "Design philosophy",
    "Sidebar contract",
    "Top bar contract",
    "Dashboard contract",
    "Card contract",
    "Mobile contract",
    "Old vs new preview",
    "Visual scorecard",
    "Implementation slices",
)

SEMANTIC_MEANINGS = (
    "profit",
    "loss",
    "success",
    "warning",
    "danger",
    "matched",
    "review",
    "mismatch",
)

IMPLEMENTATION_SLICES = (
    "mono-theme-02-s0",
    "mono-theme-02-s1",
    "mono-theme-02-s2",
    "mono-theme-02-s3",
    "mono-theme-02-s4",
    "mono-theme-02-s5",
)

_INSPIRED = ("stripe", "quickbooks", "shadcn", "linear")
_REJECTED = ("tailadmin", "rainbow saas", "rainbow dashboards")

_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}")


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"MONO-THEME-02 visual contract missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists_and_nonempty():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing section: {section!r}"


def test_audit_only_no_implementation(doc_text):
    low = doc_text.lower()
    assert "audit only" in low or "audit-only" in low
    assert "no css changes" in low
    assert "no runtime changes" in low or "no python runtime" in low


def test_mono_philosophy_pinned(doc_text):
    low = doc_text.lower()
    assert "accounting-first" in low
    assert "mono surfaces" in low or "mono surface" in low
    assert "#2563eb" in low
    assert "dense but readable" in low or "dense" in low
    assert "one app" in low or "identical" in low
    assert "no rainbow" in low
    assert "color only when meaning" in low or "color = meaning" in low
    for name in _INSPIRED:
        assert name in low, f"Inspiration reference missing: {name}"
    for name in _REJECTED:
        assert name in low, f"Anti-pattern missing: {name}"


def test_no_new_palette_rule(doc_text):
    low = doc_text.lower()
    assert "no new color" in low or "no new palette" in low
    assert "ui/design_tokens.py" in low
    assert "component_grammar_tokens" in low or "--erp-nav-" in low
    assert "existing mono-theme tokens" in low or "existing" in low and "tokens" in low


def test_semantic_colors_preserved_in_contract(doc_text):
    low = doc_text.lower()
    for meaning in SEMANTIC_MEANINGS:
        assert meaning in low, f"Semantic meaning missing from contract: {meaning!r}"
    assert "--theme-success" in doc_text or "success" in low
    assert "--theme-danger" in doc_text or "danger" in low
    assert "immutable" in low or "never flatten" in low


def test_semantic_colors_unchanged_in_token_ssot():
    """Guard: contract audit must not coincide with new accent hex in design_tokens."""
    light = LIGHT_COLOR_TOKENS
    dark = DARK_COLOR_TOKENS
    assert light["--erp-primary-fill"] == "#2563EB"
    assert light["--theme-info"] == "#2563EB"
    assert light["--theme-success"] == "#16A34A"
    assert light["--theme-danger"] == "#DC2626"
    assert light["--theme-warning"] == "#D97706"
    assert dark["--erp-primary-fill"] == "#2563EB"
    assert grammar_values_reference_only()
    assert not DEPRECATED_ROLE_TOKEN_KEYS & frozenset(COMPONENT_GRAMMAR_TOKENS)


def test_sidebar_contract_targets(doc_text):
    low = doc_text.lower()
    assert "subtle" in low and "active" in low
    assert "3px left" in low or "3px left bar" in low
    assert "--erp-nav-active" in doc_text
    assert "giant blue" in low or "filled button" in low or "button-like" in low


def test_dashboard_whitespace_gap_documented(doc_text):
    low = doc_text.lower()
    assert "whitespace" in low or "spacious" in low
    assert "kpi grid" in low or "kpi-grid" in low
    assert "recent activity" in low
    assert "refined" in low and "denser" in low


def test_card_contract_uses_erp_card_tokens(doc_text):
    assert "--erp-card-bg" in doc_text
    assert "--erp-card-border" in doc_text
    assert "--erp-card-radius" in doc_text
    assert "--erp-card-shadow" in doc_text
    assert "no decorative color" in doc_text.lower() or "no decorative colors" in doc_text.lower()


def test_mobile_desktop_parity_contract(doc_text):
    low = doc_text.lower()
    assert "desktop compressed" in low
    assert "--erp-nav-active" in doc_text
    assert "--erp-card-" in doc_text
    assert "--erp-chip-" in doc_text or "chip grammar" in low


def test_visual_scorecard_targets_ten(doc_text):
    low = doc_text.lower()
    assert "scorecard" in low
    assert "10/10" in doc_text
    for axis in ("sidebar", "top bar", "dashboard", "parity", "accounting"):
        assert axis in low, f"Scorecard axis missing: {axis}"


@pytest.mark.parametrize("slice_id", IMPLEMENTATION_SLICES)
def test_implementation_slices_documented(doc_text, slice_id):
    assert slice_id in doc_text.lower(), f"Slice plan missing: {slice_id}"


def test_s0_complete_s1_next(doc_text):
    low = doc_text.lower()
    assert "mono-theme-02-s0" in low
    table_block = low.split("implementation slices")[1][:1200]
    assert "complete" in table_block.split("mono-theme-02-s0")[1][:300]
    assert "mono-theme-02-s1" in low
    assert "sidebar polish" in low or "sidebar" in low.split("mono-theme-02-s1")[1][:200]


def test_doc_no_raw_hex_outside_cited_accent(doc_text):
    """Contract may cite #2563EB; must not introduce new palette hex values."""
    allowed = {"#2563eb", "#2563EB"}
    found = {h for h in _HEX_RE.findall(doc_text)}
    extra = {h for h in found if h.upper() not in {a.upper() for a in allowed}}
    assert not extra, f"Contract introduces palette hex beyond accent: {sorted(extra)}"
