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


def test_ui2a_void_danger_keys():
    sales = _fn_block("render_sales")
    expenses = _fn_block("render_expenses")
    purchases = _fn_block("render_purchases")
    assert 'key=f"erp_void_sale_' in sales
    assert 'key=f"erp_danger_confirm_void_sale_' in sales
    assert 'key=f"erp_void_expense_' in expenses
    assert 'key=f"erp_danger_confirm_void_exp_' in expenses
    assert 'key=f"erp_void_purchase_' in purchases
    assert 'key=f"erp_danger_confirm_void_pur_' in purchases


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
