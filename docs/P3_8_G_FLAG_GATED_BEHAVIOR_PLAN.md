# P3.8-G — Flag-Gated Alembic Behavior Plan

**Mode:** Documentation + lightweight contract test only. **No runtime change in this slice.** `ERP_ALEMBIC_AUTHORITATIVE` is **not acted on**; `app.py` behavior is unchanged; Alembic is **not authoritative**; `migrate_schema()` is **not removed, not disabled** and **still runs first**; no `alembic upgrade`, no `alembic stamp`, no schema/model/accounting/API/UI change.
**Status:** **No runtime change yet.** `migrate_schema()` **remains authoritative now and runs first.** This document plans the **first** flag-gated behavior slice to be implemented **later**.
**Context:** P3.8-C added the `ERP_ALEMBIC_AUTHORITATIVE` parser; P3.8-E added the pure decision function (inputs → action); P3.8-F logs decision diagnostics only. This plan defines how `ERP_ALEMBIC_AUTHORITATIVE=1` will **begin acting** on that decision — the smallest safe behavior step.

## 1. Scope of first behavior slice

The first slice wires the decision function to **act** only for the safe branches; risky branches **block** rather than mutate.

| Branch | Behavior in first slice |
|--------|--------------------------|
| **flag off** | **Unchanged** — `migrate_schema()` runs as today; decision function not acted on (diagnostics only, per P3.8-F) |
| **flag on + at_head** | `verify_only` — **skip `migrate_schema()`**; confirm `alembic_version == head` and start normally |
| **flag on + new / empty DB** | allow **`alembic upgrade head` only for a verified empty DB** (no app tables) → ends at `0001` |
| **flag on + unstamped legacy** | **block startup** with clear **stamp instructions** (verify equivalence + back up + `alembic stamp 0001`); **never auto-upgrade, never auto-stamp** |
| **flag on + behind_head** | **block** unless a **backup + confirmation mechanism exists**; no populated-DB upgrade in this slice |
| **flag on + ahead_of_code / unknown / ambiguous** | **fail closed** with a clear message; never downgrade, never guess |

- Only **two branches actually mutate/skip** in this first slice: `at_head` (skip migrate_schema) and `new empty DB` (upgrade head on a guaranteed-empty DB). Every other on-branch **blocks or fails closed** — no populated DB is touched.

## 2. What is explicitly NOT included

- **No production auto-upgrade of a populated DB** — `behind_head` blocks (no automatic DDL on user data) in this slice.
- **No automatic stamp of a legacy DB** — `unstamped legacy` blocks with instructions; stamping stays a manual, operator-confirmed step.
- **No removal of `migrate_schema()`** — it is retained (runs when flag off; remains a legacy no-op safety net when flag on).
- **No PostgreSQL runtime switch** — still SQLite; PG path remains future.
- **No `Float → Decimal`** — out of scope.

## 3. Required helpers before wiring

These must exist and be unit-tested **before** any startup wiring:

- **Safe empty-DB detection** — a read-only check that the DB has **no app tables** (distinguish truly-empty from unstamped-legacy); only an empty DB qualifies for `alembic upgrade head` automatically.
- **Safe Alembic command wrapper** — a thin, audited wrapper around `alembic upgrade head` / `alembic stamp` (and `current`/`heads` reads) that is **idempotent, logged, and never destructive**; centralizes command construction so startup never shells out ad-hoc.
- **Backup / confirmation gate abstraction** — a single gate that reports `backup_available` / `confirmation_given` and **must be satisfied** before any populated-DB action; absent satisfaction, the action blocks.
- **Clear startup error / message type** — a structured result/exception carrying DB state, current vs expected revision, and the exact required operator action (back up / stamp / upgrade / restore); used for both `block` and `fail_closed`.

## 4. Test matrix (for the future behavior slice)

- **flag off** → current behavior; `migrate_schema()` runs; suite green.
- **flag on + at_head** → `migrate_schema()` is **skipped**; `verify_only`; app starts.
- **flag on + new empty DB** → safe-empty detection passes → **`alembic upgrade head`** builds `0001`.
- **flag on + unstamped legacy** → **blocks startup** with stamp instructions; no upgrade, no stamp executed.
- **flag on + behind_head (no confirmation)** → **blocks**; no upgrade executed.
- **flag on + ahead_of_code** → **fail closed**; no downgrade.
- **flag on + unknown / ambiguous** → **fail closed**.
- **No destructive commands** — assert the command wrapper is never asked to drop/downgrade; only `upgrade head` (empty DB), `stamp` (manual), and read-only `current`/`heads`.
- **Rollback guidance** — assert the block/fail messages carry the restore-backup + disable-flag instructions.

## 5. Safety and rollback

- **Restore the backup** if a flag-on startup misbehaves (stop app, replace the SQLite file).
- **Disable the flag** — set `ERP_ALEMBIC_AUTHORITATIVE=0` to immediately revert to the `migrate_schema()` path.
- **`migrate_schema()` retained** — because it is not removed, flag-off restores prior authoritative behavior with no schema change.
- **Never edit accounting tables manually** — recovery is restore-from-backup + flag-off only; never hand-fix `alembic_version` or accounting rows (consistent with the never-delete-accounting-rows policy).
- **No destructive migrations**; **no auto-upgrade of populated DB without backup**; **fail closed on ambiguity**.

## 6. Execution sequence

The first behavior is built across small, separately-reviewed slices:

- **P3.8-H — safe Alembic command wrapper** — idempotent, logged, non-destructive command abstraction + tests.
- **P3.8-I — backup / confirmation gate** — the gate abstraction + tests; nothing acts on populated DBs without it.
- **P3.8-J — startup wiring behind the flag** — wire the decision function into `app.py` startup for the safe branches only (at_head skip, empty-DB upgrade), everything else blocks/fails closed; flag default stays `0`.
- **P3.8-K — bake-in review** — observe flag-on behavior across the safe branches before expanding scope (populated-DB upgrade, legacy stamp) in later slices.

## No-change decisions (P3.8-G)

- **No runtime/startup change; flag not acted on; `app.py` untouched; `migrate_schema()` runs first and stays authoritative now.**
- **No `alembic upgrade`, no `alembic stamp`, no PostgreSQL switch, no schema/model/accounting/API/UI change, no `Float → Decimal`.**
- **The first behavior slice is planned, not implemented** — helpers, wiring, and tests are future slices (P3.8-H/I/J/K).

---

*Plan only — no runtime change yet, flag not acted on, `migrate_schema()` runs first and stays authoritative now. First flag-gated behavior (future): flag off → unchanged migrate_schema; on+at_head → skip migrate_schema, verify_only; on+new empty DB → alembic upgrade head (verified-empty only); on+unstamped legacy → block with stamp instructions (no auto-upgrade, no auto-stamp); on+behind_head → block unless backup+confirmation exists; on+ahead_of_code/unknown → fail closed. Not included: production auto-upgrade of populated DB, automatic legacy stamp, migrate_schema removal, PostgreSQL switch, Float→Decimal. Helpers first: safe empty-DB detection, safe Alembic command wrapper, backup/confirmation gate, clear startup error type. Rollback = restore backup + disable flag + retained migrate_schema; never edit accounting tables manually. Sequence: P3.8-H wrapper → P3.8-I gate → P3.8-J wiring → P3.8-K bake-in.*
