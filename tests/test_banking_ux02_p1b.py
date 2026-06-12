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
    "banking.pos_entry.no_rows_focused",
    "banking.pos_entry.go_import",
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

    def test_banking_section_includes_pos_settlement_when_enabled(self):
        src = inspect.getsource(erp.render_banking)
        assert '_banking_pos_settlement_enabled(session)' in src
        assert '("pos_settlement", "banking.pos_entry.title")' in src
        assert 'section == "pos_settlement"' in src
        assert "_render_banking_pos_settlement_section" in src

    def test_entry_uses_t_helper_like_other_banking_labels(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_entry)
        assert "banking.pos_entry.title" in src
        assert "banking.pos_entry.hint" in src
        assert "banking.pos_entry.open" in src
        assert "_banking_pos_entry_label" not in src

    def test_entry_hides_on_focused_pos_settlement_section(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_entry)
        assert 'banking_section") == "pos_settlement"' in src

    def test_entry_button_calls_apply_route(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_entry)
        assert "apply_banking_pos_settlement_route()" in src

    def test_entry_does_not_duplicate_deposit_clearing_panel(self):
        entry_src = inspect.getsource(erp._render_banking_pos_settlement_entry)
        assert "_render_bsi_deposit_clearing" not in entry_src
        assert "post_deposit_clearing_match" not in entry_src


class TestFocusedPosSettlementSection:
    def test_focused_section_renders_clearing_panel_without_import_chrome(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_section)
        assert "render_bank_statement_import" not in src
        assert '_banking_section_select("bsi_section"' not in src
        assert "_render_bsi_deposit_clearing_panel" in src
        assert "_render_bsi_deposit_clearing" not in src.replace(
            "_render_bsi_deposit_clearing_panel", ""
        )

    def test_focused_section_header_and_hint_at_top(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_section)
        idx_title = src.index("banking.pos_entry.title")
        idx_hint = src.index("banking.pos_entry.hint")
        idx_panel = src.index("_render_bsi_deposit_clearing_panel")
        assert idx_title < idx_hint < idx_panel

    def test_focused_section_no_rows_shows_import_link(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_section)
        assert "banking.pos_entry.no_rows_focused" in src
        assert "banking.pos_entry.go_import" in src
        assert 'banking_section"] = "import"' in src

    def test_focused_section_filters_deposit_rows_only(self):
        src = inspect.getsource(erp._render_banking_pos_settlement_section)
        assert "_postable_deposit_rows" in src

    def test_deposit_clearing_panel_is_shared_helper(self):
        panel_src = inspect.getsource(erp._render_bsi_deposit_clearing_panel)
        assert "_render_bsi_match_line_summary" in panel_src
        assert "_render_bsi_deposit_clearing(" in panel_src
        assert "post_deposit_clearing_match" not in panel_src


class TestI18nNotRawKeys:
    def test_pos_entry_translate_never_returns_key(self):
        for key in _P1B_KEYS:
            for loc in ("en", "tr"):
                text = t(key, loc)
                assert text != key, f"unresolved {loc} key: {key}"
                assert not text.startswith("banking.pos_entry."), (
                    f"{loc}: raw key rendered for {key!r}"
                )

    def test_pos_entry_keys_in_messages_catalog(self):
        for key in _P1B_KEYS:
            assert MESSAGES["en"][key] == TRANSACTIONAL_EN[key]
            assert MESSAGES["tr"][key] == TRANSACTIONAL_TR[key]


class TestRouteSessionKeys:
    def test_route_keys_use_pos_settlement_section(self):
        keys = erp._banking_pos_settlement_route_keys()
        assert keys["nav_selection"] == NAV_BANKING
        assert keys["banking_section"] == "pos_settlement"
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
        assert state["banking_section"] == "pos_settlement"
        assert state["bsi_section"] == "match"
        assert state["bsi_match_kind"] == "card_clearing"
        assert state["bsi_pos_entry"] is True
        assert reruns == [1]

    def test_import_match_workflow_unchanged(self):
        src = inspect.getsource(erp.render_bank_statement_import)
        assert 'section == "match"' in src
        assert "_render_bsi_deposit_clearing(session, sel_row, cid)" in src

    def test_match_section_honours_pos_entry_before_row_default(self):
        src = inspect.getsource(erp.render_bank_statement_import)
        match_block = src.split('elif section == "match":', 1)[1]
        assert 'st.session_state.pop("bsi_pos_entry", False)' in match_block
        assert match_block.index("bsi_pos_entry") < match_block.index(
            "bsi_match_kind_row"
        )


class TestPostingUnchanged:
    def test_single_deposit_clearing_posting_function(self):
        assert inspect.getsourcefile(erp._render_bsi_deposit_clearing) is not None
        posting_src = inspect.getsource(erp._render_bsi_deposit_clearing)
        assert "post_deposit_clearing_match(" in posting_src
        panel_src = inspect.getsource(erp._render_bsi_deposit_clearing_panel)
        assert "post_deposit_clearing_match" not in panel_src

    def test_no_sales_revenue_in_settlement_posting(self):
        src = MATCH_POST.read_text(encoding="utf-8")
        assert "Sales Revenue" not in src
        clearing_src = inspect.getsource(erp._render_bsi_deposit_clearing)
        assert "Sales Revenue" not in clearing_src
