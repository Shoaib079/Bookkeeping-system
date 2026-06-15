"""POS-CONFIG-01 — contract tests for sales/POS configuration spec + roadmap.

Doc-only guard: verifies spec and ROADMAP carry per-company configuration
domains, assist-first auto-post defaults, and settings→AI behaviour rules.
Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "POS_CONFIG_01_SPEC.md"
ROADMAP = ROOT / "ROADMAP.md"


@pytest.fixture(scope="module")
def spec_text() -> str:
    assert SPEC.exists(), f"Spec missing: {SPEC}"
    return SPEC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def roadmap_text() -> str:
    assert ROADMAP.exists()
    return ROADMAP.read_text(encoding="utf-8")


def test_spec_exists(spec_text):
    assert "POS-CONFIG-01" in spec_text
    assert "documentation only" in spec_text.lower()


def test_no_company_wide_assumptions(spec_text, roadmap_text):
    for text in (spec_text, roadmap_text):
        low = text.lower()
        assert "no company-wide assumptions" in low
        assert "company_id" in low or "per company" in low or "each company" in low


def test_sales_and_pos_settings_page(spec_text):
    assert "Sales & POS Configuration" in spec_text
    assert "pos.sales_source" in spec_text


@pytest.mark.parametrize(
    "option",
    (
        "external_restaurant",
        "builtin_erp",
        "hybrid",
        "z-report",
        "terminal slip",
        "bank settlement",
        "manual_only",
        "suggest only",
        "trusted",
    ),
)
def test_configuration_options_documented(spec_text, option):
    assert option in spec_text.lower(), f"Spec must document {option!r}"


def test_duplicate_protection_keys(spec_text):
    low = spec_text.lower()
    for key in ("date", "terminal", "report number", "batch", "total", "hash"):
        assert key in low, f"Duplicate protection must mention {key!r}"


def test_settings_drive_ai(spec_text, roadmap_text):
    assert "settings determine ai behaviour" in spec_text.lower()
    assert "settings determine ai behaviour" in roadmap_text.lower()


def test_assist_first_default(spec_text):
    low = spec_text.lower()
    assert "suggest_only" in low or "suggest only" in low
    assert "default" in low and "trusted" in low


def test_roadmap_section(roadmap_text):
    assert "POS-CONFIG-01" in roadmap_text
    assert "POS_CONFIG_01_SPEC.md" in roadmap_text
    assert "POS-CONFIG-01-IMPL-1" in roadmap_text


def test_pos_config_before_pos_ai(roadmap_text):
    low = roadmap_text.lower()
    assert "pos-config-01" in low
    assert "precedes pos-ai" in low or "before pos-ai" in low
