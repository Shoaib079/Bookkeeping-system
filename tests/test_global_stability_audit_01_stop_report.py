"""GLOBAL-STABILITY-AUDIT-01 — contract test for the SSOT/regression stop report.

Doc-only guard: verifies the stop report exists, carries the matrix + A-E answers,
names the real fix families + canonical owners, and pins the centralization targets
and the no-change invariants. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "GLOBAL_STABILITY_AUDIT_01_STOP_REPORT.md"
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Stop report missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Stop report missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Stop report is empty"


def test_matrix_columns_present(doc_text):
    low = doc_text.lower()
    for col in ("intended global rule", "canonical owner", "bypasses", "duplicate paths", "global?", "risk"):
        assert col in low, f"Matrix must include column: {col!r}"


def test_fix_families_covered(doc_text):
    low = doc_text.lower()
    for fam in ("date-01", "obs-001", "obs-004", "obs-011", "react-local-obs",
                "banking-ux-02", "banking-ux-03", "nav-ux-02", "post-launch-stability-02"):
        assert fam in low, f"Matrix must cover {fam}"


def test_real_owners_cited(doc_text):
    low = doc_text.lower()
    assert "registry/date_utils.py" in low and "ui/date_input.py" in low, "Date owner cited"
    assert "parse_bound_date" in low, "Date helper cited"
    assert "registry/navigation.py" in low, "Nav SSOT cited"
    assert "match_post" in low, "Dedup authority cited"
    assert "apierror.ts" in low or "errormessagefromcatch" in low, "React error owner cited"


def test_real_tests_cited(doc_text):
    low = doc_text.lower()
    assert "test_at_date_ownership_all_types" in low, "Date ownership guard cited"
    assert "test_obs_001" in low, "OBS-001 test cited"
    assert "test_post_launch_stability_02_obs" in low, "Post-launch suite cited"
    assert "structural_contract" in low, "Nav structural contracts cited"


def test_answers_a_through_e(doc_text):
    low = doc_text.lower()
    assert "truly global" in low, "Answer A"
    assert "only apply on one path" in low or "one path" in low, "Answer B"
    assert "reappear" in low and "ssot" in low, "Answer C"
    assert "need centralization" in low or "centralize" in low, "Answer D"
    assert "company-" in low and "global" in low, "Answer E"


def test_global_set(doc_text):
    low = doc_text.lower()
    assert "nav-arch" in low and "global" in low, "NAV-ARCH is global"
    assert "no-bypass" in low, "Centralization via no-bypass contract tests"


def test_date_is_core_risk(doc_text):
    low = doc_text.lower()
    assert "date" in low and "posted" in low and ("call site" in low or "per-screen" in low or "per call site" in low), (
        "Core mismatch: date posted-date rule realized per call site"
    )


def test_no_change_statement(doc_text):
    low = doc_text.lower()
    assert "no code changes" in low, "Must state no code changes"
    assert "no commits" in low, "Must state no commits"
    assert "no pushes" in low, "Must state no pushes"
    assert "stop report" in low, "Must be a stop report"
