"""ROADMAP-SYNC-01/02 — contract test for ROADMAP.md register accuracy.

Doc-only guard: verifies status at a glance, current priority, paused-work
gates, completed milestones, and roadmap hygiene rule after service-extraction
audits and post-P3.9-C / external PR register sync. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "ROADMAP.md"

PYTEST_BASELINE = "4654 passed"


@pytest.fixture(scope="module")
def text() -> str:
    assert ROADMAP.exists(), f"ROADMAP.md missing: {ROADMAP}"
    return ROADMAP.read_text(encoding="utf-8")


def _section_after(heading: str, doc: str, *, limit: int = 4000) -> str:
    idx = doc.index(heading)
    return doc[idx : idx + limit]


class TestRoadmapSync01Header:
    def test_roadmap_sync_01_recorded(self, text: str):
        assert "ROADMAP-SYNC-01" in text

    def test_roadmap_sync_02_recorded(self, text: str):
        assert "ROADMAP-SYNC-02" in text

    def test_pytest_baseline_documented(self, text: str):
        assert PYTEST_BASELINE in text


class TestStatusAtAGlance:
    def test_posting_service_complete_not_blocker(self, text: str):
        glance = _section_after("## Status at a glance", text, limit=12000)
        assert "POSTING-SERVICE-01" in glance
        assert "Complete" in glance
        assert "PS-P7" in glance
        assert "not a blocker" in glance

    def test_reports_service_partial(self, text: str):
        glance = _section_after("## Status at a glance", text, limit=12000)
        assert "REPORTS-SERVICE-01" in glance
        assert "Partial" in glance
        assert "services/read_" in glance
        assert "app.py" in glance

    def test_banking_service_partial(self, text: str):
        glance = _section_after("## Status at a glance", text, limit=12000)
        assert "BANKING-SERVICE-01" in glance
        assert "Partial" in glance
        assert "write_banking" in glance
        assert "write_reconciliation" in glance
        assert "match_post" in glance

    def test_auth_session_partial_impl_1_2(self, text: str):
        glance = _section_after("## Status at a glance", text, limit=12000)
        assert "AUTH-SESSION-02" in glance
        assert "Partial" in glance
        assert "IMPL-1" in glance
        assert "IMPL-2" in glance

    def test_receipt_ai_01_complete(self, text: str):
        glance = _section_after("## Status at a glance", text, limit=12000)
        assert "RECEIPT-AI-01" in glance
        assert "Complete" in glance

    def test_receipt_ai_02_impl_1_through_5(self, text: str):
        assert "RECEIPT-AI-02" in text
        idx = text.index("RECEIPT-AI-02")
        line = text[idx : idx + 400]
        assert "IMPL-1" in line
        assert "IMPL-5" in line or "IMPL-1–5" in line or "IMPL-1/2/3/4/5" in line

    def test_fastapi_partial_strong(self, text: str):
        glance = _section_after("## Status at a glance", text, limit=12000)
        assert "FastAPI foundation" in glance
        assert "Partial" in glance
        assert "not production-complete" in glance

    def test_postgresql_test_only(self, text: str):
        glance = _section_after("## Status at a glance", text, limit=12000)
        assert "PostgreSQL runtime" in glance
        assert "test-only" in glance
        assert "SQLite" in glance
        assert "MONEY-DECIMAL-04b" in glance
        assert "MD-04c" in glance

    def test_react_not_started(self, text: str):
        glance = _section_after("## Status at a glance", text, limit=12000)
        assert "React migration" in glance
        assert "Not started" in glance
        assert "ERP_DS_05" in glance


class TestCurrentPriority:
    def test_priority_contains_bs02_characterization(self, text: str):
        block = _section_after("## Current priority", text, limit=3500)
        assert "BS-03" in block or "BS-04" in block
        assert "BS-04" in block or "write_banking" in block

    def test_priority_ordered_migration_path(self, text: str):
        block = _section_after("## Current priority", text, limit=4000)
        assert "BS-03" in block
        assert "AUTH-SESSION-02-IMPL-3" in block
        assert "P2-HARDEN-01" in block
        assert "MONEY-DECIMAL-04c" in block or "MD-04c" in block
        assert "MONEY-DECIMAL-05" in block or "MD-05" in block
        assert "PostgreSQL runtime cutover" in block
        assert "React migration" in block


class TestRoadmapSync02Register:
    def test_external_pr2_error_handling_noted(self, text: str):
        block = _section_after("## Current priority", text, limit=4000)
        assert "PR #2" in block
        assert "error-handling" in block.lower() or "error handling" in block.lower()

    def test_external_pr3_coverage_tests_noted(self, text: str):
        block = _section_after("## Current priority", text, limit=4000)
        assert "PR #3" in block
        assert "226" in block

    def test_p3_9_and_alembic_complete_noted(self, text: str):
        block = _section_after("## Current priority", text, limit=4000)
        assert "P3.9" in block
        assert "ALEMBIC-01" in block
        assert "complete" in block.lower()

    def test_md05_before_pg_cutover(self, text: str):
        block = _section_after("## Current priority", text, limit=4000)
        md05 = block.lower().index("md-05")
        pg = block.lower().index("postgresql runtime cutover")
        assert md05 < pg, "MD-05 must appear before PostgreSQL cutover in priority list"

    def test_completed_milestones_include_alembic_and_p3_9c(self, text: str):
        block = _section_after("## Completed recent milestones", text)
        assert "P3.9-C" in block
        assert "ALEMBIC-01" in block


class TestPausedWorkGate:
    def test_pos_ai_paused_without_user_approval(self, text: str):
        block = _section_after("## Paused / Do Not Start Without User Approval", text)
        lowered = block.lower()
        assert "pos-ai" in lowered or "pos ai" in lowered
        assert "explicitly" in lowered
        assert "z-report" in lowered
        assert "terminal receipt" in lowered
        assert "cash/card reconciliation" in lowered
        assert "ocr" in lowered or "ai provider" in lowered
        assert "trusted receipt auto-post" in lowered


class TestCompletedMilestones:
    def test_recent_milestones_section(self, text: str):
        block = _section_after("## Completed recent milestones", text)
        for item in (
            "NAV-UX-02",
            "AUTH-SESSION-01",
            "AUTH-SESSION-02",
            "DASH-CASH-01",
            "RECEIPT-AI-01",
            "RECEIPT-AI-02",
            "POS-CONFIG-01",
            "FULL-SERVICE-READINESS-AUDIT",
            "BANKING-SERVICE-01",
            "BS-02-CHAR",
            "BS-04",
        ):
            assert item in block, f"missing milestone: {item}"


class TestRoadmapHygieneRule:
    def test_hygiene_rule_exists(self, text: str):
        block = _section_after("## Roadmap hygiene rule", text)
        assert "ROADMAP.md" in block
        assert "doc contract test" in block.lower()
        assert "commit" in block.lower()
        assert "stale blockers" in block.lower()
        assert "test_roadmap_sync_01.py" in block
        assert "ROADMAP-SYNC-02" in text
