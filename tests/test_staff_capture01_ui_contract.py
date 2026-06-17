"""SC-P1b UI contract — Staff expense capture renderer."""

from __future__ import annotations

import inspect
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "ui" / "staff_capture.py"
APP_PATH = ROOT / "app.py"

SERVICE_CALLS = (
    "create_expense_draft",
    "update_expense_draft",
    "submit_expense_draft",
    "return_expense_draft",
    "reject_expense_draft",
    "approve_expense_draft",
    "get_expense_draft",
    "list_expense_drafts",
    "list_submitted_expense_drafts",
    "add_draft_attachment",
    "list_draft_attachments",
    "ExpenseDraftInput",
    "EXPENSE_DRAFT_TYPE",
)

ADAPTER_CALLS = (
    "is_receipt_capture_enabled",
    "create_receipt_capture_draft",
)

FORBIDDEN_UI_TOKENS = (
    "ExpenseDraft(",
    "DraftAttachment(",
    "session.add(",
    "session.delete(",
    "create_journal_entry",
    "post_expense(",
    "_save_and_post_expense_record",
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
    from ui.staff_capture import render_staff_expense_capture

    assert callable(render_staff_expense_capture)


def test_renderer_calls_service_only(ui_src: str):
    assert "services import staff_capture" in ui_src or "services.staff_capture" in ui_src
    assert "receipt_ai_adapter" in ui_src
    for fn in SERVICE_CALLS:
        assert fn in ui_src, f"Expected service call {fn!r} in UI renderer"
    for fn in ADAPTER_CALLS:
        assert fn in ui_src, f"Expected adapter call {fn!r} in UI renderer"
    for token in FORBIDDEN_UI_TOKENS:
        assert token not in ui_src, f"Forbidden token {token!r} in UI renderer"


def test_approval_uses_injected_post_fn(ui_src: str):
    assert "approve_expense_draft" in ui_src
    assert "post_fn=" in ui_src
    assert "_staff_capture_post_expense_draft" in ui_src


def test_permission_gates(ui_src: str):
    assert '_can("submit_expense_drafts")' in ui_src
    assert '_can("approve_expense_drafts")' in ui_src
    assert '_can("upload_receipts")' in ui_src
    assert "sc.no_permission" in ui_src


def test_app_dispatches_to_ui_renderer(app_src: str):
    from registry.nav_keys import NAV_STAFF_EXPENSE_CAPTURE
    from registry.navigation import dispatch_render_spec

    assert dispatch_render_spec()[NAV_STAFF_EXPENSE_CAPTURE] == "render_staff_expense_capture"
    assert "render_staff_expense_capture" in app_src
    assert "NAV_STAFF_EXPENSE_CAPTURE" in app_src


def test_nav_wired_under_transactions(app_src: str):
    idx = app_src.find('"transactions", "Record transactions"')
    assert idx != -1
    snippet = app_src[idx : idx + 500]
    assert "NAV_STAFF_EXPENSE_CAPTURE" in snippet


def test_app_posting_seam_exists(app_src: str):
    assert "def _staff_capture_post_expense_draft" in app_src
    assert "ExpensePostResult" in app_src


def test_renderer_public_signature():
    from ui.staff_capture import render_staff_expense_capture

    params = list(inspect.signature(render_staff_expense_capture).parameters)
    assert params == ["session"]


def test_renderer_passes_explicit_company_id(ui_src: str):
    assert "current_company_required" in ui_src
    assert "company_id" in ui_src


def test_inbox_and_submissions_tabs(ui_src: str):
    assert "sc.tab.my_submissions" in ui_src
    assert "sc.tab.inbox" in ui_src
    assert "list_expense_drafts" in ui_src
    assert "list_submitted_expense_drafts" in ui_src


def test_return_reject_approve_actions(ui_src: str):
    assert "return_expense_draft" in ui_src
    assert "reject_expense_draft" in ui_src
    assert "sc.action.approve" in ui_src
