"""DATE-MASK global contract — audit date input call sites."""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import app as erp

ROOT = Path(__file__).resolve().parents[1]

# Migrated to preferred masked text inputs (Phase A/B).
MIGRATED_MARKERS = (
    "_at_render_desktop_date_field",
    "_mob_at_render_date_picker_sheet",
    "_render_date_range_filters",
    "_render_txh_date_filters",
    "_render_preferred_date_range_cols",
    "_render_partner_statement",
    "render_vendors",
    "render_customers",
    "render_cash_reconciliation",
    "render_end_of_day_close",
    "render_unsettled_card_sales_list_block",
)

# Native st.date_input retained — calendar UX or high-risk forms (Phase B deferred).
NATIVE_DATE_INPUT_ALLOWED = {
    "render_sidebar_filters": "delegates to _render_date_range_filters (migrated)",
    "render_sales": "sale entry form",
    "render_expenses": "expense entry",
    "render_purchases": "purchase entry",
    "render_payables": "payable entry",
    "render_journal_entries": "JE entry",
    "render_opening_balances": "multi OB forms",
    "render_fiscal_periods": "fiscal period create",
    "render_partner_accounts": "partner movement",
    "render_workers": "worker movement",
    "render_equity": "equity movement",
    "render_recurring_expenses": "template editor",
    "_txh_render_edit_row": "inline TXH edit",
}


def _find_date_input_sites(src: str, filepath: str) -> list[tuple[int, str]]:
    sites = []
    for i, line in enumerate(src.splitlines(), 1):
        if ".date_input(" in line or "st.date_input(" in line:
            sites.append((i, line.strip()))
    return sites


def test_shared_date_modules_exist():
    from registry import date_utils
    from ui import date_input

    assert hasattr(date_utils, "parse_date_text")
    assert hasattr(date_utils, "format_date_input_for_preference")
    assert hasattr(date_input, "render_preferred_date_input")
    assert hasattr(date_input, "get_user_date_format")


def test_migrated_sites_use_preferred_date_input():
    for fn_name in MIGRATED_MARKERS:
        if fn_name.startswith("render_") and hasattr(erp, fn_name):
            src = inspect.getsource(getattr(erp, fn_name))
        elif fn_name == "render_unsettled_card_sales_list_block":
            from ui import banking

            src = inspect.getsource(
                banking.render_unsettled_card_sales_list_block
            )
        else:
            src = inspect.getsource(getattr(erp, fn_name))
        assert (
            "render_preferred_date_input" in src
            or "date_ui.render_preferred_date_input" in src
            or "_render_preferred_date_range_cols" in src
        ), f"{fn_name} should use preferred date input"


def test_add_transaction_no_isoformat_in_date_display():
    for fn in (
        erp._at_render_desktop_date_field,
        erp._at_refresh_date_text_display,
        erp._mob_at_render_date_picker_sheet,
    ):
        src = inspect.getsource(fn)
        assert "isoformat()" not in src


def test_app_reexports_date_engine():
    assert erp.parse_date_text is not None
    assert erp.format_date_input_for_preference is not None
    assert erp.normalize_date_digits is not None


def test_date_input_audit_list():
    """Inventory native date_input sites — must shrink as migration proceeds."""
    app_src = (ROOT / "app.py").read_text(encoding="utf-8")
    banking_src = (ROOT / "ui" / "banking.py").read_text(encoding="utf-8")
    app_sites = _find_date_input_sites(app_src, "app.py")
    bank_sites = _find_date_input_sites(banking_src, "ui/banking.py")
    total = len(app_sites) + len(bank_sites)
    # DATE-MASK-02A: statement/filter ranges migrated; ~34 native remain in posting forms.
    assert total >= 25
    assert total <= 45


def test_global_date_format_cached_in_main():
    src = inspect.getsource(erp.main)
    assert "_cache_user_date_format" in src


def test_render_preferred_date_input_accepts_in_form_kwarg(monkeypatch):
    """Smoke test — in_form=True must not raise TypeError at call time."""
    from ui import date_input as date_ui

    monkeypatch.setattr(date_ui.st, "text_input", lambda *a, **k: None)
    monkeypatch.setattr(
        date_ui.st,
        "session_state",
        {"_user_date_format": "DD.MM.YYYY", "at_date_text": ""},
    )
    date_ui.render_preferred_date_input(
        "Date",
        "at_date_text",
        in_form=True,
        help="typed date",
        invalid_message="invalid",
    )


def test_render_preferred_date_input_in_form_omits_on_change(monkeypatch):
    from ui import date_input as date_ui

    captured: list[dict] = []

    def _fake_text_input(label, **kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(date_ui.st, "text_input", _fake_text_input)
    monkeypatch.setattr(
        date_ui.st,
        "session_state",
        {"_user_date_format": "DD.MM.YYYY", "form_date_key": ""},
    )
    date_ui.render_preferred_date_input("Date", "form_date_key", in_form=True)
    assert captured
    assert "on_change" not in captured[0]


def test_render_preferred_date_input_outside_form_uses_on_change(monkeypatch):
    from ui import date_input as date_ui

    captured: list[dict] = []

    def _fake_text_input(label, **kwargs):
        captured.append(kwargs)

    monkeypatch.setattr(date_ui.st, "text_input", _fake_text_input)
    monkeypatch.setattr(
        date_ui.st,
        "session_state",
        {"_user_date_format": "DD.MM.YYYY", "filter_date_key": ""},
    )
    date_ui.render_preferred_date_input("Date", "filter_date_key", in_form=False)
    assert captured
    assert "on_change" in captured[0]
    assert callable(captured[0]["on_change"])


def test_add_transaction_date_field_is_form_safe():
    src = inspect.getsource(erp._at_render_desktop_date_field)
    assert "in_form=True" in src
    assert "_at_apply_deferred_date_text_sync" in src
    resolve_src = inspect.getsource(erp._at_resolve_entry_date)
    assert "_at_defer_date_text_display" in resolve_src
    assert 'st.session_state["at_date_text"]' not in resolve_src


def test_cash_recon_form_date_field_is_form_safe():
    src = inspect.getsource(erp.render_cash_reconciliation)
    form_pos = src.index('st.form(key="reconciliation_form")')
    recon_date_pos = src.index("recon_date", form_pos)
    recon_block = src[recon_date_pos : recon_date_pos + 400]
    assert "in_form=True" in recon_block
