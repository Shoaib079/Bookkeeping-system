"""BANKING-UX-02 P1B — POS Settlement entry point on Banking page."""
from __future__ import annotations

import inspect
from pathlib import Path

import app as erp
from registry.i18n import t
from registry.locales.messages import MESSAGES
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from registry.nav_keys import NAV_BANKING

MATCH_POST = Path(__file__).resolve().parents[1] / "reconciliation" / "match_post.py"

_P1B_KEYS = (
    "banking.pos_entry.title",
    "banking.pos_entry.hint",
    "banking.pos_entry.open",
    "banking.pos_entry.no_rows",
)

_EXPECTED_EN = {
    "banking.pos_entry.title": "POS / Card Settlement",
    "banking.pos_entry.open": "Open POS / Card Settlement",
}


class TestBankingEntryPoint:
    def test_render_banking_exposes_pos_settlement_entry(self):
        src = inspect.getsource(erp.render_banking)
        assert "_render_banking_pos_settlement_entry" in src
        assert src.index("_render_banking_pos_settlement_entry") < src.index(
            '_banking_section_select("banking_section"'
        )

    def test_entry_uses_t_helper_like_other_banking_labels(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_entry)
        assert '_t("banking.pos_entry.title")' in src
        assert '_t("banking.pos_entry.hint")' in src
        assert '_t("banking.pos_entry.open")' in src
        assert '_t("banking.pos_entry.no_rows")' in src
        assert "_banking_pos_entry_label" not in src

    def test_entry_stays_visible_when_import_section_selected(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_entry)
        assert 'banking_section") == "import"' not in src

    def test_entry_button_calls_apply_route(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_entry)
        assert "_apply_banking_pos_settlement_route()" in src
        assert "on_click=" not in src

    def test_entry_visible_under_feature_flags_only(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_entry)
        assert "_card_settlement_on(session)" in src
        assert "_banking_reconciliation_on(session)" in src
        assert '_can("view_bank_statement_import")' in src

    def test_entry_does_not_duplicate_deposit_clearing_panel(self):
        entry_src = inspect.getsource(erp._render_banking_pos_settlement_entry)
        assert "_render_bsi_deposit_clearing" not in entry_src
        assert "post_deposit_clearing_match" not in entry_src
        assert "compute_pos_settlement_preview" not in entry_src


class TestI18nNotRawKeys:
    def test_pos_entry_translate_never_returns_key(self):
        for key in _P1B_KEYS:
            for loc in ("en", "tr"):
                text = t(key, loc)
                assert text != key, f"unresolved {loc} key: {key}"
                assert not text.startswith("banking.pos_entry."), (
                    f"{loc}: raw key rendered for {key!r}"
                )

    def test_app_t_resolves_pos_entry_labels(self):
        for key, snippet in _EXPECTED_EN.items():
            text = erp._t(key)
            assert text == TRANSACTIONAL_EN[key]
            assert snippet in text
            assert not text.startswith("banking.pos_entry.")

    def test_pos_entry_keys_in_messages_catalog(self):
        for key in _P1B_KEYS:
            assert MESSAGES["en"][key] == TRANSACTIONAL_EN[key]
            assert MESSAGES["tr"][key] == TRANSACTIONAL_TR[key]


class TestRouteSessionKeys:
    def test_route_keys_match_requirements(self):
        keys = erp._banking_pos_settlement_route_keys()
        assert keys["nav_selection"] == NAV_BANKING
        assert keys["banking_section"] == "import"
        assert keys["bsi_section"] == "match"
        assert keys["bsi_match_kind"] == "card_clearing"
        assert keys["bsi_pos_entry"] is True

    def test_apply_route_sets_explicit_session_keys_and_reruns(self, monkeypatch):
        state: dict = {}
        reruns: list[int] = []
        monkeypatch.setattr(erp.st, "session_state", state)
        monkeypatch.setattr(erp.st, "rerun", lambda: reruns.append(1))
        erp._apply_banking_pos_settlement_route()
        assert state["nav_selection"] == NAV_BANKING
        assert state["banking_section"] == "import"
        assert state["bsi_section"] == "match"
        assert state["bsi_match_kind"] == "card_clearing"
        assert state["bsi_pos_entry"] is True
        assert reruns == [1]

    def test_render_banking_routes_to_statement_import(self):
        src = inspect.getsource(erp.render_banking)
        assert 'section == "import"' in src
        assert "_render_banking_statement_import" in src

    def test_render_bank_statement_import_routes_to_match(self):
        src = inspect.getsource(erp.render_bank_statement_import)
        assert 'section == "match"' in src
        assert "_render_bsi_deposit_clearing" in src

    def test_match_section_honours_pos_entry_before_row_default(self):
        src = inspect.getsource(erp.render_bank_statement_import)
        match_block = src.split('elif section == "match":', 1)[1]
        assert 'st.session_state.pop("bsi_pos_entry", False)' in match_block
        assert '"card_clearing"' in match_block
        assert match_block.index("bsi_pos_entry") < match_block.index(
            "bsi_match_kind_row"
        )

    def test_no_rows_guidance_in_entry_and_match(self):
        entry_src = inspect.getsource(erp._render_banking_pos_settlement_entry)
        assert "get_postable_rows" in entry_src
        assert '_t("banking.pos_entry.no_rows")' in entry_src
        match_src = inspect.getsource(erp.render_bank_statement_import)
        assert 'banking.import.match.no_rows' in match_src


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

    def test_title_and_open_button_copy(self):
        assert TRANSACTIONAL_EN["banking.pos_entry.title"] == "POS / Card Settlement"
        assert TRANSACTIONAL_EN["banking.pos_entry.open"] == "Open POS / Card Settlement"
        assert TRANSACTIONAL_TR["banking.pos_entry.title"] == "POS / Kart Tahsilatı"
        assert TRANSACTIONAL_TR["banking.pos_entry.open"] == "POS / Kart Tahsilatını Aç"
