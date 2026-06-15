# AUTH-SESSION-01 — Session restore operator guide

**Purpose:** Enable login persistence across browser refresh in production by configuring the **existing** HMAC restore cookie. No new auth logic is required.

## Quick fix (production)

Set a stable secret before starting the app:

```bash
export ERP_SESSION_RESTORE_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
streamlit run app.py
```

Without this variable, session restore is **disabled** and users must log in again after every hard refresh or new tab.

## Environment variables

| Variable | Required | Effect |
|----------|----------|--------|
| `ERP_SESSION_RESTORE_SECRET` | **Yes** (production) | Enables mint/verify of the `erp_session_restore` cookie. Unset or empty → restore is a no-op. |
| `ERP_DEV_MODE` | No (default `0`) | When `1`, dev auto-login runs and **restore is skipped** entirely. |

### Generating a strong secret

- Use **≥ 32 bytes** of randomness (48+ URL-safe characters is recommended).
- Examples:

```bash
# Python (recommended)
python -c 'import secrets; print(secrets.token_urlsafe(48))'

# OpenSSL
openssl rand -base64 48
```

- Store in your secrets manager / deployment platform — **not** in git.
- Keep the value **stable** across restarts (changing it invalidates all outstanding restore tokens).
- If compromised, rotate the secret (users re-login once; old tokens fail HMAC verify).

### Setting locally

**macOS / Linux (current shell):**

```bash
export ERP_SESSION_RESTORE_SECRET='paste-your-secret-here'
export ERP_DEV_MODE=0   # ensure restore is not masked by dev bypass
streamlit run app.py
```

**Persistent local profile** (optional — add to `~/.zshrc` or `~/.bashrc` for dev/staging only; never commit):

```bash
export ERP_SESSION_RESTORE_SECRET='your-local-staging-secret'
```

**Docker / systemd / hosting:** inject `ERP_SESSION_RESTORE_SECRET` via the platform's secret/env mechanism (Render, Fly, Kubernetes Secret, etc.).

## How restore works (already implemented)

1. On successful login, the app mints an HMAC-signed token and writes cookie `erp_session_restore` (8h `max-age`).
2. On each authenticated run, the cookie is **re-minted** (sliding window).
3. On a fresh Streamlit session (refresh/new tab), `_early_restore_auth_session()` reads the cookie, verifies signature + expiry + password fragment, re-validates the user in the DB, and re-establishes `auth_user`.

Cookie name: `erp_session_restore`  
Signing key: `ERP_SESSION_RESTORE_SECRET`  
Code: `app.py` — `_mint_restore_token`, `_verify_restore_token`, `_try_restore_session_from_cookie`

## Session TTLs (unchanged)

| TTL | Constant | Hours | Behavior |
|-----|----------|-------|----------|
| Idle session | `_SESSION_TTL_HOURS` | **8** | `auth_expires` in `st.session_state`; `_current_user()` returns None after expiry |
| Restore token | `_RESTORE_TOKEN_TTL_HOURS` | **8** | Cookie `max-age` and token `exp` claim |

No "remember me" toggle yet — when the secret is set, restore is always attempted for non-logged-out sessions.

## DEV_MODE behavior

`ERP_DEV_MODE=1` enables `_dev_auto_login` and **disables** restore cookie mint/read/render. Developers may not see refresh-logout in dev even when the secret is unset. **Production must run with `ERP_DEV_MODE=0`** and the secret set.

## Logout

`_logout()`:

- Sets `session_logged_out` (blocks restore until next explicit login)
- Clears `auth_user`, company context, and related session keys
- Calls `_render_session_restore_cookie(clear=True)` to delete the restore cookie

## Password change

Tokens embed a short `ph_frag` derived from the stored password hash. After a password change, existing restore tokens fail verification and restore returns false — user must log in with the new password.

## Security limitations (Streamlit era)

- The restore cookie is set via **client-side JavaScript**, **not HttpOnly** — readable by JS if XSS occurs.
- Mitigations today: HMAC signature, expiry, `ph_frag` binding, `SameSite=Lax`, `Secure` on HTTPS, DB re-validation on restore.
- **Future (FastAPI migration):** server-set **HttpOnly** refresh cookie unified with JWT access+refresh (`services/tokens.py`) — see `docs/AUTH_SESSION_01_AUDIT.md` §4.

## Verification

```bash
pytest tests/test_auth_session_01_audit.py
pytest tests/test_auth_session_01_impl_contract.py
pytest tests/test_ux01_session_restore.py
```

## Related docs

- `docs/AUTH_SESSION_01_AUDIT.md` — full audit + root cause
- `docs/AUTH_SESSION_01_IMPLEMENTATION.md` — IMPL-1 status
