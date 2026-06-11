"""BANKING-UX-02 P1B — POS Settlement entry point on Banking page."""
from __future__ import annotations

import inspect
from pathlib import Path

import app as erp
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR

MATCH_POST = Path(__file__).resolve().parents[1] / "reconciliation" / "match_post.py"

_P1B_KEYS = (
    "banking.pos_entry.title",
    "banking.pos_entry.hint",
    "banking.pos_entry.open",
    "banking.pos_entry.no_rows",
)


class TestBankingEntryPoint:
    def test_render_banking_exposes_pos_settlement_entry(self):
        src = inspect.getsource(erp.render_banking)
        assert "_render_banking_pos_settlement_entry" in src
        assert src.index("_render_banking_pos_settlement_entry") < src.index(
            '_banking_section_select("banking_section"'
        )

    def test_entry_uses_locale_title_and_hint(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_entry)
        assert "banking.pos_entry.title" in src
        assert "banking.pos_entry.hint" in src
        assert "banking.pos_entry.open" in src
        assert "banking.pos_entry.no_rows" in src
        assert "get_postable_rows" in src

    def test_entry_does_not_duplicate_deposit_clearing_panel(self):
        entry_src = inspect.getsource(erp._render_banking_pos_settlement_entry)
        assert "_render_bsi_deposit_clearing" not in entry_src
        assert "post_deposit_clearing_match" not in entry_src
        assert "compute_pos_settlement_preview" not in entry_src
        assert "_apply_banking_pos_settlement_route" in entry_src


class TestRouteSessionKeys:
    def test_route_keys_match_requirements(self):
        keys = erp._banking_pos_settlement_route_keys()
        assert keys["banking_section"] == "import"
        assert keys["bsi_section"] == "match"
        assert keys["bsi_match_kind"] == "card_clearing"
        assert keys["bsi_pos_entry"] is True

    def test_apply_route_sets_session_state(self):
        src = inspect.getsource(erp._apply_banking_pos_settlement_route)
        assert "_banking_pos_settlement_route_keys" in src
        assert 'st.session_state[k] = v' in src
        assert "st.rerun()" in src

    def test_match_section_honours_pos_entry_flag(self):
        src = inspect.getsource(erp.render_bank_statement_import)
        match_block = src.split('elif section == "match":', 1)[1]
        assert 'st.session_state.pop("bsi_pos_entry", False)' in match_block
        assert '"card_clearing"' in match_block
        assert match_block.index("bsi_pos_entry") < match_block.index(
            "bsi_match_kind_row"
        )


class TestPostingUnchanged:
    def test_single_deposit_clearing_renderer(self):
        assert inspect.getsourcefile(erp._render_bsi_deposit_clearing) is not None
        src = inspect.getsource(erp.render_bank_statement_import)
        assert src.count("_render_bsi_deposit_clearing(") == 1

    def test_no_sales_revenue_in_settlement_posting(self):
        src = MATCH_POST.read_text(encoding="utf-8")
        assert "Sales Revenue" not in src
        clearing_src = inspect.getsource(erp._render_bsi_deposit_clearing)
        assert "Sales Revenue" not in clearing_src


class TestLocales:
    def test_p1b_locale_keys_en_tr(self):
        for key in _P1B_KEYS:
            assert key in TRANSACTIONAL_EN, f"missing EN: {key}"
            assert key in TRANSACTIONAL_TR, f"missing TR: {key}"
            assert TRANSACTIONAL_EN[key].strip()
            assert TRANSACTIONAL_TR[key].strip()

    def test_title_matches_requirement(self):
        assert TRANSACTIONAL_EN["banking.pos_entry.title"] == "POS / Card Settlement"
        assert TRANSACTIONAL_TR["banking.pos_entry.title"] == "POS / Kart Tahsilatı"
