# P3.8-L — Alembic Startup Bake-In Review Plan

**Mode:** Documentation + lightweight contract test only. **No runtime behavior change.** `migrate_schema()` is **not removed**; the default flag behavior is unchanged (flag **off** by default → `migrate_schema()` authoritative); no `alembic upgrade`/`stamp`, no schema/model/accounting/API/UI change.
**Status:** **No retirement yet.** This defines the **bake-in period and acceptance criteria** that must pass **before** `migrate_schema()` can be retired or Alembic made the default.
**Context:** P3.8-K2 wired the authoritative schema step behind `ERP_ALEMBIC_AUTHORITATIVE` — `prepare_schema_startup_authoritative()` runs before the boot session, and `_run_schema_startup(_boot_session)` replaces the old `migrate_schema()`+diagnostic pair. Default-off still uses `migrate_schema()`; flag-on can verify `at_head`, run upgrade for a strict-new empty DB, and block unsafe states; `migrate_schema()` is retained.

## 1. Current state

- **Flag default off** — `ERP_ALEMBIC_AUTHORITATIVE` unset/`0` → startup uses `migrate_schema()` exactly as before (authoritative).
- **Flag-on behavior available** — `=1` enables the P3.8-K2 path: `verify_only` at head, `alembic upgrade head` for a **strict-new empty** DB, **block/fail-closed** for unsafe states (unstamped legacy without operator readiness, behind-head without backup+confirmation, ahead-of-code, unknown).
- **Rollback by disabling the flag** — setting `ERP_ALEMBIC_AUTHORITATIVE=0` (or unsetting) reverts to the `migrate_schema()` path with no schema change.
- **`migrate_schema()` retained** — not removed, not disabled; it remains the flag-off path and the rollback target.

## 2. Bake-in scenarios (manual / local)

Run each locally and record the result; **none mutate production data**:

- **Flag off — normal startup** — app starts via `migrate_schema()`; behavior identical to today.
- **Flag on — stamped `at_head` DB** — startup logs `verify_only`, runs **no migration**, app starts normally.
- **Flag on — unstamped legacy DB** — startup **blocks safely** with a clear stamp/backup instruction; **no auto-upgrade, no auto-stamp**; disabling the flag lets the app start again.
- **Flag on — ahead-of-code / unknown DB** — startup **fails closed** with a clear message; never downgrades or guesses.
- **Strict-new empty DB path** — exercised **only against a temporary/throwaway DB** (never `erp_data.db`): `alembic upgrade head` builds the schema; verify it ends at head and the app starts. Real `erp_data.db` is **not** used for this scenario.

## 3. Required evidence before proceeding

All must be **true and recorded** before any retirement / default-flip planning advances:

- **Full `pytest` green** on the bake-in commit.
- **App starts with flag off** (default path, `migrate_schema()`).
- **App starts with flag on against an `at_head` DB** (`verify_only`).
- **No data loss** — accounting rows (journal entries/lines, sales, purchases, payables, movements, allocations) unchanged across flag-off and flag-on starts.
- **No schema drift** — the Alembic-built / verified schema matches the `migrate_schema()`-evolved schema (tables, columns, indexes, uniques, FKs).
- **Rollback verified by disabling the flag** — after a flag-on block, setting the flag off restores a normal start with no schema change.
- **Logs reviewed** — the `[schema]` diagnostic + decision lines are clear, accurate, and match the observed branch for each scenario.

## 4. Do-not-proceed criteria

Stop and remediate if **any** of these occur during bake-in:

- **Any startup block is unclear** — a block/fail-closed message that does not state the DB state and the exact required operator action.
- **Any schema mismatch** — Alembic-built/verified schema differs from the `migrate_schema()` schema.
- **Any Alembic runner unexpected behavior** — wrong argv, production guard bypass, execution when a dry-run was expected, or a non-zero exit not surfaced as fail-closed.
- **Any app instability** — startup hang, `database is locked`, crash, or non-deterministic branch selection.
- **Any user-data concern** — any sign of mutation, loss, or risk to accounting data under any flag state.

## 5. Next-step gates

Only after §3 evidence is complete and **no** §4 criterion triggered:

- **P3.8-M (optional)** — local flag-on smoke test pass on a throwaway DB, documented.
- **P3.9** — `migrate_schema()` **retirement plan** (separate slice; not started here): only after a clean bake-in window, no legacy unstamped DBs, and proven-stable flag-on behavior.
- **PostgreSQL enablement (later)** — Alembic-only schema creation + dual-run parity before any production PG switch; out of scope here.

## No-change decisions (P3.8-L)

- **No runtime behavior change; default flag behavior unchanged (off → `migrate_schema()`); `migrate_schema()` retained.**
- **No `alembic upgrade`/`stamp`, no PostgreSQL switch, no schema/model/accounting/API/UI change, no `Float → Decimal`.**
- **No retirement of `migrate_schema()` and no default-flip** — those are P3.9 and require this bake-in to pass first.

---

*Plan only — no runtime change, default flag off (→ migrate_schema), migrate_schema retained, no retirement yet. Defines the bake-in before retiring migrate_schema or making Alembic default. Scenarios (manual/local): flag-off normal startup; flag-on at_head verify_only; flag-on unstamped legacy blocks safely; flag-on ahead/unknown fails closed; strict-new empty DB upgrade only against a temporary DB. Required evidence: full pytest green, app starts flag-off, app starts flag-on at_head, no data loss, no schema drift, rollback verified by disabling the flag, logs reviewed. Do-not-proceed if: any unclear block, schema mismatch, unexpected Alembic runner behavior, app instability, or user-data concern. Next gates: P3.8-M optional local smoke, P3.9 migrate_schema retirement plan, PostgreSQL enablement later.*
