"""GLOBAL-STABILITY-HARDENING-01 — no-bypass contract tests (tests only, no runtime patches)."""

from __future__ import annotations

import inspect
import sys
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
    sys.modules["streamlit"].session_state = {}

import app as erp
import ui.banking as banking_ui

from tests import global_stability_hardening_contract as gsh

AUDIT_DOC_PATH = gsh.AUDIT_STOP_REPORT

# ── S1 — Date no-bypass contract ─────────────────────────────────────────────


class TestS1DateNoBypassContract:
    def test_date_canonical_modules_exist(self):
        assert gsh.DATE_UTILS_MODULE.is_file()
        assert gsh.DATE_INPUT_MODULE.is_file()
        assert gsh.AT_DATE_OWNERSHIP_MODULE.is_file()

    def test_app_wires_at_date_ownership_ssot(self):
        src = inspect.getsource(erp._at_resolve_submit_date)
        assert "resolve_submit_date" in src
        app_src = gsh.read_source(gsh.ROOT / "app.py")
        assert "from services.at_date_ownership import" in app_src

    @pytest.mark.parametrize("label,required", list(gsh.DATE_SCOPED_REQUIRED.items()))
    def test_date_scoped_surfaces_use_canonical_helpers(self, label, required):
        resolver = dict(gsh.DATE_SCOPED_SURFACES)[label]
        src = resolver()
        for marker in required:
            assert marker in src, f"{label} missing {marker!r}"

    def test_at_submit_paths_forbid_direct_date_mutation_patterns(self):
        for fn_name in ("_at_process_submit", "_at_gather_submit_fields", "_at_resolve_submit_date"):
            src = inspect.getsource(getattr(erp, fn_name))
            for banned in gsh.AT_DATE_SUBMIT_FORBIDDEN:
                assert banned not in src, f"{fn_name} contains bypass {banned!r}"

    def test_staff_capture_submit_form_uses_parse_bound_date(self):
        src = inspect.getsource(
            __import__("ui.staff_capture", fromlist=["_render_submit_form"])._render_submit_form
        )
        assert "parse_bound_date" in src
        assert "datetime.strptime" not in src

    def test_banking_unsettled_dates_use_preferred_input(self):
        src = inspect.getsource(banking_ui.render_unsettled_card_sales_list_block)
        assert "render_preferred_date_input" in src
        assert "parse_bound_date" in src

    def test_native_calendar_exceptions_are_documented(self):
        for fn_name in gsh.DATE_NATIVE_CALENDAR_EXCEPTIONS:
            assert hasattr(erp, fn_name), f"missing documented exception fn {fn_name}"

    def test_extends_at_date_ownership_all_types_guard(self):
        """Pattern guard from test_at_date_ownership_all_types — submit uses SSOT for all types."""
        src = inspect.getsource(erp._at_process_submit)
        assert "_at_resolve_submit_date" in src or "_at_gather_submit_fields" in src
        gather = inspect.getsource(erp._at_gather_submit_fields)
        assert "at_date" in gather or "_at_resolve_submit_date" in gather


# ── S2 — Money input no-bypass contract ────────────────────────────────────


class TestS2MoneyNoBypassContract:
    def test_amount_input_helpers_exist(self):
        app_src = gsh.read_source(gsh.ROOT / "app.py")
        assert gsh.AMOUNT_INPUT_DEF in app_src
        assert gsh.PARSE_AMOUNT_DEF in app_src

    @pytest.mark.parametrize("label,required", list(gsh.MONEY_SCOPED_REQUIRED.items()))
    def test_money_scoped_surfaces_use_amount_input_path(self, label, required):
        resolver = dict(gsh.MONEY_SCOPED_SURFACES)[label]
        src = resolver()
        for marker in required:
            assert marker in src, f"{label} missing {marker!r}"

    @pytest.mark.parametrize("fn_name", gsh.MONEY_SCAN_APP_FUNCTIONS)
    def test_money_scoped_functions_avoid_raw_number_input(self, fn_name):
        src = inspect.getsource(getattr(erp, fn_name))
        assert "st.number_input" not in src, f"{fn_name} must not use st.number_input for money"

    @pytest.mark.parametrize("fn_name,exceptions", list(gsh.MONEY_NUMBER_INPUT_EXCEPTIONS.items()))
    def test_classified_number_input_exceptions_only(self, fn_name, exceptions):
        src = inspect.getsource(getattr(erp, fn_name))
        keys = gsh.find_st_number_input_keys(src)
        allowed = {key for key, _reason in exceptions}
        unexpected = set(keys) - allowed
        assert not unexpected, (
            f"{fn_name} has unclassified st.number_input keys {unexpected}; "
            f"add to MONEY_NUMBER_INPUT_EXCEPTIONS or switch to amount_input"
        )

    def test_txh_edit_decimal_guard_present(self):
        src = inspect.getsource(erp._txh_edit_amount_changed)
        assert "decimal_equal" in src or "Decimal" in src


# ── S3 — Error formatting no-bypass contract ───────────────────────────────


class TestS3ErrorFormattingNoBypassContract:
    def test_react_shared_normalizer_exists(self):
        api_src = gsh.read_source(gsh.REACT_API_ERROR)
        assert "normalizeApiErrorDetail" in api_src
        assert "errorMessageFromCatch" in api_src
        assert gsh.REACT_LEGACY_STRING_DETAIL not in api_src.split("normalizeApiErrorDetail", 1)[0]

    def test_react_clients_delegate_to_normalizer(self):
        for path in (gsh.REACT_READ_CLIENT, gsh.REACT_WRITE_CLIENT):
            src = gsh.read_source(path)
            assert "normalizeApiErrorDetail" in src

    def test_homepage_uses_catch_helper_not_string_coercion(self):
        home = gsh.read_source(gsh.REACT_PAGES_DIR / "HomePage.tsx")
        assert "errorMessageFromCatch" in home
        assert gsh.REACT_LEGACY_STRING_DETAIL not in home

    def test_react_legacy_error_pages_frozen_allowlist(self):
        found = gsh.react_pages_with_legacy_error_pattern()
        assert found == gsh.REACT_LEGACY_ERROR_PAGES_FROZEN, (
            "React legacy error bypass set changed — migrate new pages to "
            "errorMessageFromCatch or update frozen allowlist explicitly"
        )

    def test_react_write_page_uses_normalized_api_error_detail(self):
        write_page = gsh.read_source(gsh.REACT_PAGES_DIR / "NewTransactionPage.tsx")
        assert "apiErr.detail" in write_page
        assert gsh.REACT_LEGACY_STRING_DETAIL not in write_page

    def test_python_banking_statement_post_error_helper_exists(self):
        for helper in gsh.PYTHON_ERROR_HELPERS:
            assert hasattr(erp, helper), f"missing Python error helper {helper}"

    def test_no_new_react_pages_with_string_detail_outside_allowlist(self):
        for path in gsh.REACT_PAGES_DIR.glob("*Page.tsx"):
            name = path.name
            if name in gsh.REACT_WRITE_ERROR_EXCEPTIONS:
                continue
            src = gsh.read_source(path)
            if gsh.REACT_LEGACY_STRING_DETAIL in src:
                assert name in gsh.REACT_LEGACY_ERROR_PAGES_FROZEN


# ── S4 — Banking import ownership contract ─────────────────────────────────


class TestS4BankingImportOwnershipContract:
    def test_canonical_upload_navigator_exists(self):
        assert hasattr(banking_ui, "banking_apply_statement_import_upload_route")
        assert hasattr(banking_ui, "banking_navigate_statement_import_upload")

    def test_pos_settlement_go_import_uses_canonical_navigator(self):
        src = inspect.getsource(banking_ui.render_banking_pos_settlement_section)
        assert "banking_navigate_statement_import_upload()" in src

    def test_upload_tab_has_file_uploader_not_empty_picker(self):
        src = inspect.getsource(erp.render_bank_statement_import)
        upload = src.split('if section == "upload":', 1)[1].split("elif section ==", 1)[0]
        assert "bsi_file_uploader" in upload
        assert "file_uploader" in upload
        match = src.split('elif section == "match":', 1)[1].split("elif section ==", 1)[0]
        assert "banking.import.match.no_rows" in match

    def test_recon_on_branch_uses_staging_import_owner(self):
        src = inspect.getsource(erp._render_banking_statement_import)
        assert "_banking_reconciliation_on" in src
        assert "render_bank_statement_import" in src

    def test_recon_off_legacy_csv_branch_explicitly_classified(self):
        src = inspect.getsource(erp._render_banking_statement_import)
        assert "bank.import_csv_legacy_hint" in src
        assert "csv_import_file" in src
        assert "not _banking_reconciliation_on(session)" in src

    def test_match_tab_not_default_for_import_intent_navigation(self):
        state = erp._banking_pos_settlement_route_keys()
        banking_ui.banking_apply_statement_import_upload_route()
        erp.st.session_state.update(state)
        banking_ui.banking_apply_statement_import_upload_route()
        assert erp.st.session_state["bsi_section"] == "upload"


# ── S5 — Audit stop report contract ────────────────────────────────────────


class TestS5AuditStopReportContract:
    @pytest.fixture(scope="class")
    def doc_text(self) -> str:
        assert AUDIT_DOC_PATH.exists()
        return AUDIT_DOC_PATH.read_text(encoding="utf-8")

    def test_audit_doc_exists(self):
        assert AUDIT_DOC_PATH.exists()
        assert AUDIT_DOC_PATH.stat().st_size > 0

    def test_audit_matrix_and_families(self, doc_text):
        low = doc_text.lower()
        for col in ("intended global rule", "canonical owner", "bypasses", "duplicate paths"):
            assert col in low
        for fam in ("date-01", "obs-011", "react-local-obs", "nav-ux-02"):
            assert fam in low

    def test_audit_owners_tests_and_answers(self, doc_text):
        low = doc_text.lower()
        assert "registry/date_utils.py" in low
        assert "test_at_date_ownership_all_types" in low
        assert "truly global" in low
        assert "need centralization" in low or "centralize" in low
        assert "no code changes" in low

    def test_hardening_suite_referenced_in_roadmap(self):
        roadmap = gsh.read_source(gsh.ROOT / "ROADMAP.md").lower()
        assert "global-stability-hardening-01" in roadmap
        assert "test_global_stability_hardening_01" in roadmap
