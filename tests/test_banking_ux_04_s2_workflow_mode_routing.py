"""BANKING-UX-04-S2 — workflow mode setting + banking UI routing contract tests."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import app as erp
import pytest

from registry.banking_config import (
    BANKING_WORKFLOW_MODE_DEFAULT,
    BANKING_WORKFLOW_MODE_IDS,
    banking_normalize_workflow_mode,
    banking_workflow_mode,
)
from registry.loader import get_setting_def
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from ui.banking import (
    banking_apply_session_landing,
    banking_build_section_options,
    banking_section_extra_valid,
    banking_show_manual_advanced_panel,
    banking_workflow_default_section,
)

ROOT = Path(__file__).resolve().parents[1]
MATCH_POST = ROOT / "reconciliation" / "match_post.py"
POSTING = ROOT / "services" / "posting.py"


class TestWorkflowModeCatalog:
    def test_setting_exists_company_scoped(self):
        defn = get_setting_def("banking.workflow_mode")
        assert defn.scope == "company"
        assert defn.type == "enum"
        assert defn.default == "statement_first"
        assert set(defn.options) == set(BANKING_WORKFLOW_MODE_IDS)

    def test_normalize_invalid_falls_back(self):
        assert banking_normalize_workflow_mode(None) == BANKING_WORKFLOW_MODE_DEFAULT
        assert banking_normalize_workflow_mode("bogus") == BANKING_WORKFLOW_MODE_DEFAULT
        assert banking_normalize_workflow_mode("hybrid") == "hybrid"


class TestCompanyIsolation:
    def test_workflow_mode_reads_per_company(self):
        session = MagicMock()
        with patch(
            "registry.banking_config.get_setting",
            side_effect=lambda _s, key, company_id: {
                ("banking.workflow_mode", 1): "statement_first",
                ("banking.workflow_mode", 2): "manual_first",
            }[(key, company_id)],
        ):
            assert banking_workflow_mode(session, 1) == "statement_first"
            assert banking_workflow_mode(session, 2) == "manual_first"


class TestSectionRouting:
    def test_statement_first_hides_accounts_from_chips(self):
        opts = banking_build_section_options(
            workflow_mode="statement_first",
            show_cockpit=True,
            show_pos_settlement=False,
            show_settings=True,
        )
        ids = [o[0] for o in opts]
        assert "accounts" not in ids
        assert ids[0] == "cockpit"
        assert "import" in ids

    def test_statement_first_keeps_manual_reachable(self):
        assert banking_section_extra_valid("statement_first") == frozenset({"accounts"})
        assert banking_show_manual_advanced_panel("statement_first", "import") is True
        assert banking_show_manual_advanced_panel("statement_first", "accounts") is False

    def test_hybrid_shows_both(self):
        opts = banking_build_section_options(
            workflow_mode="hybrid",
            show_cockpit=True,
            show_pos_settlement=True,
            show_settings=True,
        )
        ids = [o[0] for o in opts]
        assert "accounts" in ids
        assert "import" in ids
        assert ids.index("accounts") < ids.index("import")

    def test_manual_first_accounts_first(self):
        opts = banking_build_section_options(
            workflow_mode="manual_first",
            show_cockpit=True,
            show_pos_settlement=False,
            show_settings=False,
        )
        ids = [o[0] for o in opts]
        assert ids[0] == "accounts"
        assert "import" in ids

    def test_statement_first_default_landing_prefers_cockpit_then_import(self):
        opts = banking_build_section_options(
            workflow_mode="statement_first",
            show_cockpit=True,
            show_pos_settlement=False,
            show_settings=False,
        )
        assert banking_workflow_default_section(opts, "statement_first") == "cockpit"
        opts_no_cockpit = banking_build_section_options(
            workflow_mode="statement_first",
            show_cockpit=False,
            show_pos_settlement=False,
            show_settings=False,
        )
        assert banking_workflow_default_section(opts_no_cockpit, "statement_first") == "import"

    def test_manual_first_default_landing_accounts(self):
        opts = banking_build_section_options(
            workflow_mode="manual_first",
            show_cockpit=False,
            show_pos_settlement=False,
            show_settings=False,
        )
        assert banking_workflow_default_section(opts, "manual_first") == "accounts"


class TestPermissionInvariance:
    def test_mode_does_not_add_gated_sections(self):
        opts = banking_build_section_options(
            workflow_mode="hybrid",
            show_cockpit=False,
            show_pos_settlement=False,
            show_settings=False,
        )
        ids = [o[0] for o in opts]
        assert "cockpit" not in ids
        assert "settings" not in ids
        assert "pos_settlement" not in ids
        assert "import" in ids
        assert "accounts" in ids


class TestRenderBankingWiring:
    def test_render_banking_uses_workflow_helpers(self):
        src = inspect.getsource(erp.render_banking)
        assert "_banking_workflow_mode" in src
        assert "_banking_build_section_options" in src
        assert "_banking_section_extra_valid" in src
        assert "_render_banking_manual_advanced_if_needed" in src
        assert "banking.workflow_mode" in inspect.getsource(erp._render_banking_page_settings)

    def test_getter_shim_mirrors_registry(self):
        src = inspect.getsource(erp._banking_workflow_mode)
        assert "banking_workflow_mode" in src
        assert "_current_company_id" in src


class TestPostingInvariance:
    def test_s2_does_not_touch_posting_kernel(self):
        assert "banking.workflow_mode" not in POSTING.read_text(encoding="utf-8")

    def test_s2_does_not_touch_match_post(self):
        assert "banking.workflow_mode" not in MATCH_POST.read_text(encoding="utf-8")

    def test_workflow_mode_helpers_have_no_posting_imports(self):
        text = (ROOT / "ui" / "banking.py").read_text(encoding="utf-8")
        block = text.split("def banking_build_section_options", 1)[1].split(
            "def banking_match_kind_confidence", 1
        )[0]
        assert "services.posting" not in block
        assert "match_post" not in block


class TestWording:
    _WORKFLOW_KEYS = (
        "settings.banking.workflow_mode_prompt",
        "settings.banking.workflow_mode.statement_first",
        "settings.banking.workflow_mode.hybrid",
        "settings.banking.workflow_mode.manual_first",
        "bank.advanced.section",
        "bank.advanced.open_manual",
    )

    @pytest.mark.parametrize("key", _WORKFLOW_KEYS)
    def test_en_keys_present(self, key):
        assert key in TRANSACTIONAL_EN

    @pytest.mark.parametrize("key", _WORKFLOW_KEYS)
    def test_tr_keys_present(self, key):
        assert key in TRANSACTIONAL_TR

    def test_owner_prompt_plain_language(self):
        assert TRANSACTIONAL_EN["settings.banking.workflow_mode_prompt"].lower().startswith(
            "how do you record"
        )


class TestHybridLandingPreservesRegistryMechanism:
    def test_hybrid_uses_banking_resolve_landing(self):
        src = inspect.getsource(banking_apply_session_landing)
        assert "banking_resolve_landing" in src
        assert "statement_first" in src
        assert "manual_first" in src
