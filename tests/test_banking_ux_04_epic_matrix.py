"""BANKING-UX-04 — epic matrix: S1–S4 cross-slice contract guardrails."""

from __future__ import annotations

from pathlib import Path

import pytest

import app as erp  # noqa: F401 — production import order

from registry.banking_config import BANKING_WORKFLOW_MODE_IDS
from registry.banking_workflow_contract import (
    workflow_mode_spec,
    validate_banking_workflow_contract,
)
from ui.banking import (
    AT_BANK_TXN_TYPE_IDX,
    at_mobile_type_picker_split,
    at_primary_type_indices,
    at_show_manual_bank_advanced,
    at_show_statement_callout,
    banking_build_section_options,
    banking_section_extra_valid,
    banking_workflow_default_section,
)

ROOT = Path(__file__).resolve().parents[1]
MATCH_POST = ROOT / "reconciliation" / "match_post.py"
POSTING = ROOT / "services" / "posting.py"

EPIC_TEST_FILES = (
    "tests/test_banking_ux_04_audit.py",
    "tests/test_banking_ux_04_s2_workflow_mode_routing.py",
    "tests/test_banking_ux_04_s3_add_transaction_bank_paths.py",
    "tests/test_banking_ux_04_s4_react_workflow_contract.py",
)

EPIC_DOCS = (
    "docs/BANKING_UX_04_AUDIT.md",
    "docs/BANKING_UX_04_REACT_WORKFLOW_CONTRACT.md",
)

_MOB_ROWS = [
    (0, "Sale", "sale"),
    (1, "Expense", "expense"),
    (2, "Purchase", "purchase"),
    (3, "Supplier Payment", "supplier"),
    (4, "Customer Payment", "customer"),
    (5, "Bank Transaction", "bank"),
    (6, "Salary", "salary"),
]


@pytest.mark.parametrize("rel_path", EPIC_TEST_FILES)
def test_epic_test_files_exist(rel_path):
    assert (ROOT / rel_path).is_file()


@pytest.mark.parametrize("rel_path", EPIC_DOCS)
def test_epic_docs_exist(rel_path):
    p = ROOT / rel_path
    assert p.is_file() and p.stat().st_size > 0


def test_epic_contract_validates():
    validate_banking_workflow_contract()


def test_posting_kernel_never_reads_workflow_mode():
    assert "banking.workflow_mode" not in POSTING.read_text(encoding="utf-8")


def test_match_post_never_reads_workflow_mode():
    assert "banking.workflow_mode" not in MATCH_POST.read_text(encoding="utf-8")


@pytest.mark.parametrize("mode", sorted(BANKING_WORKFLOW_MODE_IDS))
def test_banking_chip_order_matches_contract(mode):
    spec = workflow_mode_spec(mode)
    opts = banking_build_section_options(
        workflow_mode=mode,
        show_cockpit=True,
        show_pos_settlement=True,
        show_settings=True,
    )
    ids = [o[0] for o in opts]
    assert ids == list(spec.banking_section_order)


@pytest.mark.parametrize("mode", sorted(BANKING_WORKFLOW_MODE_IDS))
def test_banking_default_landing_matches_contract(mode):
    spec = workflow_mode_spec(mode)
    opts = banking_build_section_options(
        workflow_mode=mode,
        show_cockpit=True,
        show_pos_settlement=False,
        show_settings=False,
    )
    assert banking_workflow_default_section(opts, mode) == spec.banking_default_section


@pytest.mark.parametrize("mode", sorted(BANKING_WORKFLOW_MODE_IDS))
def test_statement_first_accounts_extra_valid_only_for_statement_first(mode):
    extra = banking_section_extra_valid(mode)
    spec = workflow_mode_spec(mode)
    assert extra == spec.banking_advanced_sections


@pytest.mark.parametrize("mode", sorted(BANKING_WORKFLOW_MODE_IDS))
def test_add_transaction_primary_types_match_contract(mode):
    spec = workflow_mode_spec(mode)
    ids = at_primary_type_indices(mode)
    if spec.add_txn_bank_type_in_primary:
        assert AT_BANK_TXN_TYPE_IDX in ids
    else:
        assert AT_BANK_TXN_TYPE_IDX not in ids
    if mode == "manual_first":
        assert ids[0] == AT_BANK_TXN_TYPE_IDX


@pytest.mark.parametrize("mode", sorted(BANKING_WORKFLOW_MODE_IDS))
def test_add_transaction_statement_callout_matches_contract(mode):
    spec = workflow_mode_spec(mode)
    shown = at_show_statement_callout(mode)
    if spec.add_txn_statement_callout == "none":
        assert shown is False
    else:
        assert shown is True


@pytest.mark.parametrize("mode", sorted(BANKING_WORKFLOW_MODE_IDS))
def test_manual_bank_advanced_gate_matches_contract(mode):
    spec = workflow_mode_spec(mode)
    assert at_show_manual_bank_advanced(mode, 0) == spec.add_txn_manual_bank_advanced


@pytest.mark.parametrize("mode", sorted(BANKING_WORKFLOW_MODE_IDS))
def test_bank_transaction_always_reachable_on_mobile(mode):
    primary, advanced = at_mobile_type_picker_split(mode, _MOB_ROWS)
    bank_in_primary = any(r[0] == AT_BANK_TXN_TYPE_IDX for r in primary)
    bank_in_advanced = any(r[0] == AT_BANK_TXN_TYPE_IDX for r in advanced)
    assert bank_in_primary or bank_in_advanced


def test_audit_doc_marks_s4_complete():
    text = (ROOT / "docs" / "BANKING_UX_04_AUDIT.md").read_text(encoding="utf-8").lower()
    assert "banking-ux-04-s4" in text
    assert "complete" in text
