# P3.8-M — Local Smoke Test Record

**Date:** 2026-06-15

**Mode:** Manual local smoke verification after P3.8-K2 startup wiring. **No code changes in this slice.**

## Environment

| Item | Value |
|------|-------|
| Platform | macOS |
| Database | `erp_data.db` |
| Alembic revision | `0001` |
| Feature flag | `ERP_ALEMBIC_AUTHORITATIVE` |

## Backup verification

Database backups created successfully:

- `erp_data.db.bak-20260615-135306`
- `erp_data.db.bak-20260615-135356`

Backup sizes matched the live database (~1.5 MB).

## Smoke test 1 — Flag OFF (default path)

**Command:**

```bash
unset ERP_ALEMBIC_AUTHORITATIVE
streamlit run app.py
```

**Result:**

- Application started successfully.
- `migrate_schema()` path remained active.
- No Alembic execution observed.
- No startup failures.

**Status:** PASS

## Smoke test 2 — Flag ON (Alembic-authoritative mode)

**Command:**

```bash
export ERP_ALEMBIC_AUTHORITATIVE=1
streamlit run app.py
```

**Result:**

- Application started successfully.
- No startup blocking occurred.
- Existing production database opened correctly.
- No visible errors or schema failures.
- Behavior consistent with `at_head` / `verify_only`.

**Status:** PASS

## Smoke test 3 — Rollback

**Command:**

```bash
unset ERP_ALEMBIC_AUTHORITATIVE
streamlit run app.py
```

**Result:**

- Application returned to the legacy startup path.
- Startup remained successful.
- Rollback requires only disabling the feature flag.

**Status:** PASS

## Conclusions

P3.8-M local smoke testing completed successfully.

Verified:

- Backup creation
- Flag-on startup
- Flag-off rollback
- Database stability
- No data loss observed
- `migrate_schema()` retained and functional

## Recommendation

Proceed to:

- **P3.9** — `migrate_schema()` retirement planning

**Do NOT remove `migrate_schema()` yet.**

---

*Manual smoke record only. Flag-off default unchanged; flag-on verified on stamped `erp_data.db` at revision `0001`; rollback = unset flag. `migrate_schema()` retained.*
