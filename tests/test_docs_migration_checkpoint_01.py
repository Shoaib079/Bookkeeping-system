"""DOCS-MIGRATION-CHECKPOINT-01 — contract test for migration register drift fix.

Doc-only guard: verifies checkpoint doc exists and that ROADMAP + TECH_DEBT
reflect POSTING-SERVICE-01 complete, partial REPORTS/BANKING, and critical path.
Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "docs" / "DOCS_MIGRATION_CHECKPOINT_01.md"
ROADMAP = ROOT / "ROADMAP.md"
TECH_DEBT = ROOT / "docs" / "TECH_DEBT_AND_MIGRATION_CLEANUP.md"
POSTING_STATUS = ROOT / "docs" / "POSTING_SERVICE_01_STATUS.md"

CRITICAL_PATH_ITEMS = (
    "AUTH-SESSION-02-IMPL-3",
    "BANKING-SERVICE-01",
    "P2-HARDEN-01",
    "MONEY-DECIMAL-01",
    "PostgreSQL runtime cutover",
    "React migration",
)


@pytest.fixture(scope="module")
def checkpoint_text() -> str:
    assert CHECKPOINT.exists(), f"Checkpoint doc missing: {CHECKPOINT}"
    return CHECKPOINT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def roadmap_text() -> str:
    return ROADMAP.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def tech_debt_text() -> str:
    return TECH_DEBT.read_text(encoding="utf-8")


class TestCheckpointDoc:
    def test_checkpoint_doc_exists(self):
        assert CHECKPOINT.exists()
        assert CHECKPOINT.stat().st_size > 0

    def test_posting_marked_complete(self, checkpoint_text: str):
        assert "POSTING-SERVICE-01" in checkpoint_text
        assert "Complete" in checkpoint_text

    def test_reports_partial_query_layer(self, checkpoint_text: str):
        assert "REPORTS-SERVICE-01" in checkpoint_text
        assert "Partial" in checkpoint_text
        assert "services/read_" in checkpoint_text
        assert "app.py" in checkpoint_text

    def test_banking_partial_manual_writes(self, checkpoint_text: str):
        assert "BANKING-SERVICE-01" in checkpoint_text
        assert "write_banking" in checkpoint_text
        assert "balance ownership" in checkpoint_text.lower()

    def test_fastapi_not_complete(self, checkpoint_text: str):
        lowered = checkpoint_text.lower()
        assert "fastapi" in lowered
        assert "not complete" in lowered or "partial" in lowered

    def test_postgres_runtime_not_complete(self, checkpoint_text: str):
        assert "SQLite remains runtime" in checkpoint_text

    def test_react_not_started(self, checkpoint_text: str):
        assert "Not started" in checkpoint_text
        assert "ERP_DS_05" in checkpoint_text

    def test_critical_path_listed(self, checkpoint_text: str):
        for item in CRITICAL_PATH_ITEMS:
            assert item in checkpoint_text, f"missing critical path item: {item}"


class TestRoadmapRegister:
    def test_posting_service_complete_in_roadmap(self, roadmap_text: str):
        assert "POSTING-SERVICE-01" in roadmap_text
        idx = roadmap_text.index("#### POSTING-SERVICE-01")
        section = roadmap_text[idx : idx + 1200]
        assert "Complete" in section or "✅" in section

    def test_reports_partial_in_roadmap(self, roadmap_text: str):
        idx = roadmap_text.index("#### REPORTS-SERVICE-01")
        section = roadmap_text[idx : idx + 800]
        assert "Partial" in section or "read_" in section

    def test_banking_partial_in_roadmap(self, roadmap_text: str):
        idx = roadmap_text.index("#### BANKING-SERVICE-01")
        section = roadmap_text[idx : idx + 800]
        assert "Partial" in section or "write_banking" in section

    def test_critical_path_in_current_priority(self, roadmap_text: str):
        idx = roadmap_text.index("## Current priority")
        block = roadmap_text[idx : idx + 2500]
        assert "AUTH-SESSION-02-IMPL-3" in block
        assert "P2-HARDEN-01" in block

    def test_posting_not_keystone_blocker(self, roadmap_text: str):
        idx = roadmap_text.index("## Current priority")
        block = roadmap_text[idx : idx + 2500]
        assert "Key blocker: **POSTING-SERVICE-01**" not in block


class TestTechDebtRegister:
    def test_posting_service_complete(self, tech_debt_text: str):
        idx = tech_debt_text.index("### Tracked migration tasks")
        table = tech_debt_text[idx : idx + 2000]
        assert "**POSTING-SERVICE-01**" in table
        assert "Complete" in table

    def test_reports_partial(self, tech_debt_text: str):
        idx = tech_debt_text.index("### Tracked migration tasks")
        table = tech_debt_text[idx : idx + 2000]
        assert "**REPORTS-SERVICE-01**" in table
        assert "Partial" in table

    def test_banking_partial(self, tech_debt_text: str):
        idx = tech_debt_text.index("### Tracked migration tasks")
        table = tech_debt_text[idx : idx + 2000]
        assert "**BANKING-SERVICE-01**" in table
        assert "Partial" in table

    def test_posting_status_doc_still_complete(self):
        text = POSTING_STATUS.read_text(encoding="utf-8")
        assert "POSTING-SERVICE-01 — Complete" in text
