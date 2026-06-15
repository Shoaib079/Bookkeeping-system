"""P3.8-K0 — contract test for the startup wiring conflict resolution plan.

Doc-only guard: verifies the resolution plan exists, addresses the three audit
blockers (R1/R2/R3), and pins the resolutions (explicit gate-approved production
authorization, gate-as-hard-stop, new-empty erp_data.db reconciliation, subprocess
outside the boot session, flag-off unchanged, seeds only after a successful schema
step, hardened new-DB detection, no runtime wiring yet). No DB / runtime involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "P3_8_K0_STARTUP_WIRING_CONFLICT_RESOLUTION.md"
)

REQUIRED_SECTIONS = (
    "allow_production policy",
    "Decision vs. gate authority order",
    "Boot-session / subprocess ordering",
    "is_new_db hardening",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Resolution plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Resolution plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Resolution plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_mentions_r1_r2_r3(doc_text):
    for marker in ("r1", "r2", "r3"):
        assert marker in doc_text.lower(), f"Plan must reference audit blocker {marker.upper()}"


def test_explicit_production_authorization(doc_text):
    lowered = doc_text.lower()
    assert "allow_production" in lowered, "Plan must address allow_production"
    assert "never" in lowered and "silently" in lowered, (
        "Plan must forbid silently enabling allow_production"
    )
    assert "gate" in lowered and "allowed" in lowered, (
        "Production authorization must require gate approval"
    )


def test_gate_is_hard_stop(doc_text):
    lowered = doc_text.lower()
    assert "hard stop" in lowered, "Plan must say the gate is the hard stop"
    assert "decision proposes" in lowered, "Plan must say decision proposes"


def test_resolves_new_empty_erp_data_db(doc_text):
    lowered = doc_text.lower()
    assert "erp_data.db" in lowered, "Plan must reference erp_data.db"
    assert "new" in lowered and "empty" in lowered, (
        "Plan must resolve the new empty erp_data.db conflict"
    )
    assert "upgrade_head" in lowered, "Plan must pin the upgrade_head outcome"


def test_subprocess_runs_outside_boot_session(doc_text):
    lowered = doc_text.lower()
    assert "before" in lowered and "_boot_session" in lowered, (
        "Plan must say the subprocess runs before opening _boot_session"
    )
    assert "database is locked" in lowered or "lock" in lowered, (
        "Plan must address the SQLite lock hazard"
    )


def test_flag_off_path_unchanged(doc_text):
    lowered = doc_text.lower()
    assert "flag-off" in lowered or "flag off" in lowered, "Plan must address the flag-off path"
    assert "unchanged" in lowered, "Flag-off path must be unchanged"
    assert "migrate_schema" in lowered, "Flag-off path must keep migrate_schema"


def test_seeds_only_after_successful_schema_step(doc_text):
    lowered = doc_text.lower()
    assert "seeds run only after" in lowered or "seeds" in lowered and "only after" in lowered, (
        "Plan must say seeds run only after a successful schema step"
    )
    assert "success" in lowered, "Plan must reference a successful schema step"


def test_hardens_new_db_detection(doc_text):
    lowered = doc_text.lower()
    assert "alembic_version" in lowered and "zero" in lowered, (
        "New-DB detection must require no alembic_version and zero app tables"
    )
    assert "partial" in lowered, "Plan must prevent partial DBs being treated as new"


def test_no_runtime_wiring_yet(doc_text):
    lowered = doc_text.lower()
    assert "no runtime wiring yet" in lowered, "Plan must state no runtime wiring yet"
    assert "untouched" in lowered, "Plan must state app.py is untouched"
