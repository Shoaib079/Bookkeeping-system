# P3.8-L-BAKEIN — Alembic Authority Bake-In Audit

**Mode:** Audit only. **No implementation, no feature-flag change, no runtime DB switch, no schema change, no Alembic change.** Determines exactly what remains to fully bake in Alembic authority and retire `migrate_schema()` as the authoritative schema path (P4.2 blocker #1).

## Verdict — **NOT READY to retire `migrate_schema()`; machinery is COMPLETE and wired**

The flag-gated authority machinery is **fully implemented and wired** (P3.8-K2): `prepare_schema_startup_authoritative()` runs pre-session and `run_schema_startup_in_session()` runs the in-session step. What remains is **operational bake-in execution** (running flag-on across real DB states for a window), an **equivalence confirmation**, a **default-flip decision**, and a **separate retirement slice (P3.9)**. So: *ready to bake in*, **not yet ready to retire**.

## 1. Exact startup flow (boot → session → schema)

`app.py` `main()`:
1. `os.chdir(PROJECT_ROOT)`; `_phase14a_milestone_backup()`; `_phase14a_rebuild_tables()`.
2. **Pre-session:** `prepare_schema_startup_authoritative()` (`app.py:26465-26467`) → detect → decide → gate → optional Alembic subprocess; caches a `SchemaStartupSessionPlan`.
3. **Boot session:** `with get_session() as _boot_session: _run_schema_startup(_boot_session)` → `run_schema_startup_in_session(session, migrate_schema_fn=migrate_schema, …)` (`app.py:26447-26449`).
4. Seeds/migrations run afterward, unchanged.

## 2. Decision matrix — flag OFF vs ON

**Flag OFF (`ERP_ALEMBIC_AUTHORITATIVE` unset/0) — today's default:**
- `prepare_…` returns `plan(flag_authoritative=False, skip_migrate_schema=False)`.
- `run_schema_startup_in_session` → **`migrate_schema_fn(session)` then diagnostics.** `migrate_schema()` is authoritative. ✅ unchanged.

**Flag ON (`=1`) — future, opt-in:**
| DB state | Pre-session action | In-session |
|---|---|---|
| **at_head** | `verify_only` → `skip_migrate_schema=True` | `migrate_schema` **skipped**; diagnostics only |
| **new / empty DB** | gate (strict-new) → `run_upgrade_head` subprocess → `skip_migrate_schema=True` | `migrate_schema` **skipped** |
| **unstamped legacy** | `require_stamp` → **`SchemaStartupError` (block)** | — |
| **behind_head (populated)** | gate must pass; **K2 never auto-upgrades** → block | — |
| **ahead_of_code / unknown** | `fail_closed` → **block** | — |

So **when flag-on resolves to `verify_only`/`new`, `migrate_schema()` is already a no-op for that run** — the retirement behavior already exists behind the flag.

## 3. Remaining callers of `migrate_schema()`

- **Exactly one runtime caller:** `run_schema_startup_in_session(... migrate_schema_fn=migrate_schema ...)` (`app.py:26447`). All other matches are docstrings/messages, not calls.
- **Implication:** retirement is clean — a single call site, already behind the flag. No scattered callers to chase.

## 4. SQLite-only logic inside `migrate_schema()`

Confirmed SQLite-specific idioms (invalid on PostgreSQL):
- Raw `_sqlite3.connect(dst)` backup (`app.py:~1785`).
- `ALTER TABLE … ADD COLUMN` (single-column) and `ALTER TABLE … RENAME COLUMN` with `session.rollback()` on duplicate-column.
- `CREATE INDEX IF NOT EXISTS`, partial `WHERE is_void = 0` predicates, `PRAGMA`/`sqlite_master` usage (per P3.1 R1/R3).

**→ `migrate_schema()` must never run on PostgreSQL** (it would error / partially apply). The wiring already guarantees this: flag-on never returns `run_migrate_schema`.

## 5. P3.8 tests currently covering authority

Present: `test_p3_8_c` (flag parser), `_d/_e` (decision plan + pure function), `_f` (diagnostics), `_g` (behavior plan), `_h` (Alembic runner), `_i` (migration gate), `_j/_k0/_k1` (wiring plan + conflict resolution + helper hardening), **`_k2` (startup wiring)**, **`_l` (bake-in review plan)**, **`_m` (local smoke test)**, plus `schema_startup_diagnostics`. The decision/runner/gate/wiring layers are unit-covered.

## 6. Missing characterization tests (for full bake-in)

- **End-to-end flag-ON startup on a real SQLite DB across all states:** stamped→`verify_only`+app starts+`migrate_schema` not called; new-empty→upgrade builds `0001`; unstamped-legacy→blocks; behind_head→blocks; ahead→fail_closed. (K2 covers decisions; a real-DB end-to-end pass per state strengthens bake-in; P3.8-M is the seed.)
- **Schema-equivalence gate (the crux of retirement):** a DB built by `alembic upgrade head` (`0001`) has the **identical** schema to one evolved by `migrate_schema()` — tables/columns/indexes/uniques/FKs (extends the P3.4-D baseline equivalence). Retiring `migrate_schema()` is only safe once this is asserted continuously.
- **Single-caller guard:** a static test that `migrate_schema` has exactly one runtime call site (the wiring), so a future caller can't reintroduce it.
- **`migrate_schema` never runs on PostgreSQL:** assert that on a PG dialect, the resolved plan never calls `migrate_schema_fn` (PG-safety invariant).
- **Lock-safety:** subprocess upgrade runs before the boot session opens (no `database is locked`) — confirm a regression test exists (K0/K1 territory).
- **Flag-off parity:** with the flag off, `migrate_schema` then diagnostics run in the exact prior order (no drift).

## 7. What "bake-in" actually means

Bake-in = running with **`ERP_ALEMBIC_AUTHORITATIVE=1`** in real use over a **defined window**, across the real DB states, and observing: the app **starts** (verify_only / new-empty), **no schema drift** vs the `migrate_schema`-equivalent baseline, **no data loss**, **rollback works** (flag off restores `migrate_schema`), and **logs are clean** — per the P3.8-L plan. It is the **operational confidence-gathering** that justifies flipping the default and then retiring `migrate_schema()`. It is *not* a code change; it is evidence collection against the already-built machinery.

## 8. Rollback if authority is enabled

- **Disable the flag** (`ERP_ALEMBIC_AUTHORITATIVE=0`/unset) → `prepare_…` returns `flag_authoritative=False` → **`migrate_schema()` runs again** (retained) → prior behavior restored with **no schema change**. The `SchemaStartupError` messages already instruct: *"Disable ERP_ALEMBIC_AUTHORITATIVE to fall back to migrate_schema()."*
- **Restore from backup** only if an upgrade mutated a populated DB and misbehaved; never hand-edit accounting tables.

## 9. PostgreSQL implications if `migrate_schema()` accidentally runs

- Its raw `sqlite3` / `ALTER … ADD COLUMN` / `PRAGMA` / partial-index idioms are **invalid on PG** → errors or partial application → corrupt/blocked startup.
- The wiring **prevents** this: flag-on never returns `run_migrate_schema`; PG must run **flag-on only** (flag-off on PG would attempt the invalid `migrate_schema`). The §6 "never on PG" test pins this invariant before any PG runtime.

## 10. Required implementation slices (sequenced — NOT in this audit)

1. **P3.8-L-EXEC — bake-in execution:** run flag-on across the real DB states for the defined window; record the §7 observations (operational, not code).
2. **P3.8-L-TESTS — add §6 characterization tests:** end-to-end per-state startup, schema-equivalence gate, single-caller guard, never-on-PG, lock-safety, flag-off parity.
3. **P3.8-N — default flip:** change the flag default to **on** once bake-in is clean and all target DBs are stamped at head; `migrate_schema()` retained as the flag-off legacy fallback.
4. **P3.9 — retire `migrate_schema()`:** make it a no-op / remove the implementation after a clean bake-in window, no legacy unstamped DBs, and (for PG) parity proven.

## Rollback plan (for the bake-in / flip)

- **Flag-off** returns to the retained `migrate_schema()` path instantly (no schema change).
- **Keep `migrate_schema()` retained** through P3.8-N and only delete in P3.9 after bake-in.
- **Restore from backup** for any mutated populated DB; **never hand-edit accounting tables**.

## ROADMAP update recommendation

- Record **P3.8-L = machinery complete, bake-in not yet executed**; retirement gated on the §6 tests + the §7 bake-in observations + all DBs stamped at head.
- State the **exact retirement condition** (below) and sequence P3.8-L-EXEC → P3.8-L-TESTS → P3.8-N (default flip) → P3.9 (retire).
- Cross-link to **P4.2** (this is its blocker #1) and to **MD-05** (NUMERIC must also land before PG production).

## Required conclusion — exact condition for `migrate_schema()` → legacy/no-op and Alembic authoritative

> **`migrate_schema()` becomes legacy/no-op and Alembic becomes authoritative when, and only when, ALL hold:**
> 1. **`ERP_ALEMBIC_AUTHORITATIVE` default is flipped to on (P3.8-N)** — until then it is opt-in and `migrate_schema()` stays authoritative on flag-off.
> 2. **The P3.8-L bake-in completed clean:** flag-on starts the app on every real DB state, with **no schema drift**, **no data loss**, clean logs, over the defined window.
> 3. **Schema equivalence is asserted continuously:** the Alembic-built (`0001`) schema == the `migrate_schema()`-evolved schema (tables/columns/indexes/uniques/FKs).
> 4. **Every target DB is stamped at head** (no unstamped-legacy DB depends on `migrate_schema()` to evolve).
> 5. **Rollback is proven:** flag-off restores the `migrate_schema()` path with no schema change.
>
> At that point `migrate_schema()` is retained only as the flag-off legacy fallback; **its implementation is removed in P3.9** after a clean bake-in window and (for PostgreSQL) only via Alembic with parity proven — `migrate_schema()` **never** runs on PostgreSQL.

## Test run note

This audit changes no code; the `test_p3_8_*` suite and full suite remain as they are. pytest cannot run in this sandbox (no `sqlalchemy`); run locally. This audit adds only a doc + a pure-stdlib doc-contract test.

## No-change statement (P3.8-L-BAKEIN audit)

- **No implementation, no feature-flag change, no runtime DB switch, no schema change, no Alembic change, no `app.py`/`services` edit.** Verdict + flow + decision matrix + callers + SQLite-only findings + test gaps + bake-in definition + rollback + PG implications + slices + exact retirement condition + ROADMAP recommendation only.

---

*Audit only. Machinery is **complete and wired** (P3.8-K2): `prepare_schema_startup_authoritative()` (pre-session) + `run_schema_startup_in_session()` (in-session); flag-off runs `migrate_schema()` then diagnostics; flag-on branches (at_head→verify_only/skip; new-empty→gate+upgrade/skip; unstamped/behind/ahead→block). The **only runtime caller** of `migrate_schema()` is the wiring's injected `migrate_schema_fn`, and its body is SQLite-only (raw sqlite3, ALTER ADD COLUMN, PRAGMA, partial index) — invalid on PG. Verdict: ready to bake in, **not yet ready to retire**. Remaining: P3.8-L bake-in execution (flag-on across real DB states, no drift/loss, clean logs, rollback proven) + §6 characterization tests (per-state e2e, schema-equivalence gate, single-caller guard, never-on-PG, lock-safety, flag-off parity) + P3.8-N default flip + P3.9 retirement. Rollback = flag-off restores migrate_schema (retained, no schema change). Exact condition: default flipped on (P3.8-N) AND bake-in clean AND equivalence asserted AND all DBs stamped AND rollback proven → migrate_schema legacy/no-op, removed in P3.9; never runs on PostgreSQL.*
