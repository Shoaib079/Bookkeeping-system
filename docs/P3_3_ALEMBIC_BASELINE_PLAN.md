# P3.3 — Alembic Baseline Plan

**Mode:** Documentation + lightweight contract test only. **No migration revisions generated.** No `alembic revision`, no `alembic upgrade`, no model changes, no runtime DB / Streamlit / FastAPI changes, no PostgreSQL switch, no `Float → Decimal`. `migrate_schema()` **remains authoritative for now**.
**Goal:** define the safe baseline strategy before the first Alembic migration is ever created.
**Status:** **No migration has been generated yet.** This is planning only.

## 1. What "baseline" means for this ERP

Four populations must be reconciled by the baseline:

| Population | Today | Baseline expectation |
|-----------|-------|----------------------|
| **Current SQLAlchemy models** (`models.py` + `Base.metadata`) | source of truth for shape | revision `0001` must reproduce exactly this schema |
| **Existing SQLite DBs** already evolved by `migrate_schema()` | live user data, columns/indexes added incrementally | must be **stamped** at `0001` **without any destructive migration** (no table rebuild, no data loss) |
| **New SQLite DBs** created from `Base.metadata.create_all` | fresh dev/test DBs | may be created by `create_all` **or** by Alembic `upgrade head` (must be equivalent) |
| **Future PostgreSQL DBs** | none yet | created **through Alembic** from `0001` upward |

"Baseline" = a single revision `0001` whose target schema is **identical** to what `Base.metadata` + the cumulative `migrate_schema()` steps produce today, so existing SQLite DBs can be marked as already-at-`0001` and new/PG DBs can be built up to it.

## 2. Baseline strategy

- **Baseline the current schema as revision `0001`.** `0001` represents "the schema as it exists after all current `migrate_schema()` evolution" — the union of `Base.metadata` and the incremental columns/indexes/partial-index added at runtime today.
- **Existing SQLite users are stamped, not migrated.** They already have the `0001` schema (via `migrate_schema`), so they are marked at `0001` with `alembic stamp 0001` (records the version; runs **no** DDL). **No destructive migration**, no table rebuild, no data touch.
- **New PostgreSQL databases are created through Alembic** (`upgrade head` from `0001`), never via the SQLite-only `migrate_schema` path.
- **New SQLite dev/test DBs** continue to work via `Base.metadata.create_all` (fast path) and must be schema-equivalent to `upgrade head`; the baseline-validation plan (§6) guards this equivalence.

## 3. Cutover rules

- **`migrate_schema()` remains authoritative now.** It continues to run at Streamlit startup and own schema evolution until the cutover is explicitly approved. **It is not removed in P3.3.**
- **Alembic becomes authoritative only after** (a) `0001` is generated and reviewed, (b) baseline validation (§6) confirms parity with the live SQLite schema, and (c) existing DBs are stamped. Until then Alembic is dormant/planned.
- **Streamlit startup change is deferred:** the eventual change (run `alembic upgrade head` instead of / before `migrate_schema`) is a later, separate task — **not** in P3.3, and only after a green dual-path validation.
- **Test change is deferred:** tests keep using `Base.metadata.create_all` until the cutover; a later task may switch DB setup to Alembic for PG fixtures. No test setup changes in P3.3.
- **Authority handoff order:** generate `0001` → review → validate parity → stamp existing DBs → (separate task) flip startup to Alembic and retire `migrate_schema`. Each step is its own approved slice.

## 4. Migration generation rules

- **No blind autogenerate.** `alembic revision --autogenerate` is allowed **only after** a model/schema audit, and **every generated revision is manually reviewed** line-by-line before commit.
- **`0001` is reviewed against the live schema**, not accepted as-emitted — autogenerate is a starting draft, not the deliverable.
- **`Float → Decimal` is excluded** from baseline and from any autogenerate diff. If autogenerate proposes type changes for money columns, they are **rejected/stripped** — money stays `Float` until the separate, characterized NUMERIC project.
- **SQLite-only constructs are normalized** in the reviewed revision: the partial index predicate becomes `is_void IS FALSE` (not `= 0`), and PRAGMA/`sqlite_master`/raw-rebuild idioms are **not** carried into Alembic.
- **Data migrations require explicit backup + rollback notes** in the revision docstring (what is changed, how to restore) — schema-only revisions preferred; data moves are exceptional and reviewed.
- Revisions are **deterministic and ordered** (`0001` → `0002` → …); no squashing of already-released revisions.

## 5. Rollback strategy

- **Local SQLite:** take a file backup of `erp_data.db` (copy) **before** any `upgrade`; rollback = restore the file copy.
- **PostgreSQL:** `pg_dump` before any `upgrade`; rollback = restore the dump.
- **Downgrade limitations for accounting data:** schema downgrades that would drop columns/tables holding posted accounting data are **prohibited**; `downgrade()` for such revisions raises/`NotImplementedError` with a note to restore from backup instead.
- **Never delete accounting rows.** Consistent with the existing void-not-delete policy — no migration may delete `JournalEntry`/`JournalEntryLine`/`Sale`/`Purchase`/`Payable`/movement/allocation rows. Reversal/void is the only "undo."
- Every revision documents its **backup precondition** and whether a safe `downgrade` exists.

## 6. Baseline validation plan

Before stamping anything, validate `0001` against reality:

- **Compare `Base.metadata` to an existing `migrate_schema()`-evolved SQLite schema:** table-by-table, column-by-column (name, type, nullability), index-by-index, constraint-by-constraint.
- **Detect missing columns/indexes:** anything `migrate_schema` adds at runtime that isn't in `Base.metadata` must be reconciled into `0001` (so a fresh `create_all`/Alembic DB matches a long-lived migrated DB).
- **Detect SQLite-only constructs:** flag `PRAGMA`, `sqlite_master`, raw-rebuild, and the `WHERE is_void = 0` partial index; ensure the reviewed `0001` uses portable equivalents (`is_void IS FALSE`).
- **Verify Alembic version-table handling:** confirm `alembic_version` is created/managed correctly and that `stamp 0001` on an existing DB writes the version row **without** DDL.
- **Equivalence check:** a DB built via `upgrade head` and a DB built via `create_all` must yield the same schema (the future dual-engine/dual-path test target).

## No-change decisions (P3.3)

- **No migration generated** (no `0001` yet) — planning only.
- **`migrate_schema()` stays authoritative and active.**
- **No model changes; `Float` stays `Float`** (NUMERIC excluded).
- **No Streamlit/FastAPI/runtime DB change; no PostgreSQL switch.**
- **No Alembic install/scaffold executed** — documented strategy only.

## Recommended P3.4 tasks (next, when approved)

- **P3.4-A:** scaffold Alembic (env.py wired to `Base.metadata` + `DATABASE_URL`); no revisions yet.
- **P3.4-B:** generate `0001` via autogenerate, then **manually review/normalize** (partial index `IS FALSE`, exclude any Float→Decimal diff).
- **P3.4-C:** baseline-validation tooling (§6) comparing `create_all` vs migrated SQLite schema.
- **P3.4-D:** stamp procedure for existing SQLite DBs (`alembic stamp 0001`, backup-first).
- **P3.4-E (later, separate):** startup cutover (Alembic authoritative) + retire `migrate_schema`, after green validation.

---

*Planning only. No migration revisions generated, `migrate_schema()` remains authoritative, models/`Float` unchanged, no PostgreSQL switch. Baseline = current schema as `0001`; existing SQLite DBs are **stamped** (non-destructive), new/PG DBs built via Alembic; autogenerate only after audit with mandatory manual review; `Float → Decimal` excluded; data migrations require backup/rollback notes; accounting rows are never deleted.*
