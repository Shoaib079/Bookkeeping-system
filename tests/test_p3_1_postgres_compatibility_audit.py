"""P3.1 — contract test for the PostgreSQL compatibility audit document.

Doc-only guard: verifies the audit exists and carries the required sections,
risk-table coverage, and P3.2 recommendations. No DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_1_POSTGRES_COMPATIBILITY_AUDIT.md"

REQUIRED_SECTIONS = (
    "Executive summary",
    "Risk table",
    "Detailed findings",
    "Query portability findings",
    "Model portability findings",
    "Money precision findings",
    "Test migration plan",
    "Recommended P3.2 tasks",
    "No-change decisions",
)

# Risk-table coverage the audit must call out (case-insensitive substrings).
REQUIRED_RISK_TOPICS = (
    "sqlite sql function",     # SQLite-specific SQL functions / DDL idioms
    "money precision",         # Decimal / money precision
    "foreign key",             # foreign keys
    "timezone",                # datetime / timezone
    "transaction behavior",    # transaction behavior
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists():
    assert DOC_PATH.exists(), f"Audit doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Audit doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_transaction_session_findings_section_present(doc_text):
    lowered = doc_text.lower()
    assert (
        "transaction / session findings" in lowered
        or "transaction/session findings" in lowered
    ), "Missing 'Transaction/session findings' section"


@pytest.mark.parametrize("topic", REQUIRED_RISK_TOPICS)
def test_risk_table_covers_required_topics(doc_text, topic):
    assert topic in doc_text.lower(), f"Risk table missing required topic: {topic!r}"


def test_decimal_money_precision_called_out(doc_text):
    lowered = doc_text.lower()
    assert "decimal" in lowered and "money" in lowered, (
        "Audit must discuss Decimal/money precision"
    )


def test_p3_2_recommendations_present(doc_text):
    lowered = doc_text.lower()
    assert "recommended p3.2 tasks" in lowered, "Missing P3.2 recommendations section"
    assert "p3.2-a" in lowered, "Expected at least one enumerated P3.2 task (P3.2-A)"


def test_no_change_decisions_present(doc_text):
    assert "no-change decisions" in doc_text.lower(), "Missing 'No-change decisions' section"
