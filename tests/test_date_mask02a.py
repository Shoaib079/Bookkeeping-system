"""DATE-MASK-02A — non-posting filter/statement date ranges use preferred text inputs."""

from __future__ import annotations

import datetime
import inspect

import app as erp


def _block_after(src: str, marker: str, end_marker: str | None = None) -> str:
    chunk = src.split(marker, 1)[1]
    if end_marker:
        chunk = chunk.split(end_marker, 1)[0]
    return chunk


def test_partner_statement_range_migrated():
    src = inspect.getsource(erp._render_partner_statement)
    assert "_render_preferred_date_range_cols" in src
    assert '"partner_stmt_from"' in src
    assert '"partner_stmt_to"' in src
    period = _block_after(src, "partner_stmt_preset", "partner_stmt_all_hide_inactive")
    assert "date_input" not in period


def test_vendor_statement_range_migrated():
    src = inspect.getsource(erp.render_vendors)
    block = _block_after(src, "vendor.stmt_expander", "gen_ven_stmt_btn")
    assert "_render_preferred_date_range_cols" in block
    assert '"stmt_ven_start"' in block
    assert "date_input" not in block


def test_customer_statement_range_migrated():
    src = inspect.getsource(erp.render_customers)
    block = _block_after(src, "customer.stmt_expander", "gen_cust_stmt_btn")
    assert "_render_preferred_date_range_cols" in block
    assert '"stmt_cust_start"' in block
    assert "date_input" not in block


def test_recon_history_filter_migrated():
    src = inspect.getsource(erp.render_cash_reconciliation)
    block = _block_after(src, "history_status_filter", "DailyCashReconciliation.date >=")
    assert "_render_preferred_date_range_cols" in block
    assert '"history_from"' in block
    assert "date_input" not in block


def test_recon_reports_tab_range_migrated():
    src = inspect.getsource(erp.render_cash_reconciliation)
    block = _block_after(src, "recon.tab.reports_desc", "status == \"reconciled\"")
    assert "_render_preferred_date_range_cols" in block
    assert '"report_from"' in block
    assert "date_input" not in block


def test_eod_history_range_migrated():
    src = inspect.getsource(erp.render_end_of_day_close)
    block = _block_after(src, "eod.history_header", "EndOfDayClose.date >=")
    assert "_render_preferred_date_range_cols" in block
    assert '"eod_hist_from"' in block
    assert "date_input" not in block


def test_render_preferred_date_range_cols_returns_dates(monkeypatch):
    captured: list[tuple[str, dict]] = []

    def _fake_text_input(label, **kwargs):
        captured.append((label, kwargs))

    state = {
        "_user_date_format": "DD.MM.YYYY",
        "mask02_from": "01.06.2026",
        "mask02_to": "15.06.2026",
    }

    class _Cols:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    col_a, col_b = _Cols(), _Cols()
    monkeypatch.setattr(erp.st, "text_input", _fake_text_input)
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp.date_ui.st, "text_input", _fake_text_input)
    monkeypatch.setattr(erp.date_ui.st, "session_state", state)

    d_from, d_to = erp._render_preferred_date_range_cols(
        col_a,
        col_b,
        "mask02_from",
        "mask02_to",
        datetime.date(2026, 6, 1),
        datetime.date(2026, 6, 30),
    )
    assert d_from == datetime.date(2026, 6, 1)
    assert d_to == datetime.date(2026, 6, 15)
    assert len(captured) == 2
    assert "on_change" in captured[0][1]


def test_partner_preset_syncs_text_keys(monkeypatch):
    state = {
        "_user_date_format": "DD.MM.YYYY",
        "partner_stmt_preset": "month",
    }
    monkeypatch.setattr(erp.st, "session_state", state)
    monkeypatch.setattr(erp.date_ui.st, "session_state", state)
    monkeypatch.setattr(erp.st, "text_input", lambda *a, **k: None)
    monkeypatch.setattr(erp.date_ui.st, "text_input", lambda *a, **k: None)

    today = datetime.date(2026, 6, 15)
    preset_from, preset_to = erp.partner_statement_preset_range("month", today)
    _pref = erp._active_user_date_format()
    state["partner_stmt_from"] = erp.format_date_for_preference(preset_from, _pref)
    state["partner_stmt_to"] = erp.format_date_for_preference(preset_to, _pref)

    assert state["partner_stmt_from"] == "01.06.2026"
    assert state["partner_stmt_to"] == "15.06.2026"
