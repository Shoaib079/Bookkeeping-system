"""AUTH-SESSION-01 — contract test for the login/session persistence audit.

Doc-only guard: verifies the audit exists, carries the required outputs (auth/session
map, existing tests, root cause, recommended design, security boundaries, contract
tests, slices, risk), and pins the findings (restore mechanism exists, secret-gated
root cause, non-HttpOnly risk, logout/idle exist, no-change). Pure stdlib; no app
imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "AUTH_SESSION_01_AUDIT.md"

REQUIRED_SECTIONS = (
    "Current auth / session map",
    "Existing tests found",
    "Root cause of refresh login behavior",
    "Recommended design",
    "Security boundaries",
    "Contract tests",
    "Implementation slices",
    "Risk assessment",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Auth audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Auth audit doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Auth audit doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_restore_mechanism_documented(doc_text):
    lowered = doc_text.lower()
    for sym in ("_mint_restore_token", "_try_restore_session_from_cookie", "erp_session_restore"):
        assert sym in lowered, f"Audit must document the restore symbol: {sym}"
    assert "hmac" in lowered, "Audit must note the HMAC-signed token"
    assert "password_hash_fragment" in lowered or "ph_frag" in lowered, (
        "Audit must note password-change invalidation"
    )


def test_root_cause_secret_gated(doc_text):
    lowered = doc_text.lower()
    assert "erp_session_restore_secret" in lowered, "Root cause must name the secret env var"
    assert "unset" in lowered, "Root cause must state the secret is unset by default"
    assert "session_state" in lowered, "Root cause must explain st.session_state refresh loss"
    assert "dev_mode" in lowered and "mask" in lowered, "Root cause must note DEV_MODE masking"


def test_existing_tests_listed(doc_text):
    lowered = doc_text.lower()
    assert "test_ux01_session_restore" in lowered, "Must cite the restore test"
    assert "test_fastapi_p1_auth" in lowered, "Must cite the FastAPI JWT auth tests"


def test_logout_and_idle_exist(doc_text):
    lowered = doc_text.lower()
    assert "_logout" in lowered, "Audit must note explicit logout exists"
    assert "idle" in lowered and "8h" in lowered, "Audit must note the 8h idle TTL"


def test_security_non_httponly(doc_text):
    lowered = doc_text.lower()
    assert "httponly" in lowered, "Security must discuss HttpOnly"
    assert "xss" in lowered, "Security must note the XSS read risk"


def test_future_fastapi_jwt(doc_text):
    lowered = doc_text.lower()
    assert "jwt" in lowered, "Recommended design must reference the JWT model"
    assert "services/tokens.py" in lowered or "tokens.py" in lowered, (
        "Must reference the FastAPI token service"
    )
    assert "refresh" in lowered, "Must reference a refresh-token model"


def test_immediate_fix_is_config(doc_text):
    lowered = doc_text.lower()
    assert "config" in lowered and "not code" in lowered, (
        "Audit must state the immediate fix is configuration"
    )


def test_risk_low(doc_text):
    lowered = doc_text.lower()
    assert "risk assessment" in lowered and "low" in lowered, "Audit must state LOW risk"


def test_no_change_statement(doc_text):
    lowered = doc_text.lower()
    assert "audit only" in lowered, "Audit must state audit-only"
    assert "no auth behavior change" in lowered, "Audit must state no auth behavior change"
    assert "no password weakening" in lowered, "Audit must state no password weakening"
    assert "no role/permission change" in lowered or "no role/permission change" in lowered, (
        "Audit must state no role/permission change"
    )
