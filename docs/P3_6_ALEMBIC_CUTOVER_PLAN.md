# P3.6 — Alembic Cutover Plan

**Mode:** Documentation + lightweight contract test only. **No runtime change in this slice.** `migrate_schema()` is **not removed, not disabled**; Streamlit/FastAPI startup unchanged; no `alembic upgrade`, no stamping, no PostgreSQL switch, no model/accounting/API/UI change.
**Status:** **No runtime change yet.** `migrate_schema()` **remains active and authoritative now.** Alembic becomes authoritative **only in a future, separately approved slice** (P3.7+).
**Context:** `0001` baseline exists; the local SQLite DB has been backed up and stamped to `0001`; full suite green; Streamlit starts; `migrate_schema()` still authoritative.

## 1. Current state

- `migrate_schema()` **still runs at startup and is authoritative** for schema evolution.
- Alembic version tracking exists (`alembic/versions/0001_baseline.py`); `alembic_version` is meaningful.
- The local `erp_data.db` is **stamped at `0001`** (non-destructive; `alembic_version` row only).
- Full `pytest` green; Streamlit starts successfully.

## 2. Cutover target

- **Alembic becomes authoritative** for schema migrations: startup runs `alembic upgrade head` (or verifies head) instead of relying on `migrate_schema()` to evolve the schema.
- **`migrate_schema()` becomes compatibility/legacy-only** — retained behind a flag and run only as a safety/no-op for not-yet-stamped DBs during a transition window, then disabled in a later slice. It is **not removed in P3.6** and not in the first cutover slice; removal is its own final step after a bake-in.
- The cutover is **gated** on: green suite, green baseline-equivalence, all target DBs stamped/backed up, explicit operator confirmation.

## 3. Startup behavior plan (target — not implemented here)

On startup, detect Alembic state via the `alembic_version` table and branch:

| DB state | Detection | Target behavior |
|----------|-----------|-----------------|
| **New / empty DB** | no app tables, no `alembic_version` | create schema via **Alembic `upgrade head`** (PG always; SQLite may keep `create_all`, equivalence-guarded) → ends at `0001` |
| **Existing stamped DB** | `alembic_version` == `0001` (current head) | **no migration runs** (already at head); start normally |
| **Existing stamped, behind head** | `alembic_version` < head | run `alembic upgrade head` **only after backup + operator confirmation** (see §4) |
| **Unstamped legacy DB** | app tables present, **no `alembic_version`** | **do NOT auto-upgrade.** Verify schema == `0001` (equivalence), back up, then `alembic stamp 0001` (operator-confirmed). If schema ≠ `0001`, **stop with a clear message** — do not guess |
| **Ahead of code head** | `alembic_version` > known heads | **fail fast** with a clear "DB newer than app" message; do not downgrade |

- **Failure messages** must be explicit and actionable: which DB, current `alembic_version`, expected head, and the required operator action (back up / stamp / upgrade / restore). Never silently mutate.

## 4. Safety rules

- **No destructive migrations** — schema-only, additive; no column/table drops of accounting data.
- **No automatic upgrade on user data without backup** — any `upgrade` that would run DDL on an existing populated DB requires a **backup first** and **explicit operator confirmation**; never silent on production data.
- **Never delete accounting rows** — consistent with the void-not-delete policy; migrations never delete `journal_entries`/`journal_entry_lines`/`sales`/`purchases`/`payables`/movements/allocations.
- **Backup before migration** — mandatory for any non-empty DB before any `upgrade`.
- **Explicit operator confirmation** for any future production schema change (no unattended upgrades in production).

## 5. Rollback strategy

- **Restore the backup** if a cutover/upgrade fails (stop app, replace the DB file / `pg_restore`).
- **Re-enable the `migrate_schema()` path** if the cutover fails — because it is retained (not removed), reverting the cutover flag restores the previous authoritative behavior with no schema change.
- **Never manually edit accounting tables** — recovery is restore-from-backup only.
- On `alembic_version` mismatch: restore the backup, re-verify equivalence, and re-stamp/upgrade on the restored copy — never hand-fix a live production `alembic_version`.

## 6. Test plan (for the future cutover slice)

- **Stamped DB startup** — `alembic_version == 0001`: startup runs no migration; app starts; suite green.
- **Unstamped legacy DB startup** — app tables, no `alembic_version`: startup does **not** auto-upgrade; verifies equivalence and surfaces the stamp instruction (or stamps under confirmation in a controlled test).
- **New empty DB startup** — Alembic `upgrade head` builds `0001`; schema equals `migrate_schema()`-evolved schema (equivalence).
- **Migration failure handling** — a forced failure leaves the DB unchanged / restorable; clear error surfaced; no partial destructive state.
- **Idempotency** — running startup twice on an at-head DB makes no changes; `migrate_schema()` (while retained) also remains a no-op on an at-head DB.

## 7. Future PostgreSQL path

- **New PostgreSQL DBs are created through Alembic** (`upgrade head` from `0001`) — never via `migrate_schema()`.
- **`migrate_schema()` never runs on PostgreSQL** (its raw SQLite DDL/PRAGMA is invalid there); it is SQLite-legacy-only and disabled for PG.
- **Optional dual-run parity before production** — compare an Alembic-built PG schema and the SQLite reference schema (and run the dual-run posting parity harness) before any production PG switch. No PostgreSQL runtime switch in this phase.

## No-change decisions (P3.6)

- **No runtime/startup change; `migrate_schema()` stays active and authoritative now.**
- **Alembic becomes authoritative only in a future approved slice** (P3.7+), not here.
- **No `alembic upgrade`, no stamping, no PostgreSQL switch, no model/accounting/API/UI change, no `Float → Decimal`.**

## Recommended next steps

- **P3.7 — startup detection (read-only):** add `alembic_version` detection + clear messaging **without** changing authority (log/observe only), behind a flag defaulting off.
- **P3.8 — flag-gated cutover:** flip authority to Alembic on opt-in (with backup + confirmation), `migrate_schema()` retained as legacy no-op; bake-in.
- **P3.9 — retire `migrate_schema()`** after a clean bake-in window.
- **PG enablement:** Alembic-only schema creation + dual-run parity before production.

---

*Planning only — no runtime/startup change, `migrate_schema()` active and authoritative now, Alembic authority deferred to a future approved slice. Target: startup detects `alembic_version` and branches (new → upgrade head; stamped-at-head → no-op; unstamped legacy → verify+backup+stamp under confirmation, never auto-upgrade; ahead-of-code → fail fast); no destructive migrations, backup + explicit confirmation before any upgrade on user data, never delete accounting rows; rollback = restore backup and re-enable the retained `migrate_schema()` path; PostgreSQL DBs created via Alembic only, with optional dual-run parity before production.*
