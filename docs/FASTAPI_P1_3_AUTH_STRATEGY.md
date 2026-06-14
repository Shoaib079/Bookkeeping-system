# FASTAPI-P1.3 — Auth / Token / Session Strategy

**Mode:** Planning only. No code, no implementation, no DB changes, no write endpoints. Preserve current Streamlit behavior.
**Inputs:** migration audit, P0 hardening plan, `api/dependencies.py`, `api/guards.py`, `services/context.py`, `services/permissions.py`, `services/user_access.py`, `app.py` auth helpers.
**Goal:** real FastAPI authentication + active-company context **before** any write endpoints.

**Two facts that anchor the whole design:**
1. The API **already DB-resolves permissions per request** (`build_request_context` → `user_access.effective_permissions`) — permissions are *not* carried anywhere. Keep it that way.
2. The current dev-header model already separates **authentication** (`X-User-Id`) from **company selection** (`X-Company-Id`) from **per-request membership/permission resolution** (the guards). JWT should replace only the *authentication* leg; the rest stays.

---

## 1. Current Streamlit auth

- **Login** (`_login`, `app.py:4811`): lookup active `User` by username → `_verify_password(password, user.password_hash)` → update `last_login` → `_establish_auth_session`.
- **Password hashing** (`_hash_password`/`_verify_password`, `:2907/:2914`): **PBKDF2-HMAC-SHA256, 260k iterations**, `salt:key_hex` format. **Reusable** as the shared verification for FastAPI.
- **Session storage:** `auth_user` dict + `auth_expires` datetime in `st.session_state`; `_current_user()` reads it with expiry check.
- **Company selection** (`_establish_auth_session`): resolves `CompanyUser` memberships → auto-activate if 1, picker if many, else restore last-active; sets `active_company_id` + `active_company_role`.
- **Role/membership:** `active_company_role` = `membership.role`; `_can` resolves effective perms via `user_access` (DB) with `User.role` fallback.
- **Existing signed-token mechanism** (`_password_hash_fragment` + HMAC-SHA256 claims incl. `ph_frag`, `:2779–2907`): a "remember/restore" token that **invalidates on password change** (the `ph_frag` check). **Strong precedent** — reuse the `ph_frag` idea in the JWT.
- **Reusable:** PBKDF2 verify/hash; User/CompanyUser models; `user_access` permission/membership services; the `ph_frag` invalidation pattern; `RequestContext`/`build_request_context`.
- **Streamlit-only:** `st.session_state` storage, the login UI, company-picker chrome, theme/landing/locale prefs on login, DEV auto-login.

## 2. FastAPI auth target (recommendation)

This is a **local desktop app** today (Streamlit + SQLite, single process) with a **future React** client. Recommend a model that serves both:

- **JWT access token (short-lived, ~15–30 min) + refresh token (longer, revocable).**
- **Access token:** Bearer, identity-only (§3). Sent on every request.
- **Refresh token:** longer-lived, **revocable** (jti/denylist or `token_version`), used to mint new access tokens. For the desktop-local case it can live in local secure storage; for React later, the secure pattern is **httpOnly refresh cookie + access token in memory**.
- **Not a pure session cookie** (couples to a server session store; weaker for a stateless API + React). **Not permissions-in-token** (§5). **Hybrid** only in the sense of bearer-access + revocable-refresh.

This replaces `X-User-Id` with `Authorization: Bearer <access>`; `X-Company-Id` stays as the company selector (§4).

## 3. Token contents

**Identity-only. Minimal. No authorization data.**

| Claim | In token? | Why |
|-------|-----------|-----|
| `sub` / `user_id` | ✅ | the authenticated identity |
| `iat`, `exp` | ✅ | issue + expiry |
| `jti` (token id) | ✅ | revocation handle |
| `ph_frag` (password-hash fragment) | ✅ | **invalidate on password change** (reuse existing mechanism) |
| `token_version` | ✅ (optional) | global/user-level mass revocation |
| `active_company_id` | ❌ (see §4) | stale-token + membership-change risk; optional non-authoritative *hint* only |
| `role` | ❌ | DB-resolved per request (changes with membership) |
| `permissions` | ❌ | DB-resolved per request (overrides/OWNER_LOCKED change anytime) |

## 4. Active-company strategy

**Active company is per-request context, NOT authoritative in the token.** Keep the `X-Company-Id` header (or a route/path param) as the company selector; **re-validate membership server-side every request** (`require_company_membership`).

| Concern | Token-baked company | Per-request (recommended) |
|---------|---------------------|---------------------------|
| Multi-company users | re-issue on every switch | switch = change the header; no re-issue |
| Company switching | clunky (token churn) | instant |
| Stale token | honors old company after revocation | server re-checks membership each request |
| Membership revoked | stale token still works until expiry | denied immediately |
| Security | weaker | stronger (server is authority) |

The token authorizes the **user**; the request selects the **company**; the server **validates membership + resolves role/permissions** each request. The token MAY carry a `last_active_company` **hint** for UX, never trusted for authorization. This matches today's dev-header split exactly — minimal change.

## 5. Permission resolution

- **DB-resolved every request** (already implemented). Token carries no permissions/role.
- **Effect:** per-user **override** changes, **OWNER_LOCKED** stripping, **membership inactive/revoked**, and role changes all take effect on the **next request** — no token re-issue, no staleness.
- **Cost:** one permission resolution per request (current behavior; acceptable). `user_access.resolve_effective_permissions` already applies template ∪ grants − denies and strips OWNER_LOCKED for non-owners.
- **Revoked/inactive membership:** `require_company_membership` returns no active role → 403.

## 6. RequestContext mapping (request → context)

```
HTTP request
  → extract Authorization: Bearer <access>
  → decode+verify JWT (signature, exp, ph_frag matches user.password_hash, jti not revoked, token_version ok)   [fail → 401]
  → load User(user_id); ensure is_active                                                                          [fail → 401/403]
  → read X-Company-Id (company selector)                                                                          [absent on scoped route → 400]
  → require_company_membership(session, user, company) → active membership role                                   [fail → 403]
  → build_request_context(user_id, company_id, membership_role, fallback_role=User.role)  [DB-resolves permissions]
  → RequestContext  (same object the read spine + guards already consume)
```

Only the **first two lines** change vs today (JWT decode replaces `X-User-Id`). Everything downstream is unchanged — `build_request_context`, the guards, `RequestContext` are reused as-is.

## 7. Security rules

| Condition | Response |
|-----------|----------|
| Missing/expired/invalid access token | **401** |
| Signature/`ph_frag` mismatch (password changed) or `token_version` bumped | **401** |
| Inactive user | **401** (treat as unauthenticated) |
| Missing `X-Company-Id` on a company-scoped route | **400** |
| User not an active member of the company | **403** |
| Permission denied (action not in effective set) | **403** |
| Role mismatch / OWNER_LOCKED action by non-owner | **403** |
| Revoked refresh/access (jti in denylist) | **401** |

(The guard already maps 400/401/403; extend the 401 set to JWT failures.)

## 8. API migration phases

| Phase | Scope |
|-------|-------|
| **P1.3a** | This plan (auth strategy) — no code |
| **P1.3b** | Token service scaffolding: JWT issue/verify (HS256 with the existing secret pattern), `ph_frag` + `jti`/`token_version`, refresh mint + revoke. Reuse PBKDF2 verify. No endpoints wired yet |
| **P1.3c** | `POST /auth/login` → access+refresh; reuse shared password verification + user/membership services; `POST /auth/refresh`, `POST /auth/logout` (revoke) |
| **P1.3d** | `GET /auth/me` (user + memberships) and `GET /auth/companies` / company-switch contract (returns memberships; switch = client changes `X-Company-Id`) |
| **P1.3e** | Replace dev headers: `get_request_context` decodes the Bearer token instead of `X-User-Id`; **keep `X-Company-Id`** as company selector; keep dev-header mode behind an explicit DEV flag for tests only |
| **P2** | Write endpoints — only **after** auth is stable (and after P0.5d commit-ownership) |

## 9. Streamlit coexistence

- **Streamlit keeps `st.session_state` auth unchanged** — no behavior change to the desktop UI.
- **FastAPI auth is separate** (JWT) but **shares the substrate**:
  - **Password verification** — extract/reuse `_verify_password`/`_hash_password` (PBKDF2) into a shared `services` module so both verify identically (Streamlit keeps calling the same logic — no behavior change).
  - **User/CompanyUser models** and **`user_access`** membership/permission services — already shared.
  - **`ph_frag` invalidation** — reuse the existing fragment helper for JWT.
- **No shared *session*** — Streamlit session_state and JWT are independent; they only share verification + services. This keeps the desktop app untouched while the API gets real auth.

## 10. Tests required (before implementation)

1. **Login success / failure** — valid creds; bad password; unknown user; **inactive user denied**.
2. **Token expiry** — expired access → 401; refresh mints a new access.
3. **Password-change invalidation** — `ph_frag` mismatch → 401.
4. **Revocation** — `jti` denylist / `token_version` bump → 401.
5. **Revoked / inactive membership** — 403 on that company; other companies unaffected.
6. **Company switch** — changing `X-Company-Id` re-resolves role/permissions; no re-issue needed.
7. **Permission change reflected next request** — add/remove override, OWNER_LOCKED → effective immediately.
8. **No cross-company access** — user A passing company B's id → 403 (membership re-validated).
9. **Role fallback** — no `membership_role` → `User.role` fallback path (matches `_can`).
10. **Scoped-route company guard** — missing `X-Company-Id` → 400; read endpoints still enforce read permission.

---

## What must not change

- Streamlit auth/session behavior (login, company picker, prefs, DEV auto-login) — untouched.
- Password hashing scheme (PBKDF2 params) — reused as-is.
- `RequestContext`, `build_request_context`, the read-spine guards — reused unchanged.
- Per-request DB permission resolution (no permissions in token).
- The existing read endpoints' behavior (P1.0–1.2) — only the *authentication* leg changes.

---

*Planning only. No code, no DB, no write endpoints. Recommendation: identity-only **JWT access + revocable refresh** (reusing PBKDF2 verify + the `ph_frag` invalidation pattern); **active company stays a per-request selector** (`X-Company-Id`) with server-side membership re-validation, never authoritative in the token; **permissions DB-resolved every request** so overrides/OWNER_LOCKED/revocation are immediate. JWT replaces only `X-User-Id`; the guards, `RequestContext`, and Streamlit auth are untouched. Writes wait for stable auth (and P0.5d).*
