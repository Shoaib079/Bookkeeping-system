# AUTH-SESSION-01-IMPL-1 — Enable/document session restore

**Status:** Implemented (2026-06). **Documentation + contract tests only; no auth behavior change.**

## Delivered

1. **Operator guide:** `docs/AUTH_SESSION_01_OPERATOR.md` — `ERP_SESSION_RESTORE_SECRET`, generation, local export, DEV_MODE bypass, 8h TTLs, logout/password invalidation, non-HttpOnly limitation, FastAPI hardening path.
2. **Contract tests:** `tests/test_auth_session_01_impl_contract.py` — operator doc guard + behavioral gaps (ph_frag restore rejection, logout blocks restore, secret-unset cookie no-op).
3. **Existing coverage retained:** `tests/test_ux01_session_restore.py` — mint/verify, tamper, expiry, secret gate, DEV_MODE, logout cookie clear.

## Operator action (production)

```bash
export ERP_SESSION_RESTORE_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export ERP_DEV_MODE=0
```

## Not in scope (later slices)

- AUTH-SESSION-01-IMPL-2 — cookie renderer compatibility: `components.v1.html` for restore cookie write/clear (replaces `st.html`).

- AUTH-SESSION-01-IMPL-3 — remember-this-device toggle
- AUTH-SESSION-01-IMPL-4 — HttpOnly + JWT unification
