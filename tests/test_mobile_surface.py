"""Mobile overlay surface helpers — one active surface rule (Phase 1 + 2)."""
from __future__ import annotations

import inspect
from pathlib import Path

import app as erp

ROOT = Path(__file__).resolve().parents[1]


def _mobile_state(**extra) -> dict:
    base = {
        "_erp_mobile_ui": True,
        "mobile_hub_open": "more",
        "mob_at_picker": "vendor",
        "mob_at_picker_search": "acme",
        "mob_qc_scan_open": True,
        "_confirm_company_switch": True,
        "_switch_target_company_id": 2,
    }
    base.update(extra)
    return base


def test_mobile_close_app_surfaces_clears_overlay_keys(monkeypatch):
    state = _mobile_state(mob_co_switch_open=True, mob_profile_open=True)
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mobile_close_app_surfaces()
    assert "mobile_hub_open" not in state
    assert "mob_at_picker" not in state
    assert "mob_at_picker_search" not in state
    assert "mob_qc_scan_open" not in state
    assert "mob_co_switch_open" not in state
    assert "mob_profile_open" not in state
    assert state.get("_confirm_company_switch") is True


def test_mobile_close_app_surfaces_noop_on_desktop(monkeypatch):
    state = _mobile_state(_erp_mobile_ui=False)
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mobile_close_app_surfaces()
    assert state.get("mobile_hub_open") == "more"
    assert state.get("mob_at_picker") == "vendor"


def test_mobile_open_surface_at_picker_clears_hub(monkeypatch):
    state = _mobile_state()
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mobile_open_surface("at_picker")
    assert "mobile_hub_open" not in state
    assert "mob_qc_scan_open" not in state
    assert "mob_at_picker_search" not in state
    assert "_confirm_company_switch" not in state


def test_mobile_open_surface_hub_clears_picker(monkeypatch):
    state = _mobile_state()
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mobile_open_surface("hub:reports")
    assert state.get("mobile_hub_open") == "reports"
    assert "mob_at_picker" not in state
    assert "mob_at_picker_search" not in state
    assert "mob_qc_scan_open" not in state
    assert "_confirm_company_switch" not in state


def test_mob_at_open_picker_clears_hub_and_sets_kind(monkeypatch):
    state = _mobile_state()
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mob_at_open_picker("invoice")
    assert state.get("mob_at_picker") == "invoice"
    assert "mobile_hub_open" not in state


def test_company_switch_menu_closes_surfaces_before_confirm():
    src = inspect.getsource(erp._render_company_switch_menu)
    assert "_mobile_close_app_surfaces()" in src
    idx_close = src.index("_mobile_close_app_surfaces()")
    idx_confirm = src.index('st.session_state["_confirm_company_switch"] = True')
    assert idx_close < idx_confirm


def test_company_switch_confirm_closes_surfaces_on_render():
    src = inspect.getsource(erp._render_company_switch_confirm)
    assert '_mobile_open_surface("company_switch_confirm")' in src


def test_page_change_clears_mobile_overlay_keys():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    idx = src.index('if st.session_state.get("_current_page") != selection:')
    block = src[idx : idx + 1050]
    for key in (
        "mobile_hub_open",
        "mob_at_picker",
        "mob_at_picker_search",
        "mob_qc_scan_open",
        "mob_co_switch_open",
        "mob_profile_open",
    ):
        assert f'st.session_state.pop("{key}", None)' in block
    assert "_mobile_clear_company_switch_confirm()" in block


def test_mobile_open_surface_profile_clears_hub(monkeypatch):
    state = {"_erp_mobile_ui": True, "mobile_hub_open": "more", "mob_at_picker": "vendor"}
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mobile_open_surface("profile")
    assert state.get("mob_profile_open") is True
    assert "mobile_hub_open" not in state
    assert "mob_at_picker" not in state


def test_mobile_open_surface_co_switch_sets_sheet_flag(monkeypatch):
    state = {"_erp_mobile_ui": True, "mobile_hub_open": "more"}
    monkeypatch.setattr(erp.st, "session_state", state)
    erp._mobile_open_surface("co_switch")
    assert state.get("mob_co_switch_open") is True
    assert "mobile_hub_open" not in state


def test_css_confirm_suppresses_co_switch_sheet_on_mobile():
    widgets = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    shell = (ROOT / "ui" / "mobile_shell.css").read_text(encoding="utf-8")
    assert "erp-mobile-co-switch-host" in shell
    marker = "/* Confirm active — suppress hub/header sheets"
    block = widgets.split(marker, 1)[1].split("/* Header popover open", 1)[0]
    assert "html.erp-mobile" in block
    assert "erp_mob_co_switch_sheet" in block
    assert "z-index: 10085" in shell
    assert "erp_mob_co_switch_sheet" in shell


def test_e13_mobile_sheet_chrome_owned_by_mobile_shell():
    """MOBILE-14 E13 — profile/co-switch/hub list chrome in mobile_shell.css only."""
    widgets = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    shell = (ROOT / "ui" / "mobile_shell.css").read_text(encoding="utf-8")
    for marker in (
        "/* E13 — hub sheet list chrome",
        "/* E13 — mobile profile sheet",
        "/* E13 — mobile company switch sheet",
    ):
        assert marker in shell
    assert "erp-mobile-hub-grab" in shell
    assert "erp-mobile-profile-title" in shell
    assert "erp-mobile-co-switch-title" in shell
    assert "z-index: 10082" in shell
    assert "z-index: 10085" in shell
    # Sheet shell styling must not remain duplicated in widgets.css
    assert "erp-mobile-profile-title" not in widgets
    assert "erp-mobile-co-switch-title" not in widgets
    assert "z-index: 10060" not in widgets
    assert "z-index: 10078" not in widgets
    assert "z-index: 10080" not in widgets
    assert "z-index: 10082" not in widgets
    assert "z-index: 10085" not in widgets
    assert ".erp-mobile-hub-title" not in widgets


def test_css_confirm_host_suppresses_hub_mobile_only():
    widgets = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    marker = "/* Confirm active — suppress hub/header sheets"
    assert marker in widgets
    block = widgets.split(marker, 1)[1].split("/* Header popover open", 1)[0]
    assert "html.erp-mobile" in block
    assert "erp-co-switch-confirm-host" in block
    assert "erp_mob_hub_sheet" in block
    assert "erp_mob_co_switch_sheet" in block
    assert "erp_mob_profile_sheet" in block
    assert "erp-mobile-hub-host" in block
    assert "erp_mob_bottom_bar" in block
    assert "pointer-events: none" in block


def test_css_confirm_guards_not_applied_without_erp_mobile_class():
    widgets = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    marker = "/* Confirm active — suppress hub/header sheets"
    block = widgets.split(marker, 1)[1].split("/* Header popover open", 1)[0]
    assert block.count("html.erp-mobile") >= 4
    assert "html.erp-mobile\n    [data-testid" in block


def test_desktop_header_popover_contract_unchanged():
    src = inspect.getsource(erp._render_hdr_toolbar)
    assert "hdr_profile_pop" in src
    assert "if _is_mobile_ui():" in src
    desktop_block = src.split("else:")[-1]
    assert "with st.popover(_initials" in desktop_block
    assert "show_inline_company_switch=len(_prof_memberships) > 1" in desktop_block


def test_bottom_nav_hub_uses_mobile_open_surface():
    src = inspect.getsource(erp._render_mobile_bottom_nav)
    assert '_mobile_open_surface(f"hub:{payload}")' in src


def test_mob_at_triggers_use_open_picker_helper():
    helper_src = inspect.getsource(erp._mob_at_open_picker)
    assert 'st.session_state["mob_at_picker"] = picker_kind' in helper_src
    trigger_fns = (
        erp._mob_at_render_category_trigger,
        erp._mob_at_render_subcategory_trigger,
        erp._mob_at_render_vendor_trigger,
        erp._mob_at_render_invoice_trigger,
        erp._mob_at_render_payable_trigger,
        erp._mob_at_render_bank_trigger,
        erp._mob_at_render_bank_pay_trigger,
        erp._mob_at_render_card_bank_trigger,
    )
    for fn in trigger_fns:
        src = inspect.getsource(fn)
        assert "_mob_at_open_picker(" in src
        assert 'st.session_state["mob_at_picker"]' not in src
