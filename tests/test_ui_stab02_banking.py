"""UI-STAB-02 — Banking presentation layer separation."""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import app as erp
import ui.banking as banking_ui
from registry.nav_keys import NAV_BANKING

ROOT = Path(__file__).resolve().parents[1]
BANKING_UI_SRC = (ROOT / "ui" / "banking.py").read_text(encoding="utf-8")
MATCH_POST = ROOT / "reconciliation" / "match_post.py"

_EXTRACTED = (
    "banking_section_select",
    "banking_pos_settlement_route_keys",
    "apply_banking_pos_settlement_route",
    "render_pos_settlement_preview_block",
    "banking_match_failure_label",
    "render_pos_match_failure_block",
    "render_card_sales_clearing_visibility_block",
    "render_unsettled_card_sales_list_block",
    "render_banking_pos_settlement_entry",
    "render_banking_pos_settlement_section",
)

_POSTING_PATTERNS = (
    "post_deposit_clearing_match",
    "create_journal_entry",
    "apply_account_balance_delta",
    "post_cc_subledger_charge",
    "post_generic_deposit",
    "post_bank_charge_outflow",
)


class TestPresentationModuleExists:
    def test_ui_banking_module_has_extracted_renderers(self):
        for name in _EXTRACTED:
            assert hasattr(banking_ui, name), f"missing {name}"

    def test_app_reexports_banking_presentation_aliases(self):
        assert erp._banking_section_select is banking_ui.banking_section_select
        assert erp._render_pos_settlement_preview_block is (
            banking_ui.render_pos_settlement_preview_block
        )
        assert erp._render_pos_match_failure_block is (
            banking_ui.render_pos_match_failure_block
        )
        assert erp._render_card_sales_clearing_visibility_block is (
            banking_ui.render_card_sales_clearing_visibility_block
        )
        assert erp._render_unsettled_card_sales_list_block is (
            banking_ui.render_unsettled_card_sales_list_block
        )
        assert erp._render_banking_pos_settlement_entry is (
            banking_ui.render_banking_pos_settlement_entry
        )
        assert erp._render_banking_pos_settlement_section is (
            banking_ui.render_banking_pos_settlement_section
        )
        assert erp._banking_pos_settlement_route_keys is (
            banking_ui.banking_pos_settlement_route_keys
        )
        assert erp._apply_banking_pos_settlement_route is (
            banking_ui.apply_banking_pos_settlement_route
        )
        assert erp._banking_match_failure_label is banking_ui.banking_match_failure_label


class TestRouteKeysUnchanged:
    def test_pos_settlement_route_keys(self):
        keys = banking_ui.banking_pos_settlement_route_keys()
        assert keys["nav_selection"] == NAV_BANKING
        assert keys["banking_section"] == "pos_settlement"
        assert keys["bsi_section"] == "match"
        assert keys["bsi_match_kind"] == "card_clearing"
        assert keys["bsi_pos_entry"] is True


class TestBankingPageWiring:
    def test_render_banking_uses_chip_selector_and_pos_entry(self):
        src = inspect.getsource(erp.render_banking)
        assert '_banking_section_select("banking_section"' in src
        assert "_render_banking_pos_settlement_entry" in src
        assert 'section == "pos_settlement"' in src
        assert "_render_banking_pos_settlement_section" in src

    def test_pos_focused_section_reachable(self):
        src = inspect.getsource(banking_ui.render_banking_pos_settlement_section)
        assert "_render_bsi_deposit_clearing_panel" in src
        assert "render_bank_statement_import" not in src

    def test_deposit_clearing_orchestration_stays_in_app(self):
        src = inspect.getsource(erp._render_bsi_deposit_clearing)
        assert "_render_pos_settlement_preview_block" in src
        assert "_render_card_sales_clearing_visibility_block" in src
        assert "_render_unsettled_card_sales_list_block" in src
        assert "_render_pos_match_failure_block" in src
        assert "post_deposit_clearing_match" in src


class TestPanelContracts:
    def test_settlement_preview_block_present(self):
        src = inspect.getsource(banking_ui.render_pos_settlement_preview_block)
        assert "banking.pos_preview.section_title" in src
        assert "banking.pos_preview.revenue_note" in src
        assert ".metric(" in src

    def test_clearing_visibility_block_present(self):
        src = inspect.getsource(
            banking_ui.render_card_sales_clearing_visibility_block
        )
        assert "compute_clearing_visibility" in src
        assert "banking.clearing_visibility.section_title" in src

    def test_unsettled_sales_list_present(self):
        src = inspect.getsource(banking_ui.render_unsettled_card_sales_list_block)
        assert "fetch_unsettled_card_sales_for_visibility" in src
        assert "banking.unsettled_card_sales.section_title" in src
        assert "_render_readable_df" in src

    def test_match_failure_panel_present(self):
        src = inspect.getsource(banking_ui.render_pos_match_failure_block)
        assert "banking.match_failure.section_title" in src
        assert "banking_match_failure_label" in src


class TestNoPostingInUiModule:
    def test_ui_banking_has_no_posting_or_je_mutations(self):
        for pat in _POSTING_PATTERNS:
            assert pat not in BANKING_UI_SRC, f"posting leak: {pat}"

    def test_ui_banking_does_not_define_accounting_helpers(self):
        assert "def calculate_account_balance" not in BANKING_UI_SRC
        assert "def get_unsettled_card_sales" not in BANKING_UI_SRC
        assert "def post_" not in BANKING_UI_SRC

    def test_posting_remains_in_app_deposit_clearing(self):
        src = inspect.getsource(erp._render_bsi_deposit_clearing)
        assert "post_deposit_clearing_match(" in src
        assert inspect.getsourcefile(erp._render_bsi_deposit_clearing).endswith(
            "app.py"
        )

    def test_match_post_unchanged(self):
        src = MATCH_POST.read_text(encoding="utf-8")
        assert "def post_deposit_clearing_match" in src
        assert "je_lines = [(bank_gl.id, deposit_amt, 0)]" in src


class TestReadOnlyPanels:
    def test_p2_p3_p4_panels_have_no_post_buttons(self):
        for fn in (
            banking_ui.render_card_sales_clearing_visibility_block,
            banking_ui.render_unsettled_card_sales_list_block,
            banking_ui.render_pos_match_failure_block,
            banking_ui.render_pos_settlement_preview_block,
        ):
            src = inspect.getsource(fn)
            assert "post_deposit_clearing_match" not in src
            assert "st.button" not in src

    def test_chip_selector_uses_locale_keys_not_raw(self):
        src = inspect.getsource(banking_ui.banking_section_select)
        assert "erp._t(msg_key)" in src
        assert "erp-bank-sel-chip-host" in src


class TestLazyAppImport:
    def test_ui_banking_uses_lazy_erp_accessor(self):
        assert "def _erp():" in BANKING_UI_SRC
        assert "import app as app_module" in BANKING_UI_SRC
        assert re.search(r"^import app\b", BANKING_UI_SRC, re.M) is None
