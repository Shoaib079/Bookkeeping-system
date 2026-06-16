# P3.9-C — migrate_schema() Implementation Removal

**Date:** 2026-06-05  
**Mode:** Phase C — remove SQLite DDL body from production `migrate_schema()`; retain no-op stub + `DeprecationWarning`. Schema evolution is **Alembic-only**.

**Prerequisites:** P3.9-A ✅ · P3.9-B-CHAR ✅ · P3.9-B ✅ · P3.8-N default-on · schema equivalence gate (P3.4-D / P3.8-L-TESTS)

**Contract:** `tests/test_p3_9_c_removal.py` · archived body: `tests/legacy_migrate_schema.py`

---

## Verdict

**P3.9-C Phase C: SHIPPED** — production `migrate_schema()` is a **no-op stub** (warn + return). SQLite DDL body archived in `tests/legacy_migrate_schema.py` for equivalence harnesses only.

**ALEMBIC-01** milestone: `migrate_schema()` no longer evolves schema in production. Unstamped/legacy DBs must use Alembic; explicit `=0` no longer applies DDL.

---

## Implementation

| Item | Detail |
|------|--------|
| Production | `app.migrate_schema` — `DeprecationWarning` + `return None` (no DDL) |
| Message | `MIGRATE_SCHEMA_DEPRECATION_MESSAGE` — references P3.9-C removal + Alembic-only |
| Wiring | Unchanged — flag-off still calls `migrate_schema_fn` (no-op) then diagnostics |
| Archive | `tests/legacy_migrate_schema.legacy_migrate_schema()` — pre-C body frozen |
| Equivalence | `p3_schema_equivalence_utils` uses legacy module for schema B |

---

## Flag-off path (post-C)

| Env | Behavior |
|-----|----------|
| Default-on (unset) | Alembic authoritative — **no** `migrate_schema` call at stamped `at_head` |
| `=0` / explicit opt-out | Calls no-op `migrate_schema()` (warning only) + diagnostics — **no DDL** |

Operators requiring schema evolution must use Alembic (`alembic upgrade head` / stamp). Rollback to DDL via `=0` is **no longer available**.

---

## Test harness

| File | Change |
|------|--------|
| `tests/legacy_migrate_schema.py` | **New** — archived DDL body |
| `tests/p3_schema_equivalence_utils.py` | Uses `legacy_migrate_schema` for schema B |
| `tests/test_phase14da_model.py` | Idempotency tests target legacy module |

---

## No-change statement (P3.9-C)

No startup wiring removal, no flag default change, no new Alembic revision, no schema/model/accounting/API/UI change beyond removing production DDL from `migrate_schema()`.
