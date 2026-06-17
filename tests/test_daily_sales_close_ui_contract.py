"""DSC-P2 UI contract — External Sales Verification renderer."""

from __future__ import annotations

import inspect
import pathlib

import pytest

import app as erp

ROOT = pathlib.Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "ui" / "external_sales_verification.py"
APP_PATH = ROOT / "app.py"

SERVICE_CALLS = (
    "compute_erp_sales_totals",
    "compute_variance",
    "get_active_verification",
    "list_verifications",
    "save_draft",
    "verify_external_sales",
    "void_verification",
    "is_verification_stale",
)

FORBIDDEN_UI_TOKENS = (
    "create_journal_entry",
    "post_cash_sale",
    "post_card_sale",
    "post_credit_sale",
    "submit_reconciliation",
    "from models import Sale",
    "import Sale",
    "session.query(Sale",
    "func.sum(Sale",
    "Sale.amount",
    "cq(session, Sale",
)


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.fixture()
def ui_src() -> str:
    return _read(UI_PATH)


@pytest.fixture()
def app_src() -> str:
    return _read(APP_PATH)


def test_renderer_module_exists():
    assert UI_PATH.is_file()
    from ui.external_sales_verification import render_external_sales_verification

    assert callable(render_external_sales_verification)


def test_renderer_calls_service_not_sale_queries(ui_src: str):
    assert "services import daily_sales_close" in ui_src or "services.daily_sales_close" in ui_src
    for fn in SERVICE_CALLS:
        assert fn in ui_src, f"Expected service call {fn!r} in UI renderer"
    for token in FORBIDDEN_UI_TOKENS:
        assert token not in ui_src, f"Forbidden token {token!r} in UI renderer"


def test_source_name_is_text_input_not_vendor_dropdown(ui_src: str):
    assert 'st.text_input' in ui_src
    assert "esv_source_name" in ui_src
    assert "st.selectbox" in ui_src
    assert "source_name" in ui_src
    # Generic source_type only — no vendor-named option lists
    lower = ui_src.lower()
    for vendor in ("wolvox", "suitable", "square", "ikentoo"):
        assert vendor not in lower


def test_app_dispatches_to_ui_renderer(app_src: str):
    from registry.nav_keys import NAV_EXTERNAL_SALES_VERIFICATION
    from registry.navigation import dispatch_render_spec

    assert dispatch_render_spec()[NAV_EXTERNAL_SALES_VERIFICATION] == (
        "render_external_sales_verification"
    )
    assert "render_external_sales_verification" in app_src
    assert "NAV_EXTERNAL_SALES_VERIFICATION" in app_src


def test_app_has_no_esv_business_logic(app_src: str):
    """app.py may dispatch only — no ESV Sale sums or verification math."""
    start = app_src.find("def render_cash_reconciliation")
    end = app_src.find("def render_end_of_day_close")
    between = app_src[start:end] if start != -1 and end != -1 else ""
    for token in ("compute_variance", "save_draft", "verify_external_sales", "ExternalSalesTotals"):
        assert token not in between


def test_renderer_passes_explicit_company_id(ui_src: str):
    assert "current_company_required" in ui_src
    assert "company_id" in ui_src


def test_nav_wired_under_closings(app_src: str):
    from registry.nav_keys import NAV_EXTERNAL_SALES_VERIFICATION

    assert "NAV_EXTERNAL_SALES_VERIFICATION" in app_src
    closings_pages = [
        page for _icon, page in erp._NAV_ACCORDION_BY_KEY["close_day"][1]
    ]
    assert NAV_EXTERNAL_SALES_VERIFICATION in closings_pages


def test_permissions_registered():
    from services import user_access as ua

    for perm in (
        "view_external_sales_verification",
        "verify_external_sales",
        "void_external_sales_verification",
    ):
        assert perm in ua.PERMISSION_REGISTRY


def test_renderer_public_signature():
    from ui.external_sales_verification import render_external_sales_verification

    params = list(inspect.signature(render_external_sales_verification).parameters)
    assert params == ["session"]
