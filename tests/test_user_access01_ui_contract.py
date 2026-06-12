"""UA-P1b UI contract — Permission management renderer."""

from __future__ import annotations

import inspect
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "ui" / "permissions.py"
APP_PATH = ROOT / "app.py"

SERVICE_CALLS = (
    "list_active_members",
    "effective_permissions",
    "list_registry",
    "set_override",
    "clear_override",
    "reset_to_template",
    "list_permission_audit",
)

FORBIDDEN_UI_TOKENS = (
    "UserPermissionOverride",
    "session.add(",
    "session.delete(",
    "resolve_effective_permissions",
    "PERMISSION_TEMPLATES",
    "OWNER_LOCKED_KEYS",
    "LEGACY_PERMISSION_MATRIX",
    "_would_violate_owner_lockout",
    "create_journal_entry",
    "post_cash_sale",
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
    from ui.permissions import render_permissions_management

    assert callable(render_permissions_management)


def test_renderer_calls_service_only(ui_src: str):
    assert "services import user_access" in ui_src or "services.user_access" in ui_src
    for fn in SERVICE_CALLS:
        assert fn in ui_src, f"Expected service call {fn!r} in UI renderer"
    for token in FORBIDDEN_UI_TOKENS:
        assert token not in ui_src, f"Forbidden token {token!r} in UI renderer"


def test_no_permission_math_in_ui(ui_src: str):
    assert "resolve_effective_permissions" not in ui_src
    assert "PERMISSION_TEMPLATES" not in ui_src


def test_manage_permissions_gate(ui_src: str):
    assert '_can("manage_permissions")' in ui_src
    assert "ua.no_permission" in ui_src


def test_owner_lockout_error_displayed(ui_src: str):
    assert "result.error" in ui_src
    assert "st.error" in ui_src
    assert "manage_permissions" in _read(ROOT / "services" / "user_access.py")


def test_app_dispatches_to_ui_renderer(app_src: str):
    assert "render_permissions_management" in app_src
    assert "NAV_PERMISSIONS:" in app_src
    assert "render_permissions_management" in app_src.split("NAV_PERMISSIONS:")[1][:80]


def test_nav_wired_under_settings(app_src: str):
    idx = app_src.find('"settings", "Settings"')
    assert idx != -1
    snippet = app_src[idx : idx + 400]
    assert "NAV_PERMISSIONS" in snippet


def test_renderer_public_signature():
    from ui.permissions import render_permissions_management

    params = list(inspect.signature(render_permissions_management).parameters)
    assert params == ["session"]


def test_renderer_passes_explicit_company_id(ui_src: str):
    assert "current_company_required" in ui_src
    assert "company_id" in ui_src


def test_clears_permission_cache_after_mutation(ui_src: str):
    assert "_clear_permission_cache" in ui_src


def test_provenance_display_uses_dto_fields(ui_src: str):
    assert "view.template_keys" in ui_src
    assert "view.grants" in ui_src
    assert "view.denies" in ui_src
    assert "view.effective_keys" in ui_src
    assert "ua.provenance.formula" in ui_src


def test_can_signature_unchanged():
    import app as erp

    params = list(inspect.signature(erp._can).parameters)
    assert params == ["action"]
