"""PARTNER-UX-01 P1–P3 — Partner Accounts plain-language UX."""
from __future__ import annotations

import inspect
from pathlib import Path

import app as erp
from registry.i18n import t
from registry.locales.messages import MESSAGES
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR

ROOT = Path(__file__).resolve().parents[1]

_MOVEMENT_EXPLAIN_KEYS = (
    "partner.mv_explain.capital_contribution",
    "partner.mv_explain.drawing",
    "partner.mv_explain.salary",
    "partner.mv_explain.advance",
    "partner.mv_explain.repayment",
    "partner.mv_explain.advance_offset",
)

_P2_KEYS = (
    "partner.mv_outstanding_advance",
    "partner.mv_no_outstanding_advance",
    "partner.mv_no_advance_to_settle",
    "partner.mv_exceeds_outstanding_advance",
)

_P3_KEYS = (
    "partner.summary_plain_capital",
    "partner.summary_plain_current",
    "partner.summary_plain_advances",
    "partner.summary_plain_adv_owes",
    "partner.summary_current_taken",
    "partner.summary_current_owed",
)

_SUMMARY_LABEL_EXPECTED_EN = {
    "partner.summary_plain_capital": "Invested in business",
    "partner.summary_plain_current": "Taken from business / profit share account",
    "partner.summary_plain_advances": "Still owes company",
}


def test_partner_summary_labels_translate_not_raw_keys():
    """Regression — Summary must never show untranslated partner.summary_* keys."""
    for key in _P3_KEYS:
        for loc in ("en", "tr"):
            val = t(key, loc)
            assert val != key, f"{loc}: {key} missing from catalog"
            assert not val.startswith("partner.summary_"), (
                f"{loc}: {key} rendered raw key {val!r}"
            )
    for key, snippet in _SUMMARY_LABEL_EXPECTED_EN.items():
        assert snippet in t(key, "en")


def test_partner_summary_labels_in_messages_catalog():
    for key in _P3_KEYS:
        assert MESSAGES["en"][key] == TRANSACTIONAL_EN[key]
        assert MESSAGES["tr"][key] == TRANSACTIONAL_TR[key]


def test_movement_explain_locale_keys_en_tr():
    for key in _MOVEMENT_EXPLAIN_KEYS + _P2_KEYS + _P3_KEYS:
        assert key in TRANSACTIONAL_EN, f"missing EN: {key}"
        assert key in TRANSACTIONAL_TR, f"missing TR: {key}"
        assert TRANSACTIONAL_EN[key].strip()
        assert TRANSACTIONAL_TR[key].strip()


def _partner_accounts_src() -> str:
    return inspect.getsource(erp.render_partner_accounts)


def test_movement_form_renders_type_explanation():
    src = _partner_accounts_src()
    assert "_PARTNER_MOVEMENT_EXPLAIN_I18N" in src
    assert "partner.new_movement_expander" in src
    assert "st.caption(_t(_PARTNER_MOVEMENT_EXPLAIN_I18N[pm_type]))" in src


def test_outstanding_advance_from_partner_advance_account():
    src = inspect.getsource(erp.get_partner_advance_balance)
    assert "advance_account_id" in src
    assert "calculate_account_balance" in src
    assert "get_partner_advance_balance" in _partner_accounts_src()


def test_no_outstanding_advance_warning_for_repayment_and_offset():
    src = _partner_accounts_src()
    assert '("Repayment", "AdvanceOffset")' in src
    assert "partner.mv_no_advance_to_settle" in src
    assert "adv_bal <= 0.01" in src


def test_exceeds_outstanding_advance_warning_before_submit():
    src = _partner_accounts_src()
    mv_block = src.split("partner.new_movement_expander", 1)[1].split(
        "partner.add_partners_first", 1
    )[0]
    assert "partner.mv_exceeds_outstanding_advance" in mv_block
    assert "pm_amt > adv_bal + 0.01" in mv_block
    assert mv_block.index("partner.mv_exceeds_outstanding_advance") < mv_block.index(
        "partner_movement_form"
    )


def test_summary_tab_plain_language_labels():
    src = _partner_accounts_src()
    summary_block = src.split("partner.tab_summary", 1)[1]
    assert "partner.summary_plain_capital" in summary_block
    assert "partner.summary_plain_current" in summary_block
    assert "partner.summary_plain_advances" in summary_block
    assert "partner.summary_plain.capital" not in summary_block
    assert "partner.summary_plain_adv_owes" in summary_block
    assert "partner.summary_current_taken" in summary_block
    assert "partner.summary_current_owed" in summary_block


def test_post_partner_movement_logic_unchanged():
    src = inspect.getsource(erp.post_partner_movement)
    assert "def post_partner_movement" in src
    assert "posting_service.post_partner_movement(" in src
    assert 'if err == "":' in src
