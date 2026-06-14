"""FASTAPI-P2.0 — write API inventory doc contract (no runtime behavior)."""

from __future__ import annotations

from pathlib import Path

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "fastapi_p2_write_api_inventory.md"

REQUIRED_SECTIONS = (
    "## Scope",
    "## Non-goals",
    "## Core invariants",
    "## Write endpoint order",
    "## Write action inventory",
    "## Risk notes",
    "## Testing strategy",
    "## Migration rules",
)

REQUIRED_P2_SLICES = (
    "P2.1",
    "P2.2",
    "P2.3",
    "P2.4",
    "P2.5",
    "P2.6",
    "P2.7",
    "P2.8",
    "P2.9",
)

REQUIRED_INVARIANTS = (
    "No GET commits",
    "JWT RequestContext",
    "X-Company-Id",
    "Never trust company_id from request body",
    "Never delete accounting records",
    "Void → reverse → audit",
)


class TestP2WriteApiInventoryDoc:
    def test_inventory_doc_exists(self):
        assert DOC_PATH.is_file(), f"missing inventory doc: {DOC_PATH}"

    def test_inventory_doc_has_required_sections(self):
        text = DOC_PATH.read_text(encoding="utf-8")
        for heading in REQUIRED_SECTIONS:
            assert heading in text, f"missing section heading: {heading}"

    def test_inventory_doc_lists_p2_endpoint_slices(self):
        text = DOC_PATH.read_text(encoding="utf-8")
        for slice_id in REQUIRED_P2_SLICES:
            assert slice_id in text, f"missing planned slice: {slice_id}"

    def test_inventory_doc_states_core_invariants(self):
        text = DOC_PATH.read_text(encoding="utf-8")
        for phrase in REQUIRED_INVARIANTS:
            assert phrase in text, f"missing invariant phrase: {phrase}"
