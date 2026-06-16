"""Unit tests for registry/banking_config.py — banking workspace config helpers.

Covers: _parse_kind_csv, banking_normalize_batch_kinds, banking_batch_safe_kinds,
banking_confidence_meets_batch_threshold, banking_sort_queue_rows,
banking_accounting_preview, banking_batch_review_reason_for_row,
and the session-dependent setting helpers via mock.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from registry.banking_config import (
    BANKING_BATCH_SAFE_KINDS,
    IMPORT_TAB_IDS,
    LANDING_IDS,
    QUEUE_DENSITY_IDS,
    QUEUE_SORT_IDS,
    REVIEW_KIND_IDS,
    _parse_kind_csv,
    banking_accounting_preview,
    banking_batch_confidence_threshold,
    banking_batch_eligible_kinds,
    banking_batch_posting_enabled,
    banking_batch_review_reason_for_row,
    banking_batch_safe_kinds,
    banking_review_required_kinds,
    banking_confidence_meets_batch_threshold,
    banking_default_import_tab,
    banking_normalize_batch_kinds,
    banking_queue_density,
    banking_queue_sort,
    banking_resolve_landing,
    banking_show_accounting_previews,
    banking_show_confidence_chips,
    banking_sort_queue_rows,
)


# ---------------------------------------------------------------------------
# _parse_kind_csv
# ---------------------------------------------------------------------------
class TestParseKindCsv:
    def test_empty(self):
        assert _parse_kind_csv(None, allowed=REVIEW_KIND_IDS) == frozenset()
        assert _parse_kind_csv("", allowed=REVIEW_KIND_IDS) == frozenset()

    def test_valid_kinds(self):
        result = _parse_kind_csv("payroll,vendor", allowed=REVIEW_KIND_IDS)
        assert result == frozenset({"payroll", "vendor"})

    def test_invalid_kinds_filtered(self):
        result = _parse_kind_csv("payroll,bogus,vendor", allowed=REVIEW_KIND_IDS)
        assert result == frozenset({"payroll", "vendor"})

    def test_whitespace_stripped(self):
        result = _parse_kind_csv(" payroll , vendor ", allowed=REVIEW_KIND_IDS)
        assert result == frozenset({"payroll", "vendor"})


# ---------------------------------------------------------------------------
# banking_batch_safe_kinds / banking_normalize_batch_kinds
# ---------------------------------------------------------------------------
class TestBatchKinds:
    def test_safe_kinds_invariant(self):
        assert banking_batch_safe_kinds() == frozenset({"bank_fee"})

    def test_normalize_from_string(self):
        assert banking_normalize_batch_kinds("bank_fee") == frozenset({"bank_fee"})

    def test_normalize_from_frozenset(self):
        assert banking_normalize_batch_kinds(frozenset({"bank_fee", "other"})) == frozenset({"bank_fee"})

    def test_normalize_none(self):
        assert banking_normalize_batch_kinds(None) == frozenset()

    def test_normalize_invalid_string(self):
        assert banking_normalize_batch_kinds("invalid_kind") == frozenset()


# ---------------------------------------------------------------------------
# banking_confidence_meets_batch_threshold
# ---------------------------------------------------------------------------
class TestConfidenceThreshold:
    def test_low_always_rejected(self):
        assert banking_confidence_meets_batch_threshold("high", "low") is False
        assert banking_confidence_meets_batch_threshold("high_and_medium", "low") is False

    def test_high_threshold_accepts_high(self):
        assert banking_confidence_meets_batch_threshold("high", "high") is True

    def test_high_threshold_rejects_medium(self):
        assert banking_confidence_meets_batch_threshold("high", "medium") is False

    def test_medium_threshold_accepts_high(self):
        assert banking_confidence_meets_batch_threshold("high_and_medium", "high") is True

    def test_medium_threshold_accepts_medium(self):
        assert banking_confidence_meets_batch_threshold("high_and_medium", "medium") is True


# ---------------------------------------------------------------------------
# banking_sort_queue_rows
# ---------------------------------------------------------------------------
class TestSortQueueRows:
    ROWS = [
        {"date": "2026-01-03", "amount": 100, "confidence": "low", "import_row_index": 3},
        {"date": "2026-01-01", "amount": 500, "confidence": "high", "import_row_index": 1},
        {"date": "2026-01-02", "amount": 200, "confidence": "medium", "import_row_index": 2},
    ]

    def test_sort_by_date(self):
        result = banking_sort_queue_rows(self.ROWS, sort_key="date")
        dates = [r["date"] for r in result]
        assert dates == sorted(dates)

    def test_sort_by_amount(self):
        result = banking_sort_queue_rows(self.ROWS, sort_key="amount")
        amounts = [r["amount"] for r in result]
        assert amounts == [500, 200, 100]

    def test_sort_by_confidence(self):
        result = banking_sort_queue_rows(self.ROWS, sort_key="confidence")
        confidences = [r["confidence"] for r in result]
        assert confidences == ["high", "medium", "low"]

    def test_unknown_sort_key_defaults_to_date(self):
        result = banking_sort_queue_rows(self.ROWS, sort_key="unknown")
        dates = [r["date"] for r in result]
        assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# banking_accounting_preview
# ---------------------------------------------------------------------------
class TestAccountingPreview:
    def test_bank_fee(self):
        result = banking_accounting_preview("bank_fee", description="EFT fee")
        assert result is not None
        assert "Bank Charges" in result

    def test_vendor(self):
        assert "Expense" in banking_accounting_preview("vendor")

    def test_worker_payroll(self):
        assert "Salary" in banking_accounting_preview("worker_payroll")

    def test_cc_bill(self):
        assert "Credit Card" in banking_accounting_preview("cc_bill")

    def test_card_clearing(self):
        assert "Clearing" in banking_accounting_preview("card_clearing")

    def test_equity_loan(self):
        assert "loan" in banking_accounting_preview("equity_loan")

    def test_other_income(self):
        assert "Income" in banking_accounting_preview("other_income")

    def test_unknown_kind(self):
        assert banking_accounting_preview("nonexistent") is None


# ---------------------------------------------------------------------------
# Session-dependent helpers (mocked)
# ---------------------------------------------------------------------------
class TestSessionDependentHelpers:
    def _mock_session(self, return_values: dict):
        """Create a mock session where get_setting returns values keyed by setting name."""
        session = MagicMock()

        def side_effect(s, key, **kwargs):
            return return_values.get(key)

        return session, side_effect

    @patch("registry.banking_config.get_setting")
    def test_banking_batch_eligible_kinds(self, mock_gs):
        mock_gs.return_value = "bank_fee"
        result = banking_batch_eligible_kinds(MagicMock(), company_id=1)
        assert result == frozenset({"bank_fee"})

    @patch("registry.banking_config.get_setting")
    def test_banking_batch_eligible_kinds_none(self, mock_gs):
        mock_gs.return_value = None
        result = banking_batch_eligible_kinds(MagicMock(), company_id=1)
        assert result == frozenset({"bank_fee"})

    @patch("registry.banking_config.get_setting")
    def test_banking_batch_posting_enabled_true(self, mock_gs):
        mock_gs.return_value = "1"
        assert banking_batch_posting_enabled(MagicMock(), company_id=1) is True

    @patch("registry.banking_config.get_setting")
    def test_banking_batch_posting_enabled_false(self, mock_gs):
        mock_gs.return_value = None
        assert banking_batch_posting_enabled(MagicMock(), company_id=1) is False

    @patch("registry.banking_config.get_setting")
    def test_banking_review_required_kinds(self, mock_gs):
        mock_gs.return_value = "payroll,low_confidence"
        result = banking_review_required_kinds(MagicMock(), company_id=1)
        assert result == frozenset({"payroll", "low_confidence"})

    @patch("registry.banking_config.get_setting")
    def test_banking_batch_confidence_threshold_valid(self, mock_gs):
        mock_gs.return_value = "high_and_medium"
        assert banking_batch_confidence_threshold(MagicMock(), 1) == "high_and_medium"

    @patch("registry.banking_config.get_setting")
    def test_banking_batch_confidence_threshold_invalid(self, mock_gs):
        mock_gs.return_value = "bogus"
        assert banking_batch_confidence_threshold(MagicMock(), 1) == "high"

    @patch("registry.banking_config.get_setting")
    def test_banking_batch_confidence_threshold_none(self, mock_gs):
        mock_gs.return_value = None
        assert banking_batch_confidence_threshold(MagicMock(), 1) == "high"

    @patch("registry.banking_config.get_setting")
    def test_resolve_landing_user_pref(self, mock_gs):
        mock_gs.return_value = "queue"
        result = banking_resolve_landing(MagicMock(), 1, user_id=10)
        assert result == "queue"

    @patch("registry.banking_config.get_setting")
    def test_resolve_landing_user_inherit(self, mock_gs):
        # user_id=None → no user preference
        mock_gs.return_value = "accounts"
        result = banking_resolve_landing(MagicMock(), 1, user_id=None)
        assert result == "accounts"

    @patch("registry.banking_config.get_setting")
    def test_resolve_landing_invalid_company_default(self, mock_gs):
        mock_gs.return_value = "bogus"
        result = banking_resolve_landing(MagicMock(), 1, user_id=None)
        assert result == "cockpit"

    @patch("registry.banking_config.get_setting")
    def test_default_import_tab_no_user(self, mock_gs):
        mock_gs.return_value = None
        result = banking_default_import_tab(MagicMock(), 1, user_id=None)
        assert result == "match"

    @patch("registry.banking_config.get_setting")
    def test_default_import_tab_user_valid(self, mock_gs):
        mock_gs.return_value = "upload"
        result = banking_default_import_tab(MagicMock(), 1, user_id=10)
        assert result == "upload"

    @patch("registry.banking_config.get_setting")
    def test_default_import_tab_user_invalid(self, mock_gs):
        mock_gs.return_value = "bogus"
        result = banking_default_import_tab(MagicMock(), 1, user_id=10)
        assert result == "match"

    @patch("registry.banking_config.get_setting")
    def test_show_confidence_chips_no_user(self, mock_gs):
        result = banking_show_confidence_chips(MagicMock(), 1, user_id=None)
        assert result is True

    @patch("registry.banking_config.get_setting")
    def test_show_confidence_chips_user(self, mock_gs):
        mock_gs.return_value = True
        result = banking_show_confidence_chips(MagicMock(), 1, user_id=10)
        assert result is True

    @patch("registry.banking_config.get_setting")
    def test_show_accounting_previews_no_user(self, mock_gs):
        result = banking_show_accounting_previews(MagicMock(), 1, user_id=None)
        assert result is True

    @patch("registry.banking_config.get_setting")
    def test_show_accounting_previews_user(self, mock_gs):
        mock_gs.return_value = ""
        result = banking_show_accounting_previews(MagicMock(), 1, user_id=10)
        assert result is False

    @patch("registry.banking_config.get_setting")
    def test_queue_sort_no_user(self, mock_gs):
        result = banking_queue_sort(MagicMock(), 1, user_id=None)
        assert result == "date"

    @patch("registry.banking_config.get_setting")
    def test_queue_sort_user_valid(self, mock_gs):
        mock_gs.return_value = "amount"
        result = banking_queue_sort(MagicMock(), 1, user_id=10)
        assert result == "amount"

    @patch("registry.banking_config.get_setting")
    def test_queue_sort_user_invalid(self, mock_gs):
        mock_gs.return_value = "bogus"
        result = banking_queue_sort(MagicMock(), 1, user_id=10)
        assert result == "date"

    @patch("registry.banking_config.get_setting")
    def test_queue_density_no_user(self, mock_gs):
        result = banking_queue_density(MagicMock(), 1, user_id=None)
        assert result == "comfortable"

    @patch("registry.banking_config.get_setting")
    def test_queue_density_user_valid(self, mock_gs):
        mock_gs.return_value = "compact"
        result = banking_queue_density(MagicMock(), 1, user_id=10)
        assert result == "compact"

    @patch("registry.banking_config.get_setting")
    def test_queue_density_user_invalid(self, mock_gs):
        mock_gs.return_value = "bogus"
        result = banking_queue_density(MagicMock(), 1, user_id=10)
        assert result == "comfortable"


# ---------------------------------------------------------------------------
# banking_batch_review_reason_for_row
# ---------------------------------------------------------------------------
class TestBatchReviewReason:
    @patch("registry.banking_config.get_setting")
    def test_excluded_kind(self, mock_gs):
        mock_gs.return_value = None
        # bank_fee is the only eligible kind; "vendor" is excluded
        result = banking_batch_review_reason_for_row(
            MagicMock(), 1, detected_kind="vendor", confidence="high", description=""
        )
        assert result == "batch_kind_excluded"

    @patch("registry.banking_config.get_setting")
    def test_low_confidence_with_review_policy(self, mock_gs):
        def side_effect(s, key, **kw):
            if "review_required_kinds" in key:
                return "low_confidence"
            if "batch_eligible_kinds" in key:
                return "bank_fee"
            if "batch_confidence_threshold" in key:
                return "high"
            return None

        mock_gs.side_effect = side_effect
        result = banking_batch_review_reason_for_row(
            MagicMock(), 1, detected_kind="bank_fee", confidence="low", description=""
        )
        assert result == "low_confidence"

    @patch("registry.banking_config.get_setting")
    def test_transfer_fee_review(self, mock_gs):
        def side_effect(s, key, **kw):
            if "review_required_kinds" in key:
                return "transfer_charges"
            if "batch_eligible_kinds" in key:
                return "bank_fee"
            if "batch_confidence_threshold" in key:
                return "high_and_medium"
            return None

        mock_gs.side_effect = side_effect
        result = banking_batch_review_reason_for_row(
            MagicMock(), 1,
            detected_kind="bank_fee", confidence="high", description="EFT",
            subtype="transfer_fee",
        )
        assert result == "review_required_transfer"

    @patch("registry.banking_config.get_setting")
    def test_no_review_reason(self, mock_gs):
        def side_effect(s, key, **kw):
            if "review_required_kinds" in key:
                return ""
            if "batch_eligible_kinds" in key:
                return "bank_fee"
            if "batch_confidence_threshold" in key:
                return "high_and_medium"
            return None

        mock_gs.side_effect = side_effect
        result = banking_batch_review_reason_for_row(
            MagicMock(), 1,
            detected_kind="bank_fee", confidence="high", description="Fee",
        )
        assert result is None
