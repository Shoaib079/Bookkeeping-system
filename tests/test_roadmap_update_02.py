"""ROADMAP-UPDATE-02 — contract test for the AI-learning + POS/Z-report roadmap items.

Doc-only guard: verifies ROADMAP.md carries AI-LEARNING-01 (human-first learning),
POS-AI-01..04, the POS auto-post safety gates, and the shared-learning-engine priority
note. Pure stdlib; no app imports; no runtime behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROADMAP = Path(__file__).resolve().parents[1] / "ROADMAP.md"


@pytest.fixture(scope="module")
def text() -> str:
    assert ROADMAP.exists(), f"ROADMAP.md missing: {ROADMAP}"
    return ROADMAP.read_text(encoding="utf-8")


def test_section_exists(text):
    assert "ROADMAP-UPDATE-02" in text, "ROADMAP-UPDATE-02 section must exist"
    assert "documentation only" in text.lower(), "Must be documentation-only"


def test_ai_learning_01(text):
    low = text.lower()
    assert "ai-learning-01" in low, "Must define AI-LEARNING-01"
    assert "human-first" in low, "Must be human-first learning"
    assert "ask the user what they are" in low, "Unknown docs must ask the user"
    for cls in ("expense receipt", "pos/z-report", "bank/card slip", "other"):
        assert cls in low, f"Classification must include {cls!r}"
    assert "posting destination" in low, "User confirms posting destination"
    assert "stores the approved pattern" in low, "System stores the approved pattern"
    assert "prefilled" in low, "Future similar documents are prefilled"


def test_trusted_autopost_gates(text):
    low = text.lower()
    for gate in ("repeated approvals", "high confidence", "owner enablement",
                 "audit", "void"):
        assert gate in low, f"Trusted auto-post must require {gate!r}"


@pytest.mark.parametrize("pos_id", ("POS-AI-01", "POS-AI-02", "POS-AI-03", "POS-AI-04"))
def test_pos_items_present(text, pos_id):
    assert pos_id in text, f"Roadmap must include {pos_id}"


def test_pos_extraction_fields(text):
    low = text.lower()
    for field in ("cash sales", "card sales", "credit sales", "refunds", "voids", "tax", "totals"):
        assert field in low, f"POS-AI-01 must extract {field!r}"
    assert "suggest only" in low, "POS-AI-01 first phase is suggest only"


def test_pos_source_learning(text):
    low = text.lower()
    assert "daily total" in low and "shift total" in low and "terminal total" in low, (
        "POS-AI-02 must learn daily/shift/terminal scope"
    )


def test_pos_autopost_destinations(text):
    low = text.lower()
    assert "card sales clearing" in low, "Card sales → Card Sales Clearing"
    assert "receivables" in low, "Credit sales → Receivables (if supported)"
    assert "existing sales/posting logic" in low or "existing sales/posting" in low, (
        "POS-AI-03 must use existing sales/posting logic"
    )


def test_pos_duplicate_protection(text):
    low = text.lower()
    assert "duplicate" in low and "z-report" in low, "POS-AI-04 duplicate protection"
    for key in ("date", "source", "terminal", "total", "hash"):
        assert key in low, f"Duplicate matching must consider {key!r}"


def test_pos_safety_rules(text):
    low = text.lower()
    assert "never auto-post an unknown format" in low or "never auto-post unknown format" in low, (
        "Must forbid auto-posting unknown formats"
    )
    assert "unclear dates" in low, "Must forbid auto-posting unclear dates"
    assert "duplicate daily report" in low, "Must forbid auto-posting duplicate reports"
    assert "mismatched totals" in low, "Must forbid auto-posting mismatched totals"
    assert "fall back to review" in low, "Must always fall back to review"


def test_shared_engine_priority(text):
    low = text.lower()
    assert "share the same learning engine" in low, "Receipt AI + POS AI share the engine"
    assert "receipt ai goes first" in low or "receipt ai first" in low, (
        "Receipt AI builds document understanding first"
    )
    assert "reuses that pattern" in low, "POS AI reuses the pattern later"
