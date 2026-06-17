"""UX-STABILIZE-02 — dashboard mobile block guard + post-dispatch scroll reset."""

from __future__ import annotations

import inspect

import app as erp


def _dashboard_src() -> str:
    return inspect.getsource(erp.render_dashboard)


def test_mobile_dashboard_blocks_guarded_by_is_mobile_ui():
    src = _dashboard_src()
    assert "if _is_mobile_ui():" in src
    mobile_block = src.split("if _is_mobile_ui():", 1)[1].split(
        "# ── Alert strip", 1
    )[0]
    assert 'key="erp_mob_ar_ap"' in mobile_block
    assert 'key="erp_mob_liquid"' in mobile_block
    assert "_render_mobile_quick_create()" in mobile_block
    outside = src.split("# ── Alert strip", 1)[0].split("if _is_mobile_ui():", 1)[0]
    assert 'key="erp_mob_ar_ap"' not in outside
    assert 'key="erp_mob_liquid"' not in outside
    assert "_render_mobile_quick_create()" not in outside


def test_desktop_liquid_kpi_grid_unchanged():
    src = _dashboard_src()
    assert "dash.kpi.cash_in_hand" in src
    assert "dash.kpi.bank_balance" in src
    assert "render_kpi_grid" in src.split("erp-dash-hide-mobile", 1)[1]


def test_scroll_helper_called_after_page_dispatch():
    src = inspect.getsource(erp.main)
    dispatch_idx = src.index("_PAGE_DISPATCH.get(selection, render_dashboard)(session)")
    scroll_idx = src.index("_scroll_main_to_top()")
    assert scroll_idx > dispatch_idx


def test_scroll_helper_targets_main_block_container():
    src = inspect.getsource(erp._scroll_main_to_top)
    assert "stMainBlockContainer" in src
    assert "stMain" in src
