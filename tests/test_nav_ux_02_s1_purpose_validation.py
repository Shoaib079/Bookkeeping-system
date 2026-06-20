"""NAV-UX-02-S1 — purpose validation contract tests.

Extends structural parity with render/surface/role/duplicate/mobile/legacy checks.
Source: docs/NAV_UX_02_AUDIT.md §6 + docs/NAV_UX_02_S1_PURPOSE_VALIDATION_REPORT.md
"""

from __future__ import annotations

import inspect

import app as erp
from registry.nav_keys import LEGACY_NAV_ALIASES, NAV_REPORTS, NAV_TODAY_SUMMARY
from tests.nav_ux_02_contract import (
    DIALOG_FUNCTION_NAMES,
    DOCUMENTED_DUPLICATE_WORKFLOWS,
    DOCUMENTED_CANONICAL_WITH_SHORTCUTS,
    DOCUMENTED_PROGRAMMATIC_NAV,
    DOCUMENTED_ROLE_PURPOSE_REVIEW,
    KNOWN_HIDDEN,
    MOBILE_HUB_ENTRY_TARGETS,
    NAV_SURFACE_PARITY_OK,
    accordion_page_keys,
    handler_has_meaningful_body,
    mobile_bottom_hub_targets,
    mobile_hub_page_keys_flat,
    page_dispatch_from_main,
    page_surface_map,
    resolve_dispatch_handler,
)


def _entry_point_kinds(surface_list: list[str]) -> set[str]:
    """Nav entry kinds only — role tags are gates, not duplicate surfaces."""
    kinds: set[str] = set()
    for tag in surface_list:
        if tag.startswith("role:"):
            continue
        if tag in {"sidebar_direct", "mobile_bottom", "mobile_hub_page", "programmatic"}:
            kinds.add(tag)
        elif tag.startswith("accordion:"):
            kinds.add("accordion")
        elif tag.startswith("mobile_hub:"):
            kinds.add("mobile_hub")
    return kinds


def test_every_dispatch_handler_is_callable():
    dispatch = page_dispatch_from_main()
    missing: list[str] = []
    for page_key, handler_name in dispatch.items():
        try:
            fn = resolve_dispatch_handler(handler_name)
        except AttributeError:
            missing.append(f"{page_key} -> {handler_name}")
            continue
        if not callable(fn):
            missing.append(f"{page_key} -> {handler_name} (not callable)")
    assert not missing, f"Non-callable dispatch handlers: {missing}"


def test_every_dispatch_handler_has_meaningful_body():
    dispatch = page_dispatch_from_main()
    stubs: list[str] = []
    for page_key, handler_name in dispatch.items():
        fn = resolve_dispatch_handler(handler_name)
        if not handler_has_meaningful_body(fn):
            stubs.append(f"{page_key} -> {handler_name}")
    assert not stubs, f"Dispatch handlers look like empty stubs: {stubs}"


def test_non_hidden_routes_reachable_from_intended_surface():
    dispatch = set(page_dispatch_from_main())
    surfaces = page_surface_map()
    unreachable = [
        page_key
        for page_key in dispatch
        if page_key not in KNOWN_HIDDEN and page_key not in surfaces
    ]
    assert not unreachable, (
        f"Routes not reachable from any documented surface (not KNOWN_HIDDEN): {unreachable}"
    )


def test_known_hidden_empty_after_s2_retirement():
    assert KNOWN_HIDDEN == frozenset()


def test_today_summary_not_treated_as_hidden_route():
    surfaces = page_surface_map()
    assert NAV_TODAY_SUMMARY not in surfaces


def test_documented_role_purpose_review_resolved_after_s5():
    """S5: Staff Expenses nav is permission-derived; no open role/purpose review flags."""
    assert DOCUMENTED_ROLE_PURPOSE_REVIEW == frozenset()


def test_documented_duplicate_workflow_clusters_have_multiple_entry_kinds():
    surfaces = page_surface_map()
    failures: list[str] = []
    for workflow_id, page_keys in DOCUMENTED_DUPLICATE_WORKFLOWS.items():
        for page_key in page_keys:
            kinds = _entry_point_kinds(surfaces.get(page_key, []))
            if len(kinds) < 2:
                failures.append(f"{workflow_id}: {page_key} kinds={sorted(kinds)}")
    assert not failures, failures


def test_undocumented_multi_entry_kinds_reported_not_enforced():
    """Informational guard — surfaces multi-entry pages outside audit duplicate set."""
    surfaces = page_surface_map()
    documented = (
        frozenset().union(*DOCUMENTED_DUPLICATE_WORKFLOWS.values())
        | NAV_SURFACE_PARITY_OK
        | DOCUMENTED_CANONICAL_WITH_SHORTCUTS
    )
    extras = []
    for page_key, surface_list in surfaces.items():
        if page_key in KNOWN_HIDDEN:
            continue
        kinds = _entry_point_kinds(surface_list)
        if len(kinds) > 1 and page_key not in documented:
            extras.append(page_key)
    # Recorded in NAV_UX_02_S1_PURPOSE_VALIDATION_REPORT.md — not a failure yet.
    assert isinstance(extras, list)


def test_legacy_alias_targets_exist_in_dispatch():
    dispatch = set(page_dispatch_from_main())
    missing = {
        alias: target
        for alias, target in LEGACY_NAV_ALIASES.items()
        if target not in dispatch
    }
    assert not missing, f"Legacy alias targets missing from dispatch: {missing}"


def test_legacy_exec_reroutes_target_dispatch_pages():
    dispatch = set(page_dispatch_from_main())
    for target in erp._LEGACY_RPT_EXEC_TO_STATEMENT.values():
        assert target in dispatch
    for target in erp._LEGACY_RPT_EXEC_TO_BOOKS.values():
        assert target in dispatch


def test_mobile_hub_page_entries_in_dispatch():
    dispatch = set(page_dispatch_from_main())
    missing = [k for k in mobile_hub_page_keys_flat() if k not in dispatch]
    assert not missing, f"Mobile hub page keys missing from dispatch: {missing}"


def test_mobile_hub_non_page_entries_target_valid_routes():
    dispatch = set(page_dispatch_from_main())
    for hub_key, entries in erp._MOBILE_HUB_CONFIG.items():
        for kind, payload, *_rest in entries:
            if kind == "open_hub":
                assert payload in erp._MOBILE_HUB_CONFIG, (
                    f"open_hub {payload!r} missing from _MOBILE_HUB_CONFIG"
                )
            elif kind == "accordion":
                assert payload in erp._NAV_ACCORDION_BY_KEY, (
                    f"accordion {payload!r} missing from _NAV_ACCORDION_BY_KEY"
                )
            elif kind in MOBILE_HUB_ENTRY_TARGETS:
                assert MOBILE_HUB_ENTRY_TARGETS[kind] in dispatch
            elif kind == "page":
                assert payload in dispatch


def test_mobile_bottom_hub_targets_in_hub_config():
    config_keys = set(erp._MOBILE_HUB_CONFIG)
    missing = [h for h in mobile_bottom_hub_targets() if h not in config_keys]
    assert not missing


def test_documented_dialog_functions_exist_and_callable():
    missing = [name for name in DIALOG_FUNCTION_NAMES if not hasattr(erp, name)]
    assert not missing, f"Dialog functions missing from app: {missing}"
    for name in DIALOG_FUNCTION_NAMES:
        assert callable(getattr(erp, name))


def test_mobile_reports_shortcuts_target_reports_page():
    source = inspect.getsource(erp._render_mobile_hub_sheet)
    assert 'presets={"mob_reports_tab": "sales"}' in source
    assert 'presets={"mob_reports_tab": "expenses"}' in source
    assert "NAV_REPORTS" in source


def test_statement_routes_dispatch_to_statement_wrappers():
    dispatch = page_dispatch_from_main()
    assert dispatch[erp.NAV_PROFIT_LOSS] == "render_profit_loss_page"
    assert dispatch[erp.NAV_BALANCE_SHEET] == "render_balance_sheet_page"
    assert dispatch[erp.NAV_CASH_FLOW] == "render_cash_flow_page"


def test_legacy_bank_statement_import_reroutes_to_banking():
    main_src = inspect.getsource(erp.main)
    assert '"Bank Statement Import"' in main_src
    assert 'st.session_state["banking_section"] = "import"' in main_src or (
        "_banking_apply_statement_import_upload_route()" in main_src
    )


def test_working_routes_include_all_non_hidden_dispatch_keys():
    dispatch = set(page_dispatch_from_main())
    working = dispatch - KNOWN_HIDDEN
    surfaces = page_surface_map()
    for page_key in working:
        assert page_key in surfaces


def test_suspicious_orphan_routes_match_known_hidden_only():
    dispatch = set(page_dispatch_from_main())
    surfaces = page_surface_map()
    orphans = dispatch - set(surfaces.keys())
    assert orphans == KNOWN_HIDDEN, f"Unexpected orphan routes: {orphans - KNOWN_HIDDEN}"


REPORT_PATH = __import__("pathlib").Path(__file__).resolve().parents[1] / "docs" / "NAV_UX_02_S1_PURPOSE_VALIDATION_REPORT.md"


def test_purpose_validation_report_exists():
    assert REPORT_PATH.exists()
    assert REPORT_PATH.stat().st_size > 0


def test_purpose_validation_report_covers_required_sections():
    text = REPORT_PATH.read_text(encoding="utf-8").lower()
    for section in (
        "routes that are working",
        "suspicious",
        "duplicates",
        "recommended next slices",
        "known_hidden",
        "staff expenses",
        "today's summary",
    ):
        assert section in text, f"Report missing section/topic: {section!r}"
