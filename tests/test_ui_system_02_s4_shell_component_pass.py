"""UI-SYSTEM-02-S4 — unified shell/component pass contract tests."""

from __future__ import annotations

import inspect
from pathlib import Path

import app as erp
from ui.section import mobile_kpi_grid_html

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = ROOT / "ui" / "theme.css"
MOBILE_COMPONENTS = ROOT / "ui" / "mobile_components.css"
MOBILE_REPORTS = ROOT / "ui" / "mobile_reports.css"
MOBILE_TXN = ROOT / "ui" / "mobile_txn.css"


def test_expense_bar_uses_inline_width_not_data_pct_ladder():
    theme = THEME_CSS.read_text(encoding="utf-8")
    assert "data-pct=" not in theme
    src = inspect.getsource(erp.render_dashboard)
    assert 'style="width:' in src or "style='width:" in src
    assert "data-pct" not in src


def test_dead_report_filters_mobile_block_rule_removed():
    """UI-02-D1 resolved — desktop hide is the only visibility rule."""
    theme = THEME_CSS.read_text(encoding="utf-8")
    assert theme.count(".erp-mobile-report-filters") == 1
    assert "display: none !important" in theme.split(".erp-mobile-report-filters", 1)[1][:80]


def test_kpi_grid_single_owner_in_mobile_components():
    components = MOBILE_COMPONENTS.read_text(encoding="utf-8")
    reports = MOBILE_REPORTS.read_text(encoding="utf-8")
    txn = MOBILE_TXN.read_text(encoding="utf-8")
    assert ".erp-mob-kpi-grid," in components
    assert ".erp-mob-kpi-grid--reports-cf" in components
    assert ".erp-mob-kpi-value" in components
    assert ".erp-mob-kpi-grid" not in reports
    assert ".erp-mob-kpi-value" not in reports
    assert ".erp-mob-kpi-grid" not in txn


def test_mobile_kpi_grid_modifier_helper():
    html = mobile_kpi_grid_html("<span/>", modifier="reports-cf")
    assert 'class="erp-mob-kpi-grid erp-mob-kpi-grid--reports-cf"' in html


def test_cash_flow_kpi_uses_reports_cf_modifier():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    cf_block = app.split('key="mob_rpt_cf_kpi"')[1][:900]
    assert 'modifier="reports-cf"' in cf_block


def test_mob_space_tokens_alias_erp_space():
    components = MOBILE_COMPONENTS.read_text(encoding="utf-8")
    for n in range(1, 7):
        assert f"--mob-space-{n}: var(--erp-space-{n}" in components
