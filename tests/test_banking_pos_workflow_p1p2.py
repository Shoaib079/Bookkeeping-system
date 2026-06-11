"""BANKING-POS-WORKFLOW-01 P1+P2 — POS Settlement guardrails and explanation."""
from __future__ import annotations

import inspect
from pathlib import Path

import app as erp
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR

ROOT = Path(__file__).resolve().parents[1]
MATCH_POST = ROOT / "reconciliation" / "match_post.py"

_P1P2_LOCALE_KEYS = (
    "banking.import.match.pos_settlement_explainer",
    "banking.import.match.other_income.advanced",
    "banking.import.match.other_income.advanced_hint",
    "banking.import.match.other_income.use_sales_revenue",
    "banking.import.match.other_income.sales_revenue_warning",
    "banking.import.match.other_income.sales_revenue_pos_warning",
)


def test_sales_revenue_not_in_main_other_income_options():
    src = inspect.getsource(erp._render_bsi_other_deposit)
    assert '"Sales Revenue"' in src
    assert "_common_credit_opts" in src
    assert src.index("_common_credit_opts") < src.index('"Sales Revenue"')
    common_block = src.split("_common_credit_opts", 1)[1].split("]", 1)[0]
    assert "Sales Revenue" not in common_block


def test_sales_revenue_warning_when_selected():
    src = inspect.getsource(erp._render_bsi_other_deposit)
    assert "bsi_other_income_use_sales_revenue" in src
    assert "banking.import.match.other_income.sales_revenue_warning" in src
    assert 'credit_acct = "Sales Revenue"' in src
    assert "st.warning" in src


def test_pos_deposit_description_escalates_warning():
    src = inspect.getsource(erp._render_bsi_other_deposit)
    assert "card_deposit_style(sel_row.description" in src
    assert "banking.import.match.other_income.sales_revenue_pos_warning" in src


def test_pos_settlement_explainer_in_card_sale_deposit_panel():
    src = inspect.getsource(erp._render_bsi_deposit_clearing)
    assert "banking.import.match.pos_settlement_explainer" in src
    assert src.index("pos_settlement_explainer") < src.index("pos_bank_note")


def test_banking_settings_caption_includes_pos_settlement_explanation():
    assert "POS Settlement" in TRANSACTIONAL_EN["bank.settings.card_settlement.caption"]
    assert "matching bank deposits to waiting card sales" in TRANSACTIONAL_EN[
        "bank.settings.card_settlement.caption"
    ]
    assert "POS Mutabakatı" in TRANSACTIONAL_TR["bank.settings.card_settlement.caption"]
    assert "bekleyen kart satışlarını banka yatırmalarıyla" in TRANSACTIONAL_TR[
        "bank.settings.card_settlement.caption"
    ]


def test_p1p2_locale_keys_en_tr_parity():
    for key in _P1P2_LOCALE_KEYS:
        assert key in TRANSACTIONAL_EN, f"missing EN: {key}"
        assert key in TRANSACTIONAL_TR, f"missing TR: {key}"
        assert TRANSACTIONAL_EN[key].strip()
        assert TRANSACTIONAL_TR[key].strip()


def test_posting_logic_unchanged():
    """P1/P2 are UX-only — match/post functions must not change."""
    src = MATCH_POST.read_text(encoding="utf-8")
    assert "def post_deposit_clearing_match" in src
    assert "def post_generic_deposit" in src
    other_src = inspect.getsource(erp._render_bsi_other_deposit)
    assert "post_generic_deposit(" in other_src
    clearing_src = inspect.getsource(erp._render_bsi_deposit_clearing)
    assert "post_deposit_clearing_match(" in clearing_src
