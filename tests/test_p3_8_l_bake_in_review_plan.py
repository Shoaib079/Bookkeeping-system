"""P3.8-L — contract test for the Alembic startup bake-in review plan.

Doc-only guard: verifies the bake-in plan exists, carries the required sections, and
pins the invariants (flag default off, migrate_schema retained, rollback disables the
flag, required evidence + do-not-proceed criteria listed, no retirement yet,
PostgreSQL later). No DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_8_L_BAKE_IN_REVIEW_PLAN.md"

REQUIRED_SECTIONS = (
    "Current state",
    "Bake-in scenarios",
    "Required evidence before proceeding",
    "Do-not-proceed criteria",
    "Next-step gates",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Bake-in plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Bake-in plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Bake-in plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_flag_default_off(doc_text):
    lowered = doc_text.lower()
    assert "flag default off" in lowered or "default off" in lowered, (
        "Plan must state the flag defaults off"
    )
    assert "erp_alembic_authoritative" in lowered, "Plan must name the flag"


def test_migrate_schema_retained(doc_text):
    lowered = doc_text.lower()
    assert "migrate_schema" in lowered and "retained" in lowered, (
        "Plan must state migrate_schema is retained"
    )


def test_rollback_disables_flag(doc_text):
    lowered = doc_text.lower()
    assert "disabling the flag" in lowered or "disable the flag" in lowered or "disabling the flag" in lowered, (
        "Rollback must be by disabling the flag"
    )
    assert "rollback" in lowered, "Plan must mention rollback"


def test_required_evidence_listed(doc_text):
    lowered = doc_text.lower()
    assert "full pytest green" in lowered or ("pytest" in lowered and "green" in lowered), (
        "Evidence must require full pytest green"
    )
    assert "no data loss" in lowered, "Evidence must require no data loss"
    assert "no schema drift" in lowered, "Evidence must require no schema drift"
    assert "logs reviewed" in lowered, "Evidence must require logs reviewed"


def test_do_not_proceed_criteria_listed(doc_text):
    lowered = doc_text.lower()
    assert "do-not-proceed" in lowered, "Plan must list do-not-proceed criteria"
    assert "schema mismatch" in lowered, "Do-not-proceed must include schema mismatch"
    assert "unclear" in lowered, "Do-not-proceed must include an unclear startup block"
    assert "user-data concern" in lowered or "user data concern" in lowered, (
        "Do-not-proceed must include a user-data concern"
    )


def test_bake_in_scenarios_present(doc_text):
    lowered = doc_text.lower()
    assert "at_head" in lowered, "Scenarios must include flag-on at_head"
    assert "unstamped legacy" in lowered, "Scenarios must include unstamped legacy"
    assert "fails closed" in lowered, "Scenarios must include ahead/unknown fails closed"
    assert "temporary" in lowered or "throwaway" in lowered, (
        "Strict-new empty DB must be tested only in a temporary DB"
    )


def test_no_retirement_yet(doc_text):
    lowered = doc_text.lower()
    assert "no retirement yet" in lowered, "Plan must state no retirement yet"
    assert "p3.9" in lowered, "Plan must defer retirement to P3.9"


def test_postgresql_later(doc_text):
    lowered = doc_text.lower()
    assert "postgresql" in lowered, "Plan must mention PostgreSQL"
    assert "later" in lowered, "PostgreSQL enablement must be later"


def test_no_runtime_behavior_change(doc_text):
    lowered = doc_text.lower()
    assert "no runtime behavior change" in lowered or "no runtime change" in lowered, (
        "Plan must state no runtime behavior change"
    )
