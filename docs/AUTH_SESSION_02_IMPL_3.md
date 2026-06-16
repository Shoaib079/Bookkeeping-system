# AUTH-SESSION-02-IMPL-3 — Idle Session Extension

**Status:** Complete (verified closure 2026-06-16)  
**Implementation commit:** `ee57dc1` — *AUTH-SESSION-02 add idle session extension*  
**Prior tag:** `auth-session-02-idle-extension`  
**Closure tag:** `auth-session-02-impl3-idle-extension`

## Scope

True idle extension of `auth_expires` on authenticated Streamlit activity, using canonical policy in `services/session_policy.py`.

| Component | Location |
|-----------|----------|
| `should_extend_idle()` | `services/session_policy.py` |
| `compute_session_expiry()` | `services/session_policy.py` |
| `_maybe_extend_idle_session()` | `app.py` — called from `main()` after boot session |
| Characterization tests | `tests/test_auth_session_02_impl_3_idle_extension.py` |

## Behavior

- On each authenticated run, if session is active and under absolute cap, `auth_expires` slides forward by idle TTL (capped by `session_started_at` + absolute TTL).
- `session_started_at` is **never** reset on extension.
- Expired sessions are **not** revived.
- Browser-session mode (idle = absolute = 8h): extension is a no-op when already at cap.
- Remember-device absolute cap (30d) still enforced.
- Restore cookie remains browser-session 8h (IMPL-2); not widened by remember mode.

## Not in scope (deferred)

- Remember-device checkbox (IMPL-4+)
- Server revocation / `token_version`
- FastAPI HttpOnly refresh path

## Verification

```bash
pytest tests/test_auth_session_02_impl_3_idle_extension.py
pytest tests/test_auth_session_02_impl_1_session_policy.py
pytest tests/
```

## Rollback

Revert `ee57dc1` or remove `_maybe_extend_idle_session()` call from `main()` — sessions revert to non-sliding absolute expiry from login time.
