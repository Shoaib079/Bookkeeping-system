"""BANKING-UX-02 P1 — POS Settlement preview."""
from __future__ import annotations

import inspect
from pathlib import Path

import app as erp
from reconciliation.pos_settlement_preview import compute_pos_settlement_preview
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR

MATCH_POST = Path(__file__).resolve().parents[1] / "reconciliation" / "match_post.py"

_P1_KEYS = (
    "banking.pos_preview.section_title",
    "banking.pos_preview.revenue_note",
    "banking.pos_preview.available_clearing",
    "banking.pos_preview.settlement_amount",
    "banking.pos_preview.bank_charges",
    "banking.pos_preview.expected_deposit",
    "banking.pos_preview.remaining_clearing",
    "banking.pos_preview.warn_no_clearing",
    "banking.pos_preview.warn_settlement_exceeds_clearing",
    "banking.pos_preview.warn_fee_exceeds_settlement",
    "banking.pos_preview.warn_negative_deposit",
)


class TestPreviewMath:
    def test_expected_deposit_equals_settlement_minus_fee(self):
        p = compute_pos_settlement_preview(5000.0, 1000.0, 970.0)
        assert p.bank_charges == 30.0
        assert p.expected_bank_deposit == 970.0

    def test_remaining_clearing_after_settlement(self):
        p = compute_pos_settlement_preview(2500.0, 800.0, 776.0)
        assert p.remaining_clearing == 1700.0

    def test_explicit_fee_from_settlement_batch(self):
        p = compute_pos_settlement_preview(3000.0, 1000.0, 970.0, fee_amount=25.0)
        assert p.bank_charges == 25.0
        assert p.expected_bank_deposit == 975.0


class TestPreviewWarnings:
    def test_warn_settlement_exceeds_clearing(self):
        p = compute_pos_settlement_preview(500.0, 600.0, 580.0)
        keys = [w.key for w in p.warnings]
        assert "banking.pos_preview.warn_settlement_exceeds_clearing" in keys

    def test_warn_fee_exceeds_settlement(self):
        p = compute_pos_settlement_preview(1000.0, 100.0, 50.0, fee_amount=150.0)
        keys = [w.key for w in p.warnings]
        assert "banking.pos_preview.warn_fee_exceeds_settlement" in keys

    def test_warn_negative_expected_deposit(self):
        p = compute_pos_settlement_preview(1000.0, 100.0, 200.0, fee_amount=150.0)
        assert p.expected_bank_deposit == -50.0
        keys = [w.key for w in p.warnings]
        assert "banking.pos_preview.warn_negative_deposit" in keys

    def test_warn_no_clearing_balance(self):
        p = compute_pos_settlement_preview(0.0, 0.0, 0.0)
        keys = [w.key for w in p.warnings]
        assert "banking.pos_preview.warn_no_clearing" in keys


class TestUiWiring:
    def test_preview_before_post_button(self):
        src = inspect.getsource(erp._render_bsi_deposit_clearing)
        assert "_render_pos_settlement_preview_block" in src
        assert "compute_pos_settlement_preview" in src
        assert src.index("_render_pos_settlement_preview_block") < src.index(
            "post_deposit_clearing_match"
        )

    def test_revenue_note_in_preview(self):
        src = inspect.getsource(erp._render_pos_settlement_preview_block)
        assert "banking.pos_preview.revenue_note" in src

    def test_sales_revenue_still_in_advanced_only(self):
        src = inspect.getsource(erp._render_bsi_other_deposit)
        common_block = src.split("_common_credit_opts", 1)[1].split("]", 1)[0]
        assert "Sales Revenue" not in common_block


class TestPostingUnchanged:
    def test_settlement_je_lines_unchanged(self):
        src = MATCH_POST.read_text(encoding="utf-8")
        assert "je_lines = [(bank_gl.id, deposit_amt, 0)]" in src
        assert "je_lines.append((clearing_gl.id, 0, clearing_total))" in src
        assert "Sales Revenue" not in src

    def test_post_deposit_clearing_match_signature_unchanged(self):
        src = MATCH_POST.read_text(encoding="utf-8")
        assert "def post_deposit_clearing_match" in src
        clearing_src = inspect.getsource(erp._render_bsi_deposit_clearing)
        assert "post_deposit_clearing_match(" in clearing_src


class TestLocales:
    def test_p1_locale_keys_en_tr(self):
        for key in _P1_KEYS:
            assert key in TRANSACTIONAL_EN, f"missing EN: {key}"
            assert key in TRANSACTIONAL_TR, f"missing TR: {key}"
            assert TRANSACTIONAL_EN[key].strip()
            assert TRANSACTIONAL_TR[key].strip()
