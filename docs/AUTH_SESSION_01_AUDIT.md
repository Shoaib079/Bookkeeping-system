# AUTH-SESSION-01 — Login / Session Persistence Audit

**Mode:** Audit + **IMPL-1 implemented (2026-06).** Operator guide added; contract tests extended. No auth behavior change.

## Headline

**A session-restore mechanism already exists** — an HMAC-signed cookie token with a sliding TTL, password-change invalidation, and DB re-validation. It is **disabled by default** because it is gated on the `ERP_SESSION_RESTORE_SECRET` environment variable being set. **That unset secret is the root cause of losing login on refresh in production.**

## 1. Current auth / session map

| Concern | Implementation | Evidence |
|---|---|---|
| Login | `_login(session, username, password)` → PBKDF2 verify (`services.auth.verify_password`), set `last_login`, `_establish_auth_session` | `app.py:4846-4857` |
| Password hashing | PBKDF2-SHA256 salted (`services/auth.py`) | `app.py:2906-2917` |
| Session establish | `_establish_auth_session` stores `auth_user` dict + `auth_expires` (now + 8h) in `st.session_state`, resolves company memberships, theme/landing/locale | `app.py:4789-4828` |
| Live session store | `st.session_state["auth_user"]` + `["auth_expires"]` (per Streamlit websocket session) | `app.py:4789-4799` |
| Current-user read | `_current_user()` — None if logged-out flag or past `auth_expires` (8h **idle TTL**); pops keys on expiry | `app.py:2963-2974` |
| **Persistence (restore)** | **HMAC-signed cookie** `erp_session_restore`: `_mint_restore_token` (user_id.iat.exp.ph_frag[.company_id].sig), `_render_session_restore_cookie` (JS-set, **not HttpOnly**, SameSite=Lax, Secure on https), `_try_restore_session_from_cookie` | `app.py:2787-2807, 2841-2903` |
| Restore trigger | `_early_restore_auth_session()` runs **before** theme bootstrap; on success `main()` reruns | `app.py:26300-26308, 26374` |
| Sliding expiry | while authenticated, `main()` re-mints + re-writes the cookie each run | `app.py:26400-26404` |
| Restore validation | signature check, expiry check, user active, **`password_hash_fragment` match** (invalidates on password change), DB membership re-validation | `app.py:2876-2903, 4804-4811` |
| Logout | `_logout()` sets `_SESSION_LOGGED_OUT`, clears auth/company keys, **clears the cookie** | `app.py:4860-4871` |
| Dev bypass | `DEV_MODE` (`ERP_DEV_MODE=1`) → `_dev_auto_login` auto-establishes admin; cookie restore **skipped** | `app.py:419, 4831-4843, 2843, 2878` |
| Secret gate | `ERP_SESSION_RESTORE_SECRET`; if unset, mint/restore are **no-ops** | `app.py:2766-2777` |
| TTLs | `_SESSION_TTL_HOURS=8` (idle), `_RESTORE_TOKEN_TTL_HOURS=8` (cookie) | `app.py:2763, 2768` |

## 2. Existing tests found

- **`tests/test_ux01_session_restore.py`** — the restore-cookie mechanism (UX-01) — directly relevant.
- **`tests/test_dev_auth.py`** — dev auto-login bypass.
- **`tests/test_login01_auth_ui.py`** — login UI.
- **`tests/test_phase14b_auth.py`** — auth + company context.
- **`tests/test_user_access01_models.py` / `_permissions.py` / `_ui_contract.py`** — user access & permissions.
- **FastAPI (future API):** `tests/test_fastapi_p1_auth_login.py`, `test_fastapi_p1_auth_tokens.py`, `test_fastapi_p1_auth_jwt_runtime.py`, `test_fastapi_p1_auth_me_companies.py` — a JWT access + refresh stack already has tests (`services/tokens.py`, `services/auth.py`).

So both the **Streamlit restore-cookie** path and a **FastAPI JWT** path already exist and are tested.

## 3. Root cause of refresh login behavior

Streamlit `st.session_state` is bound to a single browser-tab websocket session; a **hard refresh / new tab starts a fresh session**, so `auth_user` is gone and `_current_user()` returns None → login screen. The intended bridge across that gap is the **restore cookie** — but it is **gated**:

- `_render_session_restore_cookie` and `_try_restore_session_from_cookie` **early-return when `ERP_SESSION_RESTORE_SECRET` is unset** (`app.py:2843, 2878`) **or in `DEV_MODE`**.
- **Default deployments do not set the secret**, so **no cookie is written and none is read** → every refresh loses login.
- **DEV_MODE masks the problem** — `_dev_auto_login` re-establishes the session on each run, so developers never see the refresh logout.

**Conclusion:** the feature is built and correct; it is simply **opt-in via an env secret that is unset by default**. Setting `ERP_SESSION_RESTORE_SECRET` (in a non-dev deployment) enables persistent login on refresh. Secondary expiry causes: the 8h idle/token TTL and password-change (`ph_frag`) invalidation.

## 4. Recommended design

- **Immediate (config, not code):** set `ERP_SESSION_RESTORE_SECRET` to a strong, stable secret in production to **enable the existing restore** — this alone fixes "refresh logs me out." See **`docs/AUTH_SESSION_01_OPERATOR.md`**.
- **Answers to the questions:**
  - *Does the app lose login on refresh?* **By default yes** (secret unset); **no** once the secret is set (and not DEV_MODE).
  - *Is there already a token/cookie mechanism?* **Yes** — signed restore cookie (Streamlit) **and** a JWT access+refresh stack (FastAPI, `services/tokens.py`).
  - *Sessions tied only to `st.session_state`?* The **live** session, yes; **persistence** is via the restore cookie when enabled — so not *only* session_state, but the bridge is opt-in.
  - *Safest practical "stay logged in"?* Enable the existing secret now; **harden later** by moving cookie-setting **server-side and HttpOnly** (removes the XSS read risk) — natural at the FastAPI migration — and split **idle vs absolute** TTL.
  - *Idle timeout?* **Already exists** (8h `auth_expires` idle + 8h token TTL). Keep; optionally separate idle (short) from absolute (longer).
  - *Explicit logout?* **Already exists** (`_logout` clears cookie + sets logged-out flag + blocks restore).
  - *Remember-this-device?* Not a distinct opt-in today (restore is always-on when the secret is set). Could add a per-login "remember me" toggle controlling whether the cookie is written and its TTL.
- **Future-compatible:** converge the Streamlit restore token onto the **FastAPI JWT model** — short-lived access token + **HttpOnly, server-set, revocable refresh token**; the current `ph_frag`/`exp` pattern maps cleanly to refresh-token rotation/revocation.

## 5. Security boundaries

- **Non-HttpOnly cookie (XSS exposure):** the restore cookie is **JS-set, readable by JS** (documented UX-01 tradeoff) — an XSS bug could exfiltrate the token and hijack a session. Mitigations in place: HMAC signature, `ph_frag` binding (password change invalidates), expiry, `SameSite=Lax`, `Secure` on https. **Residual risk remains**; the durable fix is a server-set **HttpOnly** cookie (FastAPI).
- **Secret management:** `ERP_SESSION_RESTORE_SECRET` must be strong, stable, and protected; if it leaks, tokens can be **forged** → treat as a secret, support rotation. Unset → feature silently off (fail-safe but surprising; document it).
- **No password in token** (only `ph_frag`) — good. **DB re-validation** on restore (user active + live membership) prevents stale-grant access. **Logout** revokes locally by clearing the cookie (note: a leaked token remains valid until expiry — true revocation needs the FastAPI refresh-revocation model).
- **No role/permission data in the token** beyond identity + company; permissions are DB-resolved per request — correct.

## 6. Contract tests (audit-recommended; for a later slice)

- **Token round-trip:** `_mint_restore_token` → `_verify_restore_token` returns the claims; **tampered signature rejected**; **expired token rejected**; **`ph_frag` mismatch rejected** (extend `test_ux01_session_restore.py`).
- **Secret gate (documents the root cause):** with `ERP_SESSION_RESTORE_SECRET` unset, mint returns None and no cookie is written; restore is a no-op.
- **DEV_MODE gate:** restore is skipped in DEV_MODE.
- **Logout:** clears the cookie, sets `_SESSION_LOGGED_OUT`, and blocks a subsequent restore.
- **Idle expiry:** `_current_user()` returns None once past `auth_expires`.
- **No regression:** these are read-only assertions over existing functions — no behavior change.

## 7. Implementation slices (for Cursor — DO NOT implement here)

- **AUTH-SESSION-01-IMPL-1 — enable + document (config):** **Implemented (2026-06)** — `docs/AUTH_SESSION_01_OPERATOR.md` + `tests/test_auth_session_01_impl_contract.py`; set `ERP_SESSION_RESTORE_SECRET` in deployment. No code change.
- **AUTH-SESSION-01-IMPL-2 — test hardening:** extend the restore tests with the §6 cases (secret-unset no-op, tamper/expiry/ph_frag rejection, logout-blocks-restore).
- **AUTH-SESSION-01-IMPL-3 — optional "remember this device":** per-login toggle controlling cookie write + TTL (idle vs absolute split). **Planned:** [AUTH-SESSION-02](./AUTH_SESSION_02_AUDIT.md).
- **AUTH-SESSION-01-IMPL-4 — HttpOnly hardening (FastAPI migration):** move cookie-setting server-side and HttpOnly; unify with the JWT access+refresh model (`services/tokens.py`) for the React front end. **Planned:** [AUTH-SESSION-02](./AUTH_SESSION_02_AUDIT.md).

## 8. Risk assessment

**Audit: LOW.** Nothing changes here. The immediate fix is **configuration** (set the secret), not code — low risk and reversible (unset to disable). The real security consideration is the **non-HttpOnly cookie**, an accepted Streamlit-era tradeoff to be retired at the FastAPI migration; until then the signature + `ph_frag` + expiry + DB re-validation bound the exposure. No accounting, schema, role, or password-hashing change is proposed.

## No-change statement (AUTH-SESSION-01 audit)

- **Audit + IMPL-1 — operator documentation and contract tests only; no auth behavior change, no password weakening, no role/permission change.**

---

*Audit only. A signed-cookie session-restore mechanism already exists (`_mint_restore_token` / `_render_session_restore_cookie` / `_try_restore_session_from_cookie`, HMAC-signed, sliding 8h TTL, ph_frag password-change invalidation, DB membership re-validation), plus a separate FastAPI JWT access+refresh stack. **Root cause of refresh-logout: the restore cookie is gated on `ERP_SESSION_RESTORE_SECRET`, which is unset by default, so no cookie is written/read; DEV_MODE masks it via auto-login.** Live session lives in `st.session_state`; persistence is the opt-in cookie. Explicit logout and an 8h idle TTL already exist. Recommended: set the secret now (config fix), harden later to a server-set HttpOnly cookie unified with the JWT refresh model; optional remember-this-device toggle. Security boundary: the cookie is non-HttpOnly (XSS read risk), bounded by signature + ph_frag + expiry + DB re-validation. Risk LOW — audit only; immediate fix is configuration, not code.*
