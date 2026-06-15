"""AUTH-SESSION-02 — contract test for the session-hardening audit.

Doc-only guard: verifies the audit exists, carries required outputs, answers the
six design questions, documents security gaps and FastAPI path, and pins the
no-change statement. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "AUTH_SESSION_02_AUDIT.md"

REQUIRED_SECTIONS = (
    "Current auth map",
    "Existing tests map",
    "Security gap analysis",
    "Recommended AUTH-SESSION-02 design",
    "FastAPI migration design",
    "Answers to design questions",
    "Contract tests",
    "Implementation slices",
    "Risk assessment",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"AUTH-SESSION-02 audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing section: {section!r}"


def test_builds_on_auth_session_01(doc_text):
    lowered = doc_text.lower()
    assert "auth-session-01" in lowered
    assert "erp_session_restore_secret" in lowered


def test_current_flows_documented(doc_text):
    lowered = doc_text.lower()
    for sym in (
        "_mint_restore_token",
        "_try_restore_session_from_cookie",
        "_establish_auth_session",
        "_logout",
        "_current_user",
        "auth_expires",
    ):
        assert sym in lowered, f"Must document: {sym}"
    assert "dev_mode" in lowered or "erp_dev_mode" in lowered


def test_security_gaps(doc_text):
    lowered = doc_text.lower()
    for gap in (
        "httponly",
        "remember",
        "revocation",
        "multi-device",
        "xss",
    ):
        assert gap in lowered, f"Security gap analysis must cover: {gap}"


def test_fastapi_jwt_documented(doc_text):
    lowered = doc_text.lower()
    assert "services/tokens.py" in lowered or "tokens.py" in lowered
    assert "refresh" in lowered
    assert "fastapi" in lowered


def test_design_questions_answered(doc_text):
    lowered = doc_text.lower()
    assert "remember this device" in lowered or "remember device" in lowered
    assert "idle" in lowered and "absolute" in lowered
    assert "logout" in lowered and ("current device" in lowered or "all devices" in lowered)
    assert "session table" in lowered or "user_sessions" in lowered
    assert "streamlit now" in lowered or "streamlit" in lowered


def test_auth_expires_sliding_gap_noted(doc_text):
    lowered = doc_text.lower()
    assert "auth_expires" in lowered
    assert "sliding" in lowered or "not extended" in lowered or "absolute" in lowered


def test_implementation_slices_marked_future(doc_text):
    lowered = doc_text.lower()
    assert "auth-session-02-impl" in lowered
    assert "do not implement" in lowered


def test_contract_tests_listed(doc_text):
    lowered = doc_text.lower()
    assert "remember" in lowered
    assert "idle" in lowered
    assert "ph_frag" in lowered or "password change" in lowered


def test_no_change_statement(doc_text):
    lowered = doc_text.lower()
    assert "audit only" in lowered
    assert "no auth behavior change" in lowered
    assert "no schema change" in lowered
