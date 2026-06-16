"""Phase UI-2A — Sales / Expenses / Purchases visual polish contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read_app() -> str:
    return (ROOT / "app.py").read_text(encoding="utf-8")


def _fn_block(name: str) -> str:
    src = _read_app()
    start = src.index(f"def {name}(session):")
    nxt = src.find("\ndef ", start + 1)
    return src[start:nxt] if nxt != -1 else src[start:]


def test_ui2a_section_headers_and_bordered_forms():
    for fn in ("render_sales", "render_expenses", "render_purchases"):
        block = _fn_block(fn)
        assert "section_header_html" in block
        assert "st.container(border=True)" in block


def _read_crud_helpers() -> str:
    return (ROOT / "ui" / "crud_helpers.py").read_text(encoding="utf-8")


def test_ui2a_void_danger_keys():
    """Verify void key prefixes route through void_confirmation_widget.

    After the shared-utility refactor, inline ``key=f"erp_void_..."``
    patterns moved into ``ui.crud_helpers.void_confirmation_widget``.
    The contract checks that (a) each render function delegates to the
    widget with the correct prefix, and (b) the widget itself generates
    the expected ``erp_void_`` / ``erp_danger_confirm_void_`` keys.
    """
    sales = _fn_block("render_sales")
    expenses = _fn_block("render_expenses")
    purchases = _fn_block("render_purchases")

    # Each page delegates to the shared widget with the correct prefix
    assert 'void_confirmation_widget(' in sales
    assert 'prefix="sale"' in sales
    assert 'void_confirmation_widget(' in expenses
    assert 'prefix="expense"' in expenses
    assert 'void_confirmation_widget(' in purchases
    assert 'prefix="purchase"' in purchases

    # The shared widget generates the canonical key patterns
    helper_src = _read_crud_helpers()
    assert 'f"erp_void_{prefix}_{record_id}"' in helper_src
    assert 'f"erp_danger_confirm_void_{prefix}_{record_id}"' in helper_src


def test_ui2a_currency_not_dollar_literal_in_void_rows():
    for fn in ("render_sales", "render_expenses", "render_purchases"):
        block = _fn_block(fn)
        assert 'load_settings().get("currency"' in block
        assert 'f"${' not in block


def test_ui2a_expense_attachment_i18n():
    block = _fn_block("render_expenses")
    assert '_t("expense.select_record")' in block
    assert "Select expense record" not in block
    locales = (ROOT / "registry" / "locales" / "transactional.py").read_text(encoding="utf-8")
    assert '"expense.select_record"' in locales
    assert '"expense.new"' in locales


def test_ui2a_attachment_muted_token():
    app = _read_app()
    assert "#9ca3af" not in app.split("render_attachment_section")[1].split("def ")[0]
