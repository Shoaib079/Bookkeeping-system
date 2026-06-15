"""P3.8-M — contract test for the local smoke test record.

Doc-only guard: verifies the smoke record exists, documents all three smoke
tests (flag off, flag on, rollback), and pins conclusions including retention
of migrate_schema() and the P3.9 recommendation. No DB / runtime involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "P3_8_M_LOCAL_SMOKE_TEST.md"
)

REQUIRED_SECTIONS = (
    "Environment",
    "Backup verification",
    "Smoke test 1",
    "Smoke test 2",
    "Smoke test 3",
    "Conclusions",
    "Recommendation",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Smoke test record missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Smoke test record missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Smoke test record is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_records_all_three_smoke_tests_pass(doc_text):
    lowered = doc_text.lower()
    for label in ("flag off", "flag on", "rollback"):
        assert label in lowered, f"Smoke record must cover {label!r}"
    assert lowered.count("pass") >= 3


def test_flag_off_uses_migrate_schema_path(doc_text):
    lowered = doc_text.lower()
    assert "migrate_schema" in lowered
    assert "unset erp_alembic_authoritative" in lowered or "flag off" in lowered


def test_flag_on_at_head_verify_only(doc_text):
    lowered = doc_text.lower()
    assert "erp_alembic_authoritative=1" in lowered or "flag on" in lowered
    assert "at_head" in lowered or "verify_only" in lowered


def test_migrate_schema_not_removed_yet(doc_text):
    lowered = doc_text.lower()
    assert "do not remove" in lowered and "migrate_schema" in lowered
    assert "p3.9" in lowered
