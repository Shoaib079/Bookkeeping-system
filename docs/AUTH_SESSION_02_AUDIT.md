# AUTH-SESSION-02 — Session Hardening Audit

**Mode:** Audit only. **No auth behavior change, no cookie/token change, no schema change, no UI implementation.**

**Context:** [AUTH-SESSION-01](./AUTH_SESSION_01_AUDIT.md) shipped the signed restore cookie, operator docs (`ERP_SESSION_RESTORE_SECRET`), and contract tests. This audit plans **session hardening** before implementation.

## Headline

Streamlit auth today is a **two-layer model**: ephemeral `st.session_state` plus an optional **HMAC restore cookie** (UX-01). It works for refresh persistence when the secret is set, but has **known gaps**: non-HttpOnly JS cookie, **no remember-device opt-in**, **no server-side revocation**, **no multi-device session registry**, and a **TTL mismatch** (restore cookie slides on activity; `auth_expires` does not). A parallel **FastAPI JWT access-token** stack exists (`services/tokens.py`, `POST /auth/login`) but **no refresh token or HttpOnly cookie yet**. AUTH-SESSION-02 should unify policy (idle vs absolute, remember-me) while keeping Streamlit and FastAPI on a shared substrate (`services/auth.py`, `ph_frag`, future `token_version`).

---

## 1. Current auth map

### 1.1 Restore cookie flow (UX-01 / AUTH-SESSION-01)

| Step | Behavior | Evidence |
|---|---|---|
| Secret gate | `ERP_SESSION_RESTORE_SECRET` unset → mint/restore/render are **no-ops** | `app.py` `_restore_secret_configured`, `_mint_restore_token`, `_render_session_restore_cookie`, `_try_restore_session_from_cookie` |
| Mint | `user_id.iat.exp.ph_frag[.company_id].sig` — HMAC-SHA256 | `app.py` `_mint_restore_token` |
| Write | `components.v1.html` injects JS: `document.cookie = erp_session_restore=…; max-age=28800; SameSite=Lax; Secure` on https | `app.py` `_render_session_restore_cookie` |
| Read | `st.context.cookies.get("erp_session_restore")` → `_verify_restore_token` | `app.py` `_try_restore_session_from_cookie` |
| Early restore | `_early_restore_auth_session()` before theme bootstrap; `st.rerun()` on success | `app.py` `main()` |
| Sliding cookie | Each authenticated `main()` run re-mints + re-writes cookie (`_mint_restore_token_for_user`) | `app.py` `main()` ~26464–26468 |
| Validation | Signature, `exp`, user `is_active`, `ph_frag` match, DB membership for `company_id` | `app.py` `_try_restore_session_from_cookie`, `_establish_auth_session` |
| DEV skip | `DEV_MODE` → no mint/read/render | `app.py` `DEV_MODE`, `_render_session_restore_cookie`, `_try_restore_session_from_cookie` |

### 1.2 Live session / `session_state` flow

| Step | Behavior | Evidence |
|---|---|---|
| Login | `_login` → PBKDF2 verify → `_establish_auth_session` | `app.py` `_login`, `services/auth.py` |
| Establish | Sets `auth_user` dict, `auth_expires = now + 8h`, company context, theme/locale prefs | `app.py` `_establish_auth_session` |
| Current user | `_current_user()` — None if `_SESSION_LOGGED_OUT` or `now >= auth_expires` | `app.py` `_current_user` |
| **TTL note** | `auth_expires` is set **once** at establish/restore — **not extended** on subsequent reruns | `app.py` grep: only `_establish_auth_session` writes `auth_expires` |
| Permissions | `_can` → DB-resolved via `user_access` (not in session token) | `app.py` `_can`, `services/user_access.py` |
| Company gate | `active_company_id` / `active_company_role`; membership re-validated each run | `app.py` `main()` Gate 2/3 |

### 1.3 Logout behavior

| Action | Effect |
|---|---|
| `_logout()` | Sets `_SESSION_LOGGED_OUT = True` |
| | Clears `auth_user`, `auth_expires`, company keys, permission cache |
| | `_render_session_restore_cookie(clear=True)` — JS deletes cookie |
| Early restore when logged out | Clears cookie again (belt-and-suspenders) | `app.py` `_early_restore_auth_session` |
| Leaked token | A copied restore token remains valid until **cookie `exp`** — no server revocation | Design gap |

### 1.4 Eight-hour expiry behavior

| Mechanism | TTL | Sliding? | Notes |
|---|---|---|---|
| `auth_expires` | 8h (`_SESSION_TTL_HOURS`) | **No** — fixed from login/restore time | Same-tab session ends at T+8h even if active |
| Restore cookie `max-age` | 8h (`_RESTORE_TOKEN_TTL_HOURS`) | **Yes** — re-minted every authenticated run | Refresh/new tab can restore until cookie expires |
| Password change | Immediate | N/A | `ph_frag` mismatch invalidates restore token |
| FastAPI access JWT | 30 min default (`DEFAULT_ACCESS_TTL_SECONDS`) | N/A | Separate stack; not used by Streamlit |

**Implication:** Documentation calls `auth_expires` an "idle TTL," but implementation is **absolute from establish**. AUTH-SESSION-02 should fix terminology and optionally add true idle extension on activity.

### 1.5 DEV_MODE behavior

| Setting | Effect |
|---|---|
| `ERP_DEV_MODE=1` | `DEV_MODE = True` |
| | `_dev_auto_login` establishes admin session without login UI |
| | Restore cookie **disabled** (mint/read/render skipped) |
| | Dev banner shown in `main()` |
| `ERP_DEV_USER` | Username for auto-login (default `admin`) |
| Production | Must use `ERP_DEV_MODE=0` + `ERP_SESSION_RESTORE_SECRET` set |

### 1.6 FastAPI JWT / token services

| Component | Status | Evidence |
|---|---|---|
| Password | Shared `services/auth.py` PBKDF2 + `password_hash_fragment` | `services/auth.py` |
| Access token | `issue_access_token` / `verify_access_token` — 30 min HS256, `sub`, `ph_frag`, `jti`, optional `token_version` | `services/tokens.py` |
| Refresh token | **Not implemented** | `FASTAPI_P1_3_AUTH_STRATEGY.md` plans it; no `issue_refresh_token` |
| Login API | `POST /auth/login` → bearer access only | `api/routes/auth.py` |
| Company context | `X-Company-Id` per request; not in JWT | `docs/FASTAPI_P1_3_AUTH_STRATEGY.md` |
| `token_version` on User | Used via `getattr` in token service; **not an ORM column yet** | `services/tokens.py`, `models.User` |
| Revocation | `token_version` bump + future `jti` denylist — **scaffold only** | `services/tokens.py` |

### 1.7 Streamlit vs FastAPI coexistence

- **Independent session stores** — Streamlit `session_state` + restore cookie; FastAPI Bearer JWT.
- **Shared verification** — PBKDF2, `ph_frag`, active-user check, membership services.
- **Convergence target** — Streamlit restore cookie → FastAPI **HttpOnly refresh cookie** + in-memory access token (React/desktop API clients).

---

## 2. Existing tests map

| Test file | Coverage |
|---|---|
| `tests/test_ux01_session_restore.py` | Mint/verify, tamper/expiry, `ph_frag`, restore flow, company revalidation, cookie render, logout blocks restore, secret gate |
| `tests/test_auth_session_01_impl_contract.py` | Operator doc contract, secret unset no-op, ph_frag, logout blocks restore, TTL constants |
| `tests/test_auth_session_01_audit.py` | AUTH-SESSION-01 audit doc structure |
| `tests/test_dev_auth.py` | DEV_MODE auto-login, restore skipped |
| `tests/test_login01_auth_ui.py` | Login UI |
| `tests/test_phase14b_auth.py` | Auth + company context |
| `tests/test_fastapi_p1_auth_login.py` | API login success/failure |
| `tests/test_fastapi_p1_auth_tokens.py` | JWT issue/verify, expiry, ph_frag, token_version |
| `tests/test_fastapi_p1_auth_jwt_runtime.py` | Bearer dependency wiring |
| `tests/test_fastapi_p1_auth_me_companies.py` | `/auth/me`, `/auth/companies` |

**Gaps (not tested today):** remember-me toggle, idle extension of `auth_expires`, absolute max session, logout-all-devices, server revocation, multi-device registry, HttpOnly cookie path.

---

## 3. Security gap analysis

| Gap | Severity | Current mitigation | AUTH-SESSION-02 target |
|---|---|---|---|
| **Non-HttpOnly restore cookie** | Medium | HMAC, `ph_frag`, `exp`, DB re-validation; XSS could exfiltrate token | HttpOnly server-set cookie (FastAPI) |
| **Streamlit JS cookie write** | Medium | SameSite=Lax, Secure on https; XSS reads cookie via `document.cookie` | Eliminate client-side write |
| **No remember-device opt-in** | Low | Always-on restore when secret set | Per-login checkbox; default session-only |
| **No server revocation** | Medium | Wait for `exp`; password change via `ph_frag` | `token_version` bump, session/`jti` table |
| **No multi-device visibility** | Low | None | Optional session list + per-device revoke |
| **Leaked token usable until expiry** | Medium | Short TTL (8h) | Shorter default session + refresh rotation |
| **`auth_expires` not sliding** | Low | Cookie can re-bridge after refresh | True idle timeout + activity extension |
| **Cookie vs session TTL mismatch** | Low | Cookie slides; session absolute | Explicit idle + absolute policy |
| **Secret rotation story** | Low | Manual secret swap invalidates all tokens | Document rotation; dual-key verify window |
| **DEV_MODE in production** | High if misconfigured | Operator doc warns | Startup diagnostic if DEV+production |
| **No refresh token (API)** | Medium | Short access TTL | P1.3c refresh + revoke endpoints |

---

## 4. Recommended AUTH-SESSION-02 design

### 4.1 Session policy model (target)

Introduce a **session policy** object (service-first, env + per-login overrides):

```text
SessionPolicy
  mode: "browser_session" | "remember_device"
  idle_timeout: timedelta      # extend on activity (session_state + cookie)
  absolute_timeout: timedelta   # hard cap from first login
  write_restore_cookie: bool
```

**Defaults (proposed):**

| Mode | Idle | Absolute | Restore cookie |
|---|---|---|---|
| **Browser session** (default) | 8h activity | 8h from login | Yes, sliding idle |
| **Remember device** (opt-in) | 8h activity | 30 days | Yes, longer absolute cap |

### 4.2 Streamlit changes (future slices)

1. **Login UI** — "Remember this device" checkbox (default **off**).
2. **`_establish_auth_session`** — accept policy; set `auth_expires` with idle extension hook.
3. **`main()` activity hook** — extend `auth_expires` on authenticated run (true idle).
4. **`_mint_restore_token`** — embed `mode` or use different TTL from policy; skip mint when remember=false after browser close (optional: session cookie without max-age — limited in Streamlit JS approach).
5. **Logout** — current device only (clear cookie + logged-out flag); "Log out everywhere" later via `token_version`.

### 4.3 Keep unchanged

- PBKDF2 parameters and `services/auth.py` API.
- DB permission resolution per request.
- Company context in `session_state` / `X-Company-Id` (not authoritative in token).
- Void/audit posting rules.

---

## 5. FastAPI migration design

Align with [FASTAPI_P1_3_AUTH_STRATEGY.md](./FASTAPI_P1_3_AUTH_STRATEGY.md):

| Concern | Streamlit (now) | FastAPI (target) |
|---|---|---|
| Persistence | HMAC restore cookie (JS) | **HttpOnly** refresh cookie |
| Per-request auth | `session_state` | Bearer access JWT (memory) |
| Remember device | Checkbox → longer cookie TTL | Refresh TTL + rotation |
| Logout (device) | Clear restore cookie | Revoke refresh `jti` |
| Logout (all) | Not available | Bump `users.token_version` |
| Idle timeout | Extend `auth_expires` on rerun | Short access TTL (30m) + refresh on activity |
| Absolute timeout | Policy on restore token `exp` | Refresh `exp` claim |

**Migration path:** implement refresh token + revoke in `services/tokens.py` first; Streamlit can later call the same service for cookie mint instead of `_mint_restore_token` when co-deployed behind FastAPI.

---

## 6. Answers to design questions

### Q1 — Should we add a "Remember this device" option?

**Yes — recommended, default off.**

- Default login = **browser session** (current 8h behavior, clearer user expectation).
- Opt-in = longer **absolute** persistence (e.g. 30 days) with same **idle** cap (8h).
- Without opt-in, do not write a long-lived restore cookie (or use session-scoped cookie semantics where possible).

### Q2 — Should short login and long login have different TTLs?

**Yes.**

- **Short (default):** 8h idle + 8h absolute (or session-only if cookie technology allows).
- **Long (remember):** 8h idle + 30d absolute (tunable via env).
- Same signing secret and `ph_frag` binding; differ only in `exp` / policy claims.

### Q3 — Should there be idle timeout vs absolute timeout?

**Yes — and fix the current mismatch.**

- Today: cookie slides; `auth_expires` is absolute from establish only.
- Target: **idle** extended on each authenticated interaction; **absolute** hard cap from first authentication regardless of activity.

### Q4 — Should logout revoke only current device or all devices?

**Phased:**

1. **AUTH-SESSION-02 v1:** **Current device only** — matches today (`_logout` clears cookie + session flag). Document that leaked tokens work until expiry.
2. **AUTH-SESSION-02 v2 / FastAPI:** **All devices** — `token_version` increment on `User` + invalidate all refresh tokens / restore tokens carrying old version.

Offer UI "Sign out everywhere" only when revocation backend exists.

### Q5 — Should there be a session table later?

**Yes, for FastAPI + multi-device — optional for Streamlit-only v1.**

Proposed `user_sessions` (additive, future):

- `id`, `user_id`, `jti` or `session_id`, `device_label`, `created_at`, `last_seen_at`, `expires_at`, `revoked_at`, `ip_hint`, `user_agent_hint`
- Enables: list active sessions, per-device revoke, audit trail.
- Streamlit restore token can carry `session_id` claim when table exists.

Not required for remember-me checkbox alone; **is** required for true revocation and "logout all."

### Q6 — What belongs in Streamlit now vs FastAPI later?

| Streamlit now (AUTH-SESSION-02) | FastAPI later |
|---|---|
| Remember-me checkbox + policy | Same policy via login request body |
| Idle extension of `auth_expires` | Access token short TTL |
| Policy-aware restore token TTL | HttpOnly refresh cookie |
| Logout current device | `POST /auth/logout` + revoke refresh |
| Operator docs for TTL env vars | OpenAPI auth docs |
| Contract tests on policy helpers | Integration tests on refresh rotation |
| — | `token_version` column + migration |
| — | Session table + admin UI |
| — | HttpOnly cookie (cannot fully fix in pure Streamlit) |

---

## 7. Contract tests (for implementation slices)

Pure tests over policy helpers and existing token functions — **no behavior change until slices land.**

1. **Policy defaults** — browser session vs remember_device TTL pairs.
2. **Idle extension** — activity bumps `auth_expires` but not past absolute cap.
3. **Remember off** — login without remember does not mint long-`exp` token.
4. **Remember on** — minted token `exp` reflects 30d absolute (configurable).
5. **Logout device** — clears cookie; logged-out flag blocks restore (extend existing).
6. **Logout all (future)** — `token_version` bump invalidates old restore/JWT tokens.
7. **ph_frag / password change** — still invalidates all modes.
8. **DEV_MODE** — still skips restore regardless of remember.
9. **Secret unset** — still no-op.
10. **FastAPI parity** — same `SessionPolicy` maps to access+refresh TTLs.

---

## 8. Implementation slices (DO NOT implement in this audit)

| Slice | Scope |
|---|---|
| **AUTH-SESSION-02-IMPL-1** | `SessionPolicy` service + env config (`ERP_SESSION_IDLE_HOURS`, `ERP_SESSION_ABSOLUTE_DAYS_REMEMBER`); docs only wiring |
| **AUTH-SESSION-02-IMPL-2** | Remember-me checkbox on login UI; policy passed to `_establish_auth_session` / `_mint_restore_token` |
| **AUTH-SESSION-02-IMPL-3** | True idle extension — refresh `auth_expires` on authenticated runs; align terminology |
| **AUTH-SESSION-02-IMPL-4** | `users.token_version` column + bump on password change + "logout all" API/hook |
| **AUTH-SESSION-02-IMPL-5** | FastAPI refresh token + `POST /auth/refresh` + `POST /auth/logout` (revoke) |
| **AUTH-SESSION-02-IMPL-6** | HttpOnly refresh cookie via FastAPI; React/desktop client path |
| **AUTH-SESSION-02-IMPL-7** | Optional `user_sessions` table + device list UI (admin/account) |

**Dependency order:** IMPL-1 → IMPL-2/3 (Streamlit) → IMPL-4 → IMPL-5 → IMPL-6/7 (FastAPI/React).

---

## 9. Risk assessment

| Area | Risk | Notes |
|---|---|---|
| **This audit** | **LOW** | Doc + contract tests only |
| **IMPL-2/3 (Streamlit TTL)** | **MEDIUM** | Touches auth path; thorough regression on restore tests |
| **IMPL-4 (token_version)** | **MEDIUM** | Schema additive; must not break existing logins |
| **IMPL-6 (HttpOnly)** | **MEDIUM** | Requires FastAPI front door or proxy; Streamlit cannot set HttpOnly alone |
| **Remember-me default off** | **LOW** | Reduces accidental long persistence |
| **Logout all** | **LOW** if deferred | Avoid until revocation exists |

**Non-negotiables:** no password weakening, no permission-in-token, no skipping membership re-validation, no weakening void/audit rules.

---

## No-change statement (AUTH-SESSION-02 audit)

- **Audit only.** No auth behavior change, no cookie/token format change, no schema change, no UI implementation, no password or permission weakening.

---

*AUTH-SESSION-02 plans hardening after AUTH-SESSION-01: optional remember-device, idle vs absolute TTL split (fix `auth_expires` non-sliding gap), current-device logout now, server revocation + session table later, HttpOnly cookie via FastAPI. Streamlit keeps policy + checkbox + idle extension; FastAPI gets refresh rotation + HttpOnly. Risk LOW for audit; MEDIUM for implementation slices.*
