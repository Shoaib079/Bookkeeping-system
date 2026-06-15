# P3.9 — migrate_schema() Retirement Plan

**Mode:** Documentation + lightweight contract test only. **No runtime change in this slice.** `migrate_schema()` is **not removed, not deprecated, not disabled**; `app.py` is unchanged; the default flag behavior is unchanged (flag **off** by default → `migrate_schema()` authoritative); no `alembic upgrade`/`stamp`, no schema/model/accounting/API/UI change.
**Status:** **No retirement performed.** This defines the **safe, phased retirement path** to be executed **later**, only after the P3.8-L bake-in gate passes.
**Context:** P3.8-K2 wired the authoritative schema step behind `ERP_ALEMBIC_AUTHORITATIVE` (off by default); P3.8-L defined the bake-in/acceptance criteria. Retirement is the final step **after** that bake-in is complete and clean.

## 1. Current state

- **`migrate_schema()` retained** — still the authoritative schema-evolution path and the rollback target; not removed or deprecated.
- **Flag default off** — `ERP_ALEMBIC_AUTHORITATIVE` unset/`0` → startup uses `migrate_schema()` exactly as today.
- **Flag-on path operational** — `=1` enables the P3.8-K2 Alembic path (`verify_only` at head, `alembic upgrade head` for a strict-new empty DB, block/fail-closed for unsafe states).
- **Rollback available** — disabling the flag (`=0`/unset) reverts to the `migrate_schema()` path with no schema change.

## 2. Retirement prerequisites

**All** must be true and recorded before **any** retirement phase begins:

- **Bake-in completed** — the P3.8-L bake-in window finished with no do-not-proceed criterion triggered.
- **Smoke tests passed** — the optional P3.8-M local flag-on smoke (throwaway DB) passed and is documented.
- **All production DBs stamped** — every production/target database is `alembic stamp`-ed at a known revision (no DB relies on `migrate_schema()` to evolve).
- **No unstamped legacy DBs remain** — no known database is in the unstamped-legacy state.
- **Schema equivalence proven** — the Alembic-built/verified schema equals the `migrate_schema()`-evolved schema (tables, columns, indexes, uniques, FKs).
- **Rollback tested** — disabling the flag has been verified to restore a normal start with no schema change.

## 3. Retirement sequence

Phased, each phase a separate reviewed slice; **not started here**:

### Phase A — stop calling `migrate_schema()` at startup
- Make the flag-on (Alembic) path the **default** startup behavior; **stop invoking `migrate_schema()` at startup**.
- **Keep the function in the codebase** (callable, tested) as a safety net and for emergency manual use.
- Reversible: re-enabling the call (or flipping the default back) restores the prior path.

### Phase B — deprecate the function
- Mark `migrate_schema()` **deprecated**; **emit a deprecation warning if it is called**.
- Keep it functional for one or more releases so any out-of-band caller is surfaced via the warning before removal.
- Update docs to point all schema evolution at Alembic.

### Phase C — remove the implementation
- **Remove the `migrate_schema()` implementation in a future major release**, only after Phase B has run with no warnings observed in practice.
- Removal is the final, irreversible step and is gated on a clean Phase B.

## 4. Safety rules

- **Never delete accounting data** — no retirement phase deletes `journal_entries`, `journal_entry_lines`, `sales`, `purchases`, `payables`, movements, allocations, etc. (consistent with the void-not-delete policy).
- **Backup before migration** — any phase that would run DDL on a populated DB requires a verified backup first.
- **Fail closed on schema mismatch** — if the Alembic schema and the expected schema diverge at any phase, **stop** (do not proceed, do not silently fall back); resolve the mismatch before continuing.
- **No destructive migrations**, and no auto-upgrade of a populated DB without backup + operator confirmation.

## 5. PostgreSQL future

- **PostgreSQL never uses `migrate_schema()`** — its SQLite-only DDL/PRAGMA is invalid there; PG schema is **Alembic-only** (`upgrade head` from baseline).
- **Alembic-only path on PG** — new PG databases are created and evolved exclusively through Alembic; optional dual-run parity precedes any production PG switch. Out of scope for this slice.

## No-change decisions (P3.9)

- **No runtime change; `migrate_schema()` not removed/deprecated/disabled; `app.py` untouched; flag default unchanged (off → `migrate_schema()`).**
- **No `alembic upgrade`/`stamp`, no PostgreSQL switch, no schema/model/accounting/API/UI change, no `Float → Decimal`.**
- **The retirement is planned, not executed** — Phases A/B/C are future, separately-approved slices gated on the §2 prerequisites.

---

*Plan only — no retirement performed, `migrate_schema()` retained, `app.py` untouched, flag default off (→ migrate_schema). Defines the safe phased retirement after the P3.8-L bake-in: prerequisites (bake-in completed, smoke tests passed, all production DBs stamped, no unstamped legacy DBs, schema equivalence proven, rollback tested), then Phase A (stop calling migrate_schema at startup, keep the function), Phase B (deprecate + warn if used), Phase C (remove implementation in a future major release). Safety: never delete accounting data, backup before migration, fail closed on schema mismatch. PostgreSQL never uses migrate_schema — Alembic-only path.*
