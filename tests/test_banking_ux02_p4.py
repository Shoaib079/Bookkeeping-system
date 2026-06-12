"""BANKING-UX-02 P4 — Match failure explanation."""
from __future__ import annotations

import inspect
import types
from pathlib import Path
from unittest.mock import MagicMock

import app as erp
from reconciliation.pos_match_failure import evaluate_pos_match_failure
from reconciliation.pos_settlement_preview import compute_pos_settlement_preview
from registry.i18n import t
from registry.locales.messages import MESSAGES
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR

MATCH_POST = Path(__file__).resolve().parents[1] / "reconciliation" / "match_post.py"

_P4_KEYS = (
    "banking.match_failure.section_title",
    "banking.match_failure.status.ready",
    "banking.match_failure.status.attention",
    "banking.match_failure.status.cannot_post",
    "banking.match_failure.no_row_selected",
    "banking.match_failure.not_deposit",
    "banking.match_failure.row_already_posted",
    "banking.match_failure.no_unsettled_sales",
    "banking.match_failure.no_sales_in_window",
    "banking.match_failure.no_sales_selected",
    "banking.match_failure.no_clearing_balance",
    "banking.match_failure.settlement_exceeds_clearing",
    "banking.match_failure.fee_exceeds_settlement",
    "banking.match_failure.negative_expected_deposit",
    "banking.match_failure.deposit_amount_mismatch",
    "banking.match_failure.bank_charges_account_missing",
    "banking.match_failure.bank_charges_disabled",
    "banking.match_failure.inferred_fee_unconfirmed",
    "banking.match_failure.currency_mismatch",
)


def _row(**kwargs):
    defaults = {
        "credit_amount": True,
        "debit_amount": False,
        "status": "staging",
        "amount": 970.0,
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _evaluate(
    *,
    available=5000.0,
    settlement=1000.0,
    deposit=970.0,
    fee_amount=None,
    picked=1,
    clearing_available=True,
    unsettled_sales_available=None,
    window_sales_available=None,
    **kwargs,
):
    preview = compute_pos_settlement_preview(
        available, settlement, deposit, fee_amount=fee_amount
    )
    unsettled = (
        clearing_available
        if unsettled_sales_available is None
        else unsettled_sales_available
    )
    in_window = (
        clearing_available
        if window_sales_available is None
        else window_sales_available
    )
    defaults = dict(
        sel_row=_row(amount=deposit),
        preview=preview,
        deposit_amount=deposit,
        picked_sale_count=picked,
        unsettled_sales_available=unsettled,
        window_sales_available=in_window,
        bank_charges_enabled=True,
        bank_charges_account_exists=True,
        confirm_inferred_fee=False,
        fee_gap_needs_confirm=False,
        import_currency="TRY",
        company_currency="TRY",
    )
    defaults.update(kwargs)
    return evaluate_pos_match_failure(**defaults)


class TestMatchFailureLogic:
    def test_ready_when_amounts_match(self):
        check = _evaluate(settlement=1000.0, deposit=970.0, picked=2)
        assert check.status == "ready"
        assert not check.items

    def test_attention_when_no_sales_selected(self):
        check = _evaluate(picked=0)
        assert check.status == "attention"
        keys = [i.key for i in check.items]
        assert "banking.match_failure.no_sales_selected" in keys

    def test_deposit_mismatch_warning(self):
        check = _evaluate(settlement=1000.0, deposit=9800.0, picked=1)
        assert check.status == "cannot_post"
        keys = [i.key for i in check.items]
        assert "banking.match_failure.deposit_amount_mismatch" in keys

    def test_no_unsettled_sales_warning(self):
        check = _evaluate(clearing_available=False, picked=0)
        assert check.status == "cannot_post"
        keys = [i.key for i in check.items]
        assert "banking.match_failure.no_unsettled_sales" in keys

    def test_no_contradiction_when_p2_has_unsettled_but_window_empty(self):
        """P2/P3 use wide-date fetch; P4 must not claim zero unsettled when total > 0."""
        check = _evaluate(
            picked=0,
            unsettled_sales_available=True,
            window_sales_available=False,
        )
        keys = [i.key for i in check.items]
        assert "banking.match_failure.no_unsettled_sales" not in keys
        assert "banking.match_failure.no_sales_in_window" in keys
        assert check.status == "attention"

    def test_fee_exceeds_settlement_warning(self):
        preview = compute_pos_settlement_preview(1000.0, 100.0, 50.0, fee_amount=150.0)
        check = evaluate_pos_match_failure(
            sel_row=_row(),
            preview=preview,
            deposit_amount=50.0,
            picked_sale_count=1,
            unsettled_sales_available=True,
            bank_charges_enabled=True,
            bank_charges_account_exists=True,
            confirm_inferred_fee=False,
            fee_gap_needs_confirm=False,
            import_currency="TRY",
            company_currency="TRY",
        )
        assert check.status == "cannot_post"
        keys = [i.key for i in check.items]
        assert "banking.match_failure.fee_exceeds_settlement" in keys

    def test_row_already_posted_warning(self):
        check = _evaluate(sel_row=_row(status="posted"))
        assert check.status == "cannot_post"
        keys = [i.key for i in check.items]
        assert "banking.match_failure.row_already_posted" in keys

    def test_not_deposit_warning(self):
        check = _evaluate(
            sel_row=_row(credit_amount=False, debit_amount=True),
        )
        assert check.status == "cannot_post"
        keys = [i.key for i in check.items]
        assert "banking.match_failure.not_deposit" in keys

    def test_settlement_exceeds_clearing_warning(self):
        check = _evaluate(available=500.0, settlement=600.0, deposit=580.0)
        assert check.status == "cannot_post"
        keys = [i.key for i in check.items]
        assert "banking.match_failure.settlement_exceeds_clearing" in keys

    def test_inferred_fee_unconfirmed_attention(self):
        check = _evaluate(
            settlement=1000.0,
            deposit=970.0,
            picked=1,
            fee_gap_needs_confirm=True,
            confirm_inferred_fee=False,
        )
        assert check.status == "attention"
        keys = [i.key for i in check.items]
        assert "banking.match_failure.inferred_fee_unconfirmed" in keys


class TestUiWiring:
    def test_unsettled_source_matches_p2_p3(self):
        src = inspect.getsource(erp._render_bsi_deposit_clearing)
        assert "fetch_unsettled_card_sales_for_visibility" in src
        assert "unsettled_sales_available=bool(unsettled_all)" in src
        assert "unsettled_sales_available=bool(clearing)" not in src

    def test_match_check_after_preview_before_post(self):
        src = inspect.getsource(erp._render_bsi_deposit_clearing)
        assert "evaluate_pos_match_failure" in src
        assert "_render_pos_match_failure_block" in src
        assert src.index("_render_pos_match_failure_block") > src.index(
            "_render_pos_settlement_preview_block"
        )
        assert src.index("_render_pos_match_failure_block") < src.index(
            "post_deposit_clearing_match"
        )

    def test_match_panel_read_only(self):
        src = inspect.getsource(erp._render_pos_match_failure_block)
        assert "st.button" not in src
        assert "post_deposit_clearing_match" not in src

    def test_match_panel_uses_banking_label_helper(self):
        src = inspect.getsource(erp._render_pos_match_failure_block)
        assert "banking_match_failure_label" in src
        assert '_t("banking.match_failure' not in src

    def test_app_banking_label_resolves_not_raw(self):
        erp.st.session_state["ui_locale"] = "en"
        label = erp._banking_match_failure_label(
            "banking.match_failure.section_title"
        )
        assert label == "Match check"
        assert not label.startswith("banking.match_failure")

    def test_focused_pos_section_uses_match_check(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_section)
        assert "_render_bsi_deposit_clearing_panel" in src


class TestPostingUnchanged:
    def test_settlement_je_lines_unchanged(self):
        src = MATCH_POST.read_text(encoding="utf-8")
        assert "je_lines = [(bank_gl.id, deposit_amt, 0)]" in src
        assert "je_lines.append((clearing_gl.id, 0, clearing_total))" in src
        assert "Sales Revenue" not in src

    def test_post_deposit_clearing_match_signature_unchanged(self):
        src = MATCH_POST.read_text(encoding="utf-8")
        assert "def post_deposit_clearing_match" in src


class TestLocales:
    def test_p4_locale_keys_en_tr(self):
        for key in _P4_KEYS:
            assert key in TRANSACTIONAL_EN, f"missing EN: {key}"
            assert key in TRANSACTIONAL_TR, f"missing TR: {key}"
            assert TRANSACTIONAL_EN[key].strip()
            assert TRANSACTIONAL_TR[key].strip()

    def test_deposit_mismatch_example_en(self):
        text = t(
            "banking.match_failure.deposit_amount_mismatch",
            "en",
            currency="TRY",
            deposit=9800.0,
            expected=9750.0,
        )
        assert "9,800" in text
        assert "9,750" in text
        assert text != "banking.match_failure.deposit_amount_mismatch"

    def test_p4_keys_resolve_not_raw(self):
        for key in _P4_KEYS:
            text = t(
                key,
                "en",
                currency="TRY",
                deposit=100.0,
                expected=90.0,
                settlement=100.0,
                available=50.0,
                fee=10.0,
                amount=-5.0,
                import_currency="USD",
                company_currency="TRY",
            )
            assert text != key

    def test_tr_messages_duplicate(self):
        assert MESSAGES["tr"]["banking.match_failure.section_title"] == (
            TRANSACTIONAL_TR["banking.match_failure.section_title"]
        )
