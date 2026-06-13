"""BANKING-UX-03 P1.2 — suggested match kind + confidence chip."""
from __future__ import annotations

import inspect

from reconciliation.match_post import (
    card_deposit_style,
    looks_like_commission,
    looks_like_credit_card_bill_payment,
    looks_like_worker_payroll,
    suggest_deposit_match_kind,
    suggest_withdrawal_match_kind,
)
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from ui.banking import banking_match_kind_confidence, render_banking_match_suggestion_chip

import app as erp_app

_P12_KEYS = (
    "banking.import.match.detected_kind",
    "banking.import.match.confidence_label",
    "banking.import.match.confidence.high",
    "banking.import.match.confidence.medium",
    "banking.import.match.confidence.low",
    "banking.import.match.accept_suggestion",
)

_DEPOSIT_CASES = (
    ("NET SATIS TUTARI", True, "card_clearing"),
    ("POS YATIRMA", True, "card_clearing"),
    ("WIRE FROM CUSTOMER", True, "other_income"),
    ("WIRE FROM CUSTOMER", False, "other_income"),
)

_WITHDRAWAL_CASES = (
    ("KK ODEME", True, True, True, "cc_bill"),
    ("KOMISYON UCRET", False, True, False, "bank_fee"),
    ("MAAS ODEME", False, False, True, "worker_payroll"),
    ("ACME SUPPLIES", True, True, True, "vendor"),
)


class TestSuggestionCharacterization:
    def test_deposit_suggestions_pinned(self):
        for desc, settlement_on, expected in _DEPOSIT_CASES:
            assert (
                suggest_deposit_match_kind(desc, card_settlement_on=settlement_on)
                == expected
            )

    def test_withdrawal_suggestions_pinned(self):
        for desc, cc_on, charges_on, workers, expected in _WITHDRAWAL_CASES:
            assert (
                suggest_withdrawal_match_kind(
                    desc,
                    company_card_on=cc_on,
                    bank_charges_on=charges_on,
                    has_workers=workers,
                )
                == expected
            )

    def test_card_deposit_style_net_and_card(self):
        assert card_deposit_style("NET SATIS TUTARI") == "net"
        assert card_deposit_style("POS YATIRMA") == "card"


class TestConfidenceBanding:
    def test_deposit_net_sales_high(self):
        assert (
            banking_match_kind_confidence(
                "card_clearing", "NET SATIS TUTARI", is_deposit=True
            )
            == "high"
        )

    def test_deposit_generic_card_medium(self):
        assert (
            banking_match_kind_confidence(
                "card_clearing", "POS YATIRMA", is_deposit=True
            )
            == "medium"
        )

    def test_deposit_other_income_low(self):
        assert (
            banking_match_kind_confidence(
                "other_income", "WIRE FROM CUSTOMER", is_deposit=True
            )
            == "low"
        )

    def test_withdrawal_cc_bill_high(self):
        assert (
            banking_match_kind_confidence(
                "cc_bill", "KK ODEME", is_deposit=False
            )
            == "high"
        )

    def test_withdrawal_bank_fee_high(self):
        assert (
            banking_match_kind_confidence(
                "bank_fee", "KOMISYON UCRET", is_deposit=False
            )
            == "high"
        )

    def test_withdrawal_worker_payroll_high(self):
        assert (
            banking_match_kind_confidence(
                "worker_payroll", "MAAS ODEME", is_deposit=False
            )
            == "high"
        )

    def test_withdrawal_vendor_fallback_low(self):
        assert (
            banking_match_kind_confidence(
                "vendor", "ACME SUPPLIES", is_deposit=False
            )
            == "low"
        )

    def test_heuristic_alignment_with_suggest_cc_bill(self):
        desc = "KK ODEME"
        kind = suggest_withdrawal_match_kind(
            desc, company_card_on=True, bank_charges_on=True, has_workers=True
        )
        assert kind == "cc_bill"
        assert looks_like_credit_card_bill_payment(desc)
        assert banking_match_kind_confidence(kind, desc, is_deposit=False) == "high"

    def test_heuristic_alignment_commission_bank_fee(self):
        desc = "KOMISYON UCRET"
        assert looks_like_commission(desc)
        kind = suggest_withdrawal_match_kind(
            desc, company_card_on=False, bank_charges_on=True, has_workers=False
        )
        assert kind == "bank_fee"
        assert banking_match_kind_confidence(kind, desc, is_deposit=False) == "high"


class TestUiContract:
    def test_match_section_renders_suggestion_chip(self):
        src = inspect.getsource(erp_app.render_bank_statement_import)
        assert "render_banking_match_suggestion_chip" in src
        assert "banking_match_kind_confidence" in src

    def test_accept_sets_session_state_only(self):
        src = inspect.getsource(render_banking_match_suggestion_chip)
        assert 'st.session_state["bsi_match_kind"]' in src
        assert "post_deposit_clearing_match" not in src
        assert "post_generic_deposit" not in src
        assert "post_vendor_outflow" not in src

    def test_post_flow_unchanged(self):
        clearing_src = inspect.getsource(erp_app._render_bsi_deposit_clearing)
        assert "post_deposit_clearing_match(" in clearing_src
        other_src = inspect.getsource(erp_app._render_bsi_other_deposit)
        assert "post_generic_deposit(" in other_src
        vendor_src = inspect.getsource(erp_app._render_bsi_vendor_payment)
        assert "post_vendor_outflow(" in vendor_src
        fee_src = inspect.getsource(erp_app._render_bsi_bank_fee)
        assert "post_bank_charge_outflow(" in fee_src

    def test_chip_helper_uses_locale_keys(self):
        src = inspect.getsource(render_banking_match_suggestion_chip)
        assert "banking.import.match.detected_kind" in src
        assert "banking.import.match.confidence." in src
        assert "banking.import.match.accept_suggestion" in src


class TestLocales:
    def test_en_and_tr_keys_exist(self):
        for key in _P12_KEYS:
            assert key in TRANSACTIONAL_EN, f"missing EN: {key}"
            assert key in TRANSACTIONAL_TR, f"missing TR: {key}"
            assert TRANSACTIONAL_EN[key].strip()
            assert TRANSACTIONAL_TR[key].strip()
