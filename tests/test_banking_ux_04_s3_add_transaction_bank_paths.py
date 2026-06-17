"""BANKING-UX-04-S3 — Add Transaction bank-path workflow routing contract tests."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import patch

import app as erp
import pytest

from registry.banking_config import BANKING_WORKFLOW_MODE_DEFAULT
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from ui.banking import (
    AT_BANK_TXN_TYPE_IDX,
    at_apply_add_transaction_landing,
    at_mobile_type_picker_split,
    at_primary_type_indices,
    at_show_manual_bank_advanced,
    at_show_statement_callout,
)

ROOT = Path(__file__).resolve().parents[1]
MATCH_POST = ROOT / "reconciliation" / "match_post.py"
POSTING = ROOT / "services" / "posting.py"

_MOB_ROWS = [
    (0, "Sale", "sale"),
    (1, "Expense", "expense"),
    (2, "Purchase", "purchase"),
    (3, "Supplier Payment", "supplier"),
    (4, "Customer Payment", "customer"),
    (5, "Bank Transaction", "bank"),
    (6, "Salary", "salary"),
]


class TestPrimaryTypeRouting:
    def test_statement_first_hides_bank_type_from_primary(self):
        ids = at_primary_type_indices("statement_first")
        assert AT_BANK_TXN_TYPE_IDX not in ids
        assert 0 in ids

    def test_manual_first_puts_bank_type_first(self):
        ids = at_primary_type_indices("manual_first")
        assert ids[0] == AT_BANK_TXN_TYPE_IDX

    def test_hybrid_keeps_all_types(self):
        ids = at_primary_type_indices("hybrid")
        assert ids == list(range(6))


class TestMobileTypePickerSplit:
    def test_statement_first_splits_bank_to_advanced(self):
        primary, advanced = at_mobile_type_picker_split("statement_first", _MOB_ROWS)
        assert any(r[0] == AT_BANK_TXN_TYPE_IDX for r in advanced)
        assert not any(r[0] == AT_BANK_TXN_TYPE_IDX for r in primary)

    def test_manual_first_keeps_bank_in_primary_first(self):
        primary, advanced = at_mobile_type_picker_split("manual_first", _MOB_ROWS)
        assert primary[0][0] == AT_BANK_TXN_TYPE_IDX
        assert not advanced

    def test_hybrid_no_advanced_split(self):
        primary, advanced = at_mobile_type_picker_split("hybrid", _MOB_ROWS)
        assert len(primary) == len(_MOB_ROWS)
        assert not advanced


class TestAdvancedPanel:
    def test_statement_first_shows_advanced_when_not_on_bank_type(self):
        assert at_show_manual_bank_advanced("statement_first", 0) is True
        assert at_show_manual_bank_advanced("statement_first", AT_BANK_TXN_TYPE_IDX) is False

    def test_hybrid_never_shows_advanced_gate(self):
        assert at_show_manual_bank_advanced("hybrid", 0) is False


class TestLanding:
    def test_manual_first_landing_selects_bank_type_once(self):
        erp.st.session_state.clear()
        at_apply_add_transaction_landing("manual_first")
        assert erp.st.session_state["at_type_idx"] == AT_BANK_TXN_TYPE_IDX
        assert erp.st.session_state["at_workflow_landing_applied"] is True
        erp.st.session_state["at_type_idx"] = 0
        at_apply_add_transaction_landing("manual_first")
        assert erp.st.session_state["at_type_idx"] == 0

    def test_statement_first_does_not_change_default_type(self):
        erp.st.session_state.clear()
        erp.st.session_state["at_type_idx"] = 0
        at_apply_add_transaction_landing("statement_first")
        assert erp.st.session_state["at_type_idx"] == 0


class TestRenderAddTransactionWiring:
    def test_render_add_transaction_uses_workflow_helpers(self):
        src = inspect.getsource(erp.render_add_transaction)
        assert "_banking_workflow_mode" in src
        assert "_at_apply_add_transaction_landing" in src
        assert "_at_primary_type_indices" in src
        assert "_at_render_statement_workflow_callout" in src
        assert "_at_show_manual_bank_advanced" in src
        assert "_at_render_manual_bank_advanced_gate" in src
        assert 'st.session_state["at_workflow_mode"]' in src

    def test_mobile_type_picker_uses_split_helper(self):
        src = inspect.getsource(erp._mob_at_render_txn_type_picker_sheet)
        assert "_at_mobile_type_picker_split" in src
        assert "bank.advanced.section" in src

    def test_mobile_add_transaction_renders_statement_callout(self):
        src = inspect.getsource(erp._render_add_transaction_mobile)
        assert "_at_render_statement_workflow_callout" in src


class TestPostingInvariance:
    def test_s3_does_not_touch_posting_kernel(self):
        assert "banking.workflow_mode" not in POSTING.read_text(encoding="utf-8")

    def test_s3_does_not_touch_match_post(self):
        assert "banking.workflow_mode" not in MATCH_POST.read_text(encoding="utf-8")

    def test_at_helpers_have_no_posting_imports(self):
        text = (ROOT / "ui" / "banking.py").read_text(encoding="utf-8")
        block = text.split("AT_BANK_TXN_TYPE_IDX", 1)[1].split(
            "def banking_match_kind_confidence", 1
        )[0]
        assert "services.posting" not in block
        assert "match_post" not in block


class TestWording:
    _KEYS = (
        "txn.bank_workflow.statement_callout",
        "txn.bank_workflow.statement_alt",
        "txn.bank_workflow.open_statement_import",
        "txn.bank_workflow.manual_advanced_caption",
        "txn.bank_workflow.open_manual_bank",
    )

    @pytest.mark.parametrize("key", _KEYS)
    def test_en_keys_present(self, key):
        assert key in TRANSACTIONAL_EN

    @pytest.mark.parametrize("key", _KEYS)
    def test_tr_keys_present(self, key):
        assert key in TRANSACTIONAL_TR


class TestStatementCalloutVisibility:
    def test_callout_for_statement_and_manual_first_only(self):
        assert at_show_statement_callout("statement_first") is True
        assert at_show_statement_callout("manual_first") is True
        assert at_show_statement_callout("hybrid") is False

    def test_invalid_mode_falls_back_safely(self):
        assert at_show_statement_callout("bogus") is True  # normalize → statement_first
        assert at_primary_type_indices("bogus") == [i for i in range(6) if i != AT_BANK_TXN_TYPE_IDX]
