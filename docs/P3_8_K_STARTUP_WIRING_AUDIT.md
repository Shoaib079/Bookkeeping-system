# P3.8-K — Startup Wiring Pre-Implementation Audit

**Mode:** Audit only. No implementation, no runtime change, no code/test modifications. `migrate_schema()` remains authoritative; nothing in this document is wired.
**Reviewed:** `services/schema_startup.py` (P3.8-E decision + P3.8-F diagnostics), `services/alembic_runner.py` (P3.8-H), `services/schema_migration_gate.py` (P3.8-I), `services/schema_version.py` (P3.7), `docs/P3_8_J_STARTUP_WIRING_PLAN.md`, and the live startup flow in `app.py`.
**Headline:** the components are individually sound, but wiring them as P3.8-J describes hits **two real integration conflicts** (the runner refuses the production DB; the gate and the decision function disagree on a new empty `erp_data.db`) and **one SQLite concurrency hazard** (subprocess upgrade vs. an open boot-session connection). These must be resolved in design **before** P3.8-K writes any code.

## 1. Exact insertion point in app.py

Current startup (verified, `app.py` `def main()`):

```
26297    with get_session() as _boot_session:
26298        migrate_schema(_boot_session)                  # ← authoritative schema evolution
26299        _log_schema_startup_diagnostic(_boot_session)  # ← P3.8-A/F read-only diagnostics
26300        initialize_chart_of_accounts(_boot_session)
26301        migrate_sales(_boot_session)
             ... seeds/data migrations unchanged ...
26316        sync_account_balances(_boot_session)
```

- `_log_schema_startup_diagnostic` (line 26281) **already calls** `log_schema_startup_decision_diagnostics(session)` — i.e. the decision is **already built and logged read-only today** (P3.8-F), but never enforced.
- **Insertion point:** replace **lines 26298–26299 only** with a single dispatcher `_run_schema_startup(_boot_session)`. Lines 26300+ (seeds) stay byte-for-byte.
- **Important nuance:** the safe upgrade path runs Alembic in a **subprocess** that opens its own connection to the same SQLite file. It therefore **cannot run inside** the `with get_session()` block without a lock hazard (§5). The dispatcher should perform **read-only detection + decision first**, and any **subprocess upgrade must happen before the boot session is opened** (or with the boot connection fully released). This means the real insertion is likely **two-staged**: (a) a pre-session `_resolve_schema_authority()` that may run the subprocess upgrade/verify/stamp-or-block, then (b) the existing `with get_session()` block whose first line becomes flag-aware (flag-off → `migrate_schema`; flag-on → skip).

## 2. Startup sequence diagram

```
main()
  os.chdir(PROJECT_ROOT)
  _phase14a_milestone_backup()
  _phase14a_rebuild_tables()        # raw sqlite3 DDL (chart_of_accounts, products)
  │
  ├─ FLAG OFF (ERP_ALEMBIC_AUTHORITATIVE unset/0)  ── default, unchanged ──
  │     with get_session() as s:
  │        migrate_schema(s)                 # authoritative (as today)
  │        _log_schema_startup_diagnostic(s) # read-only decision log (P3.8-F)
  │        <seeds…>
  │
  └─ FLAG ON (=1)  ── future P3.8-K target ──
        [pre-session, read-only]
          info = detect_schema_version(engine)             # P3.7
          is_new = infer_is_new_database(engine)           # journal_entries absent?
          decision = decide_schema_startup_action(...)      # P3.8-E (pure)
            ├─ at_head            → verify_only ───────────────┐
            ├─ new empty DB       → alembic_upgrade_head        │
            ├─ unstamped legacy   → require_stamp (block unless ready)
            ├─ behind_head        → upgrade (block unless ready)
            └─ ahead/unknown/PG   → fail_closed (block)         │
          if decision.requires_backup/confirmation:            │
            gate = evaluate_migration_gate(...)  # P3.8-I       │
            if not gate.allowed: raise StartupError (BLOCK)     │
          if action == upgrade_head:                            │
            run_upgrade_head(url, allow_execute=True, …)  # P3.8-H subprocess
            if not result.success: raise StartupError (BLOCK)   │
        [then] with get_session() as s:  ←─────────────────────┘
          # migrate_schema SKIPPED when flag on
          _log_schema_startup_diagnostic(s)  # still logs
          <seeds…>   # unchanged
```

## 3. Risk analysis

| # | Risk | Severity | Evidence | Mitigation for P3.8-K design |
|---|------|----------|----------|------------------------------|
| **R1** | **Runner refuses the real startup DB.** `DATABASE_URL = sqlite:///…/erp_data.db`; `alembic_runner._PRODUCTION_DB_MARKERS` contains `"erp_data.db"`, so `is_allowed_database_url()` → `False` and `build_*`/`run_*` raise `ValueError` unless `allow_production=True`. The only real startup DB is exactly the path the runner blocks. | **High / blocker** | `alembic_runner.py:25-31,50-75,152,166`; `paths.py:10-11` | Wiring must pass `allow_production=True` **consciously and only after the gate passes**, OR introduce an explicit "startup-authorized" flag distinct from the dev guard. Decide deliberately; do not silently flip `allow_production`. |
| **R2** | **Gate vs decision disagree on a new empty `erp_data.db`.** Decision (P3.8-E) for `is_new_db` returns `alembic_upgrade_head` with `requires_backup=False, requires_confirmation=False`. Gate (P3.8-I) for `upgrade_head` + `not populated` + **production path** returns `needs_backup=True, needs_confirmation=True`. Same scenario, opposite verdicts. | **High** | `schema_startup.py:172-187`; `schema_migration_gate.py:123-126,142-145` | Define **one authority order** in P3.8-K: e.g. decision proposes, gate is the hard stop. For a brand-new empty file the gate will demand a backup of a DB that doesn't exist yet — reconcile (treat truly-empty-nonexistent file as exempt, or relax the production marker for a zero-table DB). Pin the chosen rule in tests. |
| **R3** | **`is_new_db` may never be true at the wiring point.** `infer_is_new_database` keys off the `journal_entries` table. But `_phase14a_rebuild_tables()` runs **before** the boot block and creates tables; if any path has already created `journal_entries` (or a prior `migrate_schema`/`create_all` ran), detection returns `False` and the new-empty branch is dead. | **Medium** | `app.py:26294` (pre-session DDL) vs `schema_startup.py:393-408` | Verify the true table-creation ordering on a clean checkout; ensure detection runs **before** any table creation, or base "new DB" on absence of `alembic_version` **and** zero app tables. |
| **R4** | **Lexicographic revision comparison.** `_classify_revision` uses `db_revision > head_revision` (string compare) for ahead-of-code. Fine for `"0001"`, but non-zero-padded or hash revisions will misorder. | **Low (now), Medium (later)** | `schema_version.py:130` | Document single-head/zero-padded constraint; revisit when a second revision lands. |
| **R5** | **Unreachable PostgreSQL guard.** The `dialect == "postgresql"` fail-closed in the decision function sits **after** all known-status branches (`at_head`/`unstamped`/`behind_head` all return earlier), so it never executes for a known status. Not harmful (flag-on never returns `run_migrate_schema`, so PG never reaches `migrate_schema` anyway), but the guard is dead and misleading. | **Low** | `schema_startup.py:189-268` | Either remove the dead branch or move the PG check earlier; note that PG-safety actually holds structurally, not via this branch. |
| **R6** | **Second connection during boot.** Detection opens a **new** connection from the bind (`bind.connect()`) separate from the session's. Read-only and closed in `finally`, but adds connections during the boot window. | **Low** | `schema_version.py:102-105,187-193`; `schema_startup.py:411-414` | Acceptable for reads; ensure all are closed before the subprocess upgrade (§5). |

## 4. Commit ownership concerns

- **Boot session does not auto-commit.** `get_session()` returns a bare `SessionLocal()` (`autocommit=False`), and `with get_session() as s:` calls `Session.__exit__` → **`close()`, not `commit()`**. Today every startup function commits internally (SQLite also auto-commits DDL). The flag-off dispatcher branch **must preserve this exactly** — call `migrate_schema(s)` then `_log_schema_startup_diagnostic(s)` in the same order, same session.
- **Subprocess upgrade commits out-of-band.** `run_upgrade_head(allow_execute=True)` runs `python -m alembic upgrade head` in a **separate process** with its **own engine, transaction, and commit** against the same `erp_data.db`. The boot session has **no ownership** of that commit. This is an intentional but real **commit-ownership split**: schema is committed by the subprocess; data seeds are committed (internally) by the in-process session afterward.
- **Ordering requirement:** the subprocess must finish and commit **before** the in-process boot session runs seeds, otherwise seeds may run against a not-yet-migrated schema. The dispatcher must treat a non-success runner result as fail-closed and **not** proceed to seeds.
- **No partial-commit recovery in-process.** If the subprocess half-applies and exits non-zero, the in-process code cannot roll it back (different transaction/process). Recovery is restore-from-backup (consistent with P3.8-J rollback), which is why the gate's backup requirement matters for any populated DB.

## 5. Session lifecycle concerns

- **SQLite single-writer / lock hazard.** If the dispatcher runs the Alembic **subprocess while `_boot_session` (or detection's extra connection) holds an open transaction/connection** to `erp_data.db`, the subprocess can hit `database is locked`. **Mitigation:** run detection read-only and **close every connection**, run the subprocess upgrade **before** opening the boot session, then open the boot session for seeds. The current P3.8-J sketch places the branch *inside* `with get_session()` — that is unsafe for the subprocess action and should be restructured (§1).
- **`check_same_thread=False`** is set (`db.py:10`), so Streamlit's threading is fine; the subprocess is a separate process and unaffected by the connect-listener `PRAGMA` (dialect-guarded).
- **Connection cleanup is correct in the helpers** (`owns_connection` close in `finally`), so read-only detection won't leak — but the *timing* relative to the subprocess is the concern, not leakage.
- **`engine.dispose()`** in the runner's read path (`alembic_runner.py:125`) is good; the upgrade subprocess path does not touch the in-process engine at all.

## 6. Failure-mode analysis

| Failure | Current component behavior | Required wiring behavior (P3.8-K) |
|---------|----------------------------|-----------------------------------|
| Runner refuses production URL (R1) | `ValueError` raised | Catch → structured `StartupError` with clear operator message; **block**, do not fall back to `migrate_schema` |
| Subprocess `upgrade` exits non-zero | `AlembicCommandResult.success=False` (+ stderr) | Treat as **fail-closed**; block startup; surface stderr; restore-from-backup guidance |
| `alembic`/`alembic.ini` missing | subprocess error / non-zero | Clear "Alembic not available" message; block |
| Gate returns `allowed=False` | `MigrationGateDecision.allowed=False` (+ reason) | **Block** with the gate message; **no silent fallback** to `migrate_schema` (per P3.8-J) |
| Decision `blocks_startup=True` (require_stamp not ready / fail_closed) | pure flags only | Raise `StartupError`; print required operator action (back up / stamp / restore) |
| Partial upgrade on empty DB, then restart | `is_new_db` may now read `False` (some tables exist) → misclassify (R3) | Base "new" on `alembic_version` absence **and** zero app tables; otherwise route to fail_closed |
| SQLite locked during subprocess (§5) | subprocess error | Sequence so no in-process connection is open during upgrade; retry/clear message |
| Flag on, `at_head` | decision `verify_only`, no DDL | Skip `migrate_schema`; optionally assert schema present; continue to seeds |

## 7. Test matrix additions (beyond P3.8-J's list)

Integration / hazard tests that the current per-component unit tests do **not** cover:

1. **Production-marker reconciliation (R1):** with `DATABASE_URL` pointing at an `erp_data.db`-named temp file, assert the wiring's chosen `allow_production` policy is explicit and that a flag-on upgrade is either authorized-after-gate or blocked — never an unhandled `ValueError`.
2. **Gate-vs-decision new-empty-DB conflict (R2):** new empty file named `erp_data.db` → pin which authority wins and the exact resulting action (one canonical expected outcome).
3. **SQLite lock safety (§5):** simulate an open boot-session connection, then invoke the upgrade path → assert no `database is locked`; assert the dispatcher closes connections before the subprocess.
4. **Subprocess-failure fail-closed:** force a non-zero Alembic exit → assert startup blocks and `migrate_schema` is **not** called.
5. **No silent fallback when flag on:** gate-blocked / decision-blocked → assert `migrate_schema` is not invoked.
6. **`is_new_db` ordering (R3):** on a clean checkout, assert detection runs before any table creation (or that "new" requires both no `alembic_version` and zero app tables).
7. **Flag-off byte-for-byte parity:** assert the dispatcher's flag-off branch calls `migrate_schema(s)` then `_log_schema_startup_diagnostic(s)` in that order, same session — no behavioral drift.
8. **No raw Alembic in `app.py` (static):** assert `app.py` contains no direct `alembic upgrade`/`stamp` strings; Alembic only via `services.alembic_runner`.
9. **Commit-ownership boundary:** assert seeds run only after a successful subprocess upgrade (no seed-before-migrate ordering).

## Recommended pre-P3.8-K resolutions

1. **Decide the `allow_production` policy** for startup (R1) — likely a dedicated "startup-authorized" path, gated by P3.8-I, distinct from the dev guard.
2. **Pin the authority order** decision-proposes / gate-decides and **reconcile the new-empty-`erp_data.db` case** (R2).
3. **Restructure the insertion** so the subprocess upgrade runs **outside/before** the boot-session connection (§1, §5).
4. **Harden `is_new_db`** to require `alembic_version` absence + zero app tables (R3).
5. Optionally clean up the **dead PG branch** (R5).

## No-change statement (P3.8-K audit)

- **No code or tests modified; no wiring implemented; `migrate_schema()` remains authoritative and runs first.**
- This is an audit of existing P3.8-E/F/H/I artifacts and the live `app.py` flow only.

---

*Audit only. Insertion = replace app.py lines 26298–26299 with a flag-aware dispatcher, but the subprocess upgrade must run before/outside the boot session (lock safety). Two blocking conflicts found: (R1) the safe runner refuses the real `erp_data.db` URL unless `allow_production=True`; (R2) the migration gate demands backup+confirmation for an upgrade on a production-named DB while the decision function exempts a new empty DB — they disagree on the same scenario. One concurrency hazard: subprocess Alembic vs. an open SQLite boot connection → `database is locked`. Commit ownership splits across an out-of-process subprocess (schema) and the in-process session (seeds); seeds must only run after a successful upgrade, and flag-off must preserve migrate_schema→diagnostic exactly. Resolve allow_production policy, gate/decision authority order, insertion restructuring, and is_new_db hardening before implementing P3.8-K.*
