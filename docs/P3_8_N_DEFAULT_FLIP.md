# P3.8-N — Alembic Authority Default Flip

**Date:** 2026-06-16  
**Mode:** Default-on flip for `ERP_ALEMBIC_AUTHORITATIVE`. **`migrate_schema()` retained** as explicit opt-out legacy path (`=0`/`false`/`off`). No schema/model change, no retirement (P3.9).

**Prerequisites:** P3.8-L-EXEC ✅ · P3.8-L-TESTS ✅ · all target DBs stamped at Alembic head before deploying to production.

---

## Verdict

**P3.8-N default flip: SHIPPED** — unset/empty env → Alembic authoritative; explicit `ERP_ALEMBIC_AUTHORITATIVE=0` (or `false`/`no`/`off`) → legacy `migrate_schema()` path.

**`migrate_schema()` not removed** — P3.9 retirement remains a separate slice.

---

## Parsing rules (after P3.8-N)

| Input | Result |
|-------|--------|
| unset / `None` | **`True`** (default on) |
| `""` or whitespace only | **`True`** (default on) |
| `1`, `true`, `yes`, `on` | `True` |
| `0`, `false`, `no`, `off` | `False` (legacy `migrate_schema()` path) |
| any other value | `False` (fail-safe → legacy path) |

Implementation: `services/schema_startup.py` — `parse_alembic_authoritative_flag()`.

---

## Rollback

Set **`ERP_ALEMBIC_AUTHORITATIVE=0`** (or `false`/`off`) → `migrate_schema()` authoritative again; **no schema change**.

**Note:** After P3.8-N, *unset* **does not restore** the legacy path — explicit opt-out is required.

---

## Production checklist

1. Database **stamped at Alembic head** (`0001` or later) before deploy without explicit `=0`.
2. Unstamped legacy DBs **block startup** under default-on (by design).
3. Keep rollback env documented for operators: `ERP_ALEMBIC_AUTHORITATIVE=0`.

---

## Next slice

**P3.9** — phased `migrate_schema()` retirement (function retained through Phase A/B).

Contract: `tests/test_p3_8_n_default_flip.py`

---

## No-change statement (P3.8-N)

No `migrate_schema()` removal, no Alembic revision change, no PostgreSQL runtime switch, no schema/model/accounting change.
