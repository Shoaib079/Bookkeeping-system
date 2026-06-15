# P3.8-J — Flag-Gated Startup Wiring Plan

**Mode:** Documentation + lightweight contract test only. **No runtime change in this slice.** No startup wiring is implemented; `app.py` behavior is unchanged; Alembic is **not authoritative**; `migrate_schema()` is **not removed** and still runs first; no `alembic upgrade`/`stamp`, no schema/model/accounting/API/UI change.
**Status:** **No startup wiring yet.** `migrate_schema()` **remains authoritative now and runs first.** This document specifies the exact implementation for the **later** P3.8-K slice where startup finally acts on `ERP_ALEMBIC_AUTHORITATIVE=1`.
**Context:** P3.8-C added the flag parser; P3.8-E added the pure decision function; P3.8-F logs diagnostics only; P3.8-H added the safe Alembic runner; P3.8-I added the migration safety gate. This plan composes those pieces into the startup branch — without building it here.

## 1. Startup sequence with flag off

**Unchanged from today** — this is the fail-safe default:
- `migrate_schema(_boot_session)` **runs first** (current authoritative path).
- `_log_schema_startup_diagnostic(_boot_session)` logs the read-only diagnostic (P3.8-F).
- All existing seeds/migrations run exactly as now.
- The decision function is **not acted on** (diagnostics only). No Alembic command runs.

## 2. Startup sequence with flag on (target — P3.8-K)

When `ERP_ALEMBIC_AUTHORITATIVE=1`, startup composes the existing pieces:

1. **Build diagnostic** — read-only schema/version snapshot (P3.7 / `services.schema_version`).
2. **Build decision** — call the pure decision function (P3.8-E) with the parsed flag (P3.8-C), diagnostic, is-new-DB, and dialect.
3. **Evaluate the gate if needed** — for any action requiring it, consult the migration safety gate (P3.8-I) for `backup_available` / `confirmation_given`.
4. **Act per branch:**

| Decision | Startup action (flag on) |
|----------|---------------------------|
| **at_head** | **skip `migrate_schema()`**; `verify_only`; continue to seeds and start |
| **new / empty DB** | `run_upgrade_head` **only through the safe Alembic runner (P3.8-H)** + gate; verified-empty only |
| **unstamped legacy** | **block startup** with stamp instructions (verify equivalence + back up + `alembic stamp 0001`); no auto-upgrade, no auto-stamp |
| **behind_head** | **block** unless a future backup/confirmation mechanism is satisfied via the gate; no populated-DB upgrade in this slice |
| **ahead_of_code / unknown / ambiguous** | **fail closed** with a clear message; never downgrade, never guess |

- Only `at_head` (skip migrate_schema) and `new empty DB` (runner upgrade) **proceed**; all other on-branches **block or fail closed** — no populated DB is mutated.
- Alembic is invoked **only** through the P3.8-H runner; startup never shells out raw Alembic.

## 3. App wiring location

- **Current startup location** (`app.py`, `def main()` → `with get_session() as _boot_session:`):
  ```
  26297    with get_session() as _boot_session:
  26298        migrate_schema(_boot_session)
  26299        _log_schema_startup_diagnostic(_boot_session)
  26300        initialize_chart_of_accounts(_boot_session)
  ...
  ```
- **Where the branch is inserted** — a single new dispatcher call **replaces lines 26298–26299** (the `migrate_schema()` + diagnostic pair), e.g. `_run_schema_startup(_boot_session)`. Everything from `initialize_chart_of_accounts` onward is **unchanged**.
- **`_run_schema_startup(session)` (future P3.8-K)** encapsulates the branch:
  - **flag off** → call `migrate_schema(session)` then `_log_schema_startup_diagnostic(session)` — **byte-for-byte the current path**.
  - **flag on** → run the §2 sequence (diagnostic → decision → gate → act); raise the structured startup error on block/fail.
- **Keeping the old path when flag off** — the flag-off branch is the literal existing two calls in the existing order; no behavior difference when `ERP_ALEMBIC_AUTHORITATIVE` is unset/`0`.

## 4. Error handling

- **Structured startup error** — a dedicated exception/result type carrying: DB state, current vs expected `alembic_version`/head, the chosen action, and the exact required operator action (back up / stamp / upgrade / restore).
- **Clear user/operator message** — surfaced at startup (Streamlit + logs); actionable, never a bare traceback.
- **No silent fallback when flag on** — if a flag-on branch blocks or fails closed, startup **stops** with the message; it does **not** quietly fall back to `migrate_schema()` (that would defeat the gate).
- **Flag off can revert to `migrate_schema`** — disabling the flag returns to the retained current path with no schema change.

## 5. Tests for implementation (P3.8-K)

- **flag off** → `migrate_schema()` runs first; diagnostic logged; behavior unchanged; suite green.
- **flag on + at_head** → `migrate_schema()` is **skipped**; `verify_only`; app continues.
- **flag on + new empty DB** → calls the **safe runner** dry/safe `upgrade head` path (through the gate); no raw alembic.
- **flag on + unstamped legacy** → **blocks** with stamp instructions; no upgrade/stamp executed.
- **flag on + ahead_of_code / unknown** → **blocks / fail closed**.
- **No raw alembic calls in `app.py`** — assert `app.py` contains no direct `alembic upgrade`/`stamp` invocations; Alembic only via the P3.8-H runner.
- **Runner / gate used** — assert the flag-on path goes through the safe runner (P3.8-H) and the safety gate (P3.8-I).
- **No production DB action without backup/confirmation** — a populated-DB action is never executed unless the gate reports backup + confirmation.
- **Full suite green** — including the existing startup tests.

## 6. Rollback

- **Disable the flag** — set `ERP_ALEMBIC_AUTHORITATIVE=0` to immediately revert to the `migrate_schema()` path (no schema change needed).
- **Restore the backup if needed** — if a flag-on startup mutated a DB and misbehaved, stop the app and restore the backup.
- **`migrate_schema()` retained** — not removed/disabled; it remains the flag-off path and a legacy no-op safety net.
- **Never edit accounting tables manually** — recovery is restore-from-backup + flag-off only.

## No-change decisions (P3.8-J)

- **No runtime/startup change; no wiring implemented; `app.py` untouched; `migrate_schema()` runs first and stays authoritative now.**
- **No `alembic upgrade`, no `alembic stamp`, no PostgreSQL switch, no schema/model/accounting/API/UI change, no `Float → Decimal`.**
- **The wiring is specified, not implemented** — implementation + tests are the future P3.8-K slice.

---

*Plan only — no startup wiring yet, `app.py` untouched, `migrate_schema()` runs first and stays authoritative now. Future P3.8-K: replace the `migrate_schema()`+diagnostic pair (app.py lines 26298–26299) with a single `_run_schema_startup(session)` dispatcher. Flag off → existing path byte-for-byte (migrate_schema then diagnostic). Flag on → build diagnostic → build decision (P3.8-E) → evaluate gate (P3.8-I) → act: at_head skip migrate_schema/verify_only; new empty DB upgrade head only via safe runner (P3.8-H) + gate; unstamped legacy block with stamp instructions; behind_head block unless backup/confirmation; ahead/unknown fail closed. Structured startup error, clear operator message, no silent fallback when flag on; flag off reverts to migrate_schema. Tests: flag-off unchanged, on+at_head skips migrate_schema, on+new empty uses runner, on+unstamped blocks, on+ahead/unknown blocks, no raw alembic in app.py, runner/gate used, no populated-DB action without backup/confirmation. Rollback = disable flag + restore backup + retained migrate_schema; never edit accounting tables manually.*
