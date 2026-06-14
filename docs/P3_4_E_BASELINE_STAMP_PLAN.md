# P3.4-E — Alembic Baseline Acceptance & Stamp Plan

**Mode:** Documentation + lightweight contract test only. **No stamping performed.** No `alembic stamp`, no `alembic upgrade`, no touch of `erp_data.db`, no startup change, `migrate_schema()` not removed, no model/accounting/API/UI change.
**Status:** **No database has been stamped yet.** This defines the exact safe process to run **later**.
**Context:** `alembic/versions/0001_baseline.py` was authored in P3.4-D; its equivalence tests pass against the `migrate_schema()`-evolved schema; `migrate_schema()` remains authoritative.

## 1. Preconditions before stamping

All must be **true and verified** before any stamp:
- **Full `pytest` green** on the target commit.
- **Baseline-equivalence tests green** (`0001` schema == `migrate_schema()`-evolved schema: tables, columns, indexes, uniques, FKs).
- **Working tree clean** (`git status` shows no uncommitted changes).
- **DB backup created** (§2) and verified.
- **App closed — no Streamlit/FastAPI process running** against `erp_data.db` (no open SQLite handles).
- **Current DB schema verified equivalent** to `0001` / `migrate_schema()` (§3).
- **Migration file committed and tagged** (`0001_baseline.py` in version control at a known tag).

## 2. Backup procedure

- **Copy `erp_data.db` to a timestamped backup** before anything, e.g. `erp_data.db.bak-YYYYMMDD_HHMMSS` (file copy; no DB tool needed).
- **Optionally verify the backup opens** (e.g. open read-only and read `sqlite_master`/a row count) to confirm it is not truncated.
- **Never delete the backup during this phase** — it is the sole rollback artifact for §6.
- Backups are data; they are never edited.

## 3. Dry-run / verification procedure (read-only)

- **Inspect current DB tables/indexes** (read-only) and confirm they match `0001` (tables, columns, indexes, uniques, FKs) — reuse the baseline-equivalence comparison.
- **Verify no pending destructive DDL** — `0001` is create-only; stamping issues **no** DDL, so there is nothing to apply. Confirm there is no `upgrade`/`downgrade` step that would run.
- **Verify the `alembic_version` table is absent or safe** — for a never-stamped DB it should be **absent**; if present, confirm it is empty or already at `0001` (do not overwrite a higher revision).
- **Verify `0001` is the current head** (`alembic heads` shows `0001`, no later revisions).

## 4. Stamp procedure (to run later — not now)

- Command to run **later**, once §1–§3 pass:
  ```
  alembic stamp 0001
  ```
- **`alembic stamp 0001` writes only the `alembic_version` row** (records the version) — it issues **no schema DDL**, creates/alters/drops **no** tables/columns/indexes, and touches **no** accounting data.
- **Do not run `alembic upgrade`.** The existing DB already has the `0001` schema via `migrate_schema()`; running `upgrade` would attempt DDL and is forbidden here.

## 5. Post-stamp verification

- **Inspect `alembic_version`** — confirm exactly one row, value `0001`.
- **Rerun `pytest`** — full suite stays green.
- **Open Streamlit locally** — app starts and reads/writes normally.
- **Confirm `migrate_schema()` remains safe/idempotent** — it still runs at startup and makes no changes on an already-current DB (its `ALTER ... ADD COLUMN` steps roll back as no-ops; `CREATE ... IF NOT EXISTS` are no-ops). Stamping does not disable it.

## 6. Rollback procedure

- **If anything is wrong, restore the backup:** stop the app, replace `erp_data.db` with the timestamped backup from §2.
- **Remove the failed copy** (the post-stamp `erp_data.db`) only after the backup is restored and verified.
- **Do not manually edit accounting tables** — never hand-edit `journal_entries`, `journal_entry_lines`, `sales`, `purchases`, `payables`, movements, allocations, etc. Recovery is restore-from-backup only (consistent with the never-delete-accounting-rows policy).
- **If an `alembic_version` mismatch occurs** (e.g. wrong/extra revision, or a value other than `0001`): do **not** run `upgrade`/`downgrade` to "fix" it. Restore the backup, re-verify §1–§3, and re-stamp. The `alembic_version` table may be safely removed/reset **only on a restored backup**, never on a live production DB with an unknown state.

## 7. Cutover boundary

- **Stamping does NOT make Alembic authoritative.** It only records that the DB is at `0001`.
- **`migrate_schema()` remains active and authoritative** until a **separate P3.5/P3.6 cutover** task explicitly flips startup to Alembic and (later) retires `migrate_schema()`.
- **No PostgreSQL runtime switch** in this phase — still SQLite.
- **No `Float → Decimal`** — out of scope.

## 8. Operator checklist (for Shoaib, to run later)

1. `git status` → clean; on the tagged commit containing `0001_baseline.py`.
2. Run `pytest` → all green.
3. Run the baseline-equivalence tests → green.
4. **Close the app** (no Streamlit/FastAPI process touching `erp_data.db`).
5. **Back up:** copy `erp_data.db` → `erp_data.db.bak-YYYYMMDD_HHMMSS`; verify it opens.
6. **Dry-run/verify (read-only):** schema matches `0001`; `alembic_version` absent or safe; `alembic heads` == `0001`.
7. **Stamp:** `alembic stamp 0001` (writes `alembic_version` only — no DDL, no data touch).
8. **Verify:** `alembic_version` has one row `0001`; rerun `pytest`; open Streamlit; confirm `migrate_schema()` still no-ops.
9. **Keep the backup.** If anything failed: restore the backup, remove the failed copy, do **not** edit accounting tables.
10. Note: `migrate_schema()` stays authoritative; Alembic authority is a later, separate cutover.

## No-change decisions (P3.4-E)

- **No stamp run, no `alembic` command executed, `erp_data.db` untouched.**
- **`migrate_schema()` stays authoritative and active.**
- **No startup / model / accounting / API / UI change; no PostgreSQL switch; no `Float → Decimal`.**

---

*Planning only — no DB stamped, no alembic command run, `erp_data.db` untouched, `migrate_schema()` authoritative. Later process: verify preconditions (green suite + equivalence + clean tree + backup + app closed) → back up `erp_data.db` → read-only dry-run → `alembic stamp 0001` (writes `alembic_version` only, no DDL, no data touch) → verify (one `0001` row, green suite, app opens, migrate_schema still idempotent) → rollback = restore backup, never hand-edit accounting tables. Stamping is not the cutover; `migrate_schema()` stays authoritative until a separate P3.5/P3.6.*
