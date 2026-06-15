# P3.8-K0 — Startup Wiring Conflict Resolution Plan

**Mode:** Documentation + lightweight contract test only. **No runtime wiring in this slice.** `app.py` is unchanged; `migrate_schema()` remains authoritative and runs first; no `alembic upgrade`/`stamp`, no schema/model/accounting/API/UI change.
**Status:** **No runtime wiring yet.** This document **resolves the three P3.8-K audit blockers** (R1, R2, R3) so that P3.8-K can be implemented safely afterward.
**Inputs reviewed:** `docs/P3_8_K_STARTUP_WIRING_AUDIT.md`, `services/alembic_runner.py`, `services/schema_migration_gate.py`, `services/schema_startup.py`, `services/schema_version.py`, and the `app.py` startup block (lines 26288–26316).

## Audit blockers being resolved

- **R1** — the safe Alembic runner refuses the real startup DB (`erp_data.db` is a production marker) unless `allow_production=True`; `DATABASE_URL` is exactly that path.
- **R2** — for a new empty `erp_data.db`, the **decision function** (P3.8-E) exempts backup while the **migration gate** (P3.8-I) demands backup + confirmation; the two disagree on the same scenario.
- **R3** — `is_new_db` keys only off the `journal_entries` table, so a partial/half-created DB can be misclassified as "new".

## 1. allow_production policy

- **Startup never sets `allow_production=True` implicitly.** The runner's production guard (`erp_data.db` marker) stays the default-deny.
- **A single explicit authorization token gates it.** Startup may pass `allow_production=True` to the runner **only** when a dedicated, explicit "startup-authorized" decision says so — never inferred from the DB path, never a hard-coded literal at the call site.
- **Gate approval is a precondition.** `allow_production=True` is permitted **only after** `evaluate_migration_gate(...)` returns `allowed=True` for the chosen action. If the gate is not consulted, or returns `allowed=False`, `allow_production` **must remain `False`** and the runner call must not be made.
- **Order of authorization (all must hold before any production runner call):**
  1. `ERP_ALEMBIC_AUTHORITATIVE` parsed `True` (P3.8-C).
  2. Decision (P3.8-E) selects an action that performs a runner operation (`alembic_upgrade_head`).
  3. Gate (P3.8-I) returns `allowed=True` for that action (backup + confirmation satisfied where required).
  4. Only then is `allow_production=True` passed to `run_upgrade_head` / `run_stamp`.
- **Explicit and testable.** The authorization is a discrete function/value (e.g. `production_authorized = flag_on and decision.action == ... and gate.allowed`) that a test can assert is `False` whenever the gate blocks — proving startup cannot silently authorize the production DB.

## 2. Decision vs. gate authority order

- **Decision proposes; gate disposes.** The decision function (P3.8-E) **proposes** an action; the migration gate (P3.8-I) is the **hard stop** for backup/confirmation. The gate can **only veto/allow** — it never invents a new action.
- **Hard-stop rule:** if `gate.allowed == False`, startup **blocks** regardless of what the decision proposed. There is **no silent fallback to `migrate_schema()`** when the flag is on.
- **Resolving the new empty `erp_data.db` conflict (R2):** pin one canonical rule —
  - A database is treated as **truly new/empty** only when it has **no `alembic_version` table and zero application tables** (see §4). For such a DB the **gate is consulted with `is_populated=False`**, and the canonical expected outcome is **`upgrade_head` allowed without backup/confirmation** — because an empty/zero-table file holds **no accounting data to protect**, the production-name marker alone does not force a backup.
  - **Concrete decision:** for `action == upgrade_head` **and** the §4 hardened `is_new_db == True`, the production-name marker is **not** sufficient to require backup; the gate must return `allowed=True` with `requires_backup=False`. This reconciles P3.8-E (exempt) and P3.8-I (currently demands backup for a production-named upgrade): **the empty-DB exemption wins, but only under the strict §4 definition of empty.**
  - **Any non-empty / partially-created / unstamped-legacy production DB** keeps the gate's **backup + confirmation hard stop** — no exemption.
- **Pinned expected behavior table:**

  | Scenario | Decision (proposes) | Gate (hard stop) | Final |
  |----------|---------------------|------------------|-------|
  | flag on, **strict-new empty** `erp_data.db` | `upgrade_head`, no backup | `allowed=True`, no backup | **upgrade_head, no backup** |
  | flag on, populated `erp_data.db` behind head | `upgrade_head`, backup+confirm | enforce backup+confirm | **block until backup+confirm** |
  | flag on, unstamped legacy populated | `require_stamp` | enforce backup+confirm | **block until backup+confirm** |
  | flag on, at_head | `verify_only` | n/a | **verify_only, no migration** |
  | flag on, ahead/unknown | `fail_closed` | n/a | **block** |

## 3. Boot-session / subprocess ordering

- **Any Alembic subprocess runs BEFORE `_boot_session` is opened.** Schema authority resolution (detection → decision → gate → optional `run_upgrade_head`/`run_stamp` subprocess) happens **outside and before** the `with get_session() as _boot_session:` block, so **no in-process SQLite connection is open** while the subprocess writes — eliminating the `database is locked` hazard (audit §5).
- **Flag-off path is unchanged.** When the flag is off, the existing block runs exactly as today: inside `with get_session() as _boot_session:`, call **`migrate_schema(_boot_session)` then `_log_schema_startup_diagnostic(_boot_session)`** in that order, same session — byte-for-byte, no new behavior.
- **Seeds run only after a successful schema-authority step.** The seed/data-migration calls (`initialize_chart_of_accounts` … `sync_account_balances`) execute **only if** the schema step succeeded:
  - flag off → after `migrate_schema()` returns normally;
  - flag on → after `verify_only` passes, or after the subprocess `upgrade_head`/`stamp` returns `success=True`.
  - If the schema step **blocks or fails closed**, startup raises a structured error and **seeds never run**.
- **No raw Alembic in `app.py`.** All Alembic invocation stays behind `services.alembic_runner`; the dispatcher only orchestrates.

## 4. is_new_db hardening (R3)

- **New means: no `alembic_version` table AND zero application tables.** A DB is "new/empty" only when **both** hold:
  1. the `alembic_version` table is **absent** (P3.7 `unstamped`, table-absent variant), **and**
  2. **no application tables exist** (not just `journal_entries` — check the core app table set / `Base.metadata` presence).
- **Partial/half-created DBs are NOT new.** If **some** app tables exist but not others, or `alembic_version` exists with no/extra rows, the DB is **not** new → route to `fail_closed` (or the appropriate non-new branch), never to the unguarded empty-DB upgrade.
- **Why:** the current single-table check (`journal_entries` absent) would treat a partially-built DB as new and could trigger an empty-DB upgrade over partial state. Requiring the conjunction prevents that.
- **Detection stays read-only** and runs **before** any table creation in `main()` (audit R3 ordering note); "new" is computed from the live DB state prior to `migrate_schema`/`create_all`.

## Resolution summary

- **R1 resolved:** production runner access is gated behind an explicit, gate-approved authorization; never silently enabled; testable as `False` whenever the gate blocks.
- **R2 resolved:** decision proposes, gate is the hard stop; the new-empty-`erp_data.db` conflict is pinned to **upgrade_head without backup, but only under the strict §4 empty definition**; all populated/partial/legacy production DBs keep the backup+confirmation hard stop.
- **R3 resolved:** `is_new_db` requires **no `alembic_version` and zero app tables**, so partial DBs are never treated as new.

## No-change decisions (P3.8-K0)

- **No runtime wiring; `app.py` untouched; `migrate_schema()` authoritative and first.**
- **No `alembic upgrade`/`stamp`, no PostgreSQL switch, no schema/model/accounting/API/UI change, no `Float → Decimal`.**
- **Resolutions are specified, not implemented** — P3.8-K implements them under these rules.

---

*Plan only — no runtime wiring yet, `app.py` untouched, `migrate_schema()` authoritative and first. Resolves the three P3.8-K audit blockers: (R1) startup may pass `allow_production=True` to the Alembic runner only after an explicit, gate-approved authorization — never silently, testable as False when the gate blocks; (R2) decision proposes / gate is the hard stop, and the new-empty-`erp_data.db` conflict is pinned to upgrade_head without backup but only under the strict §4 definition (no alembic_version + zero app tables), while every populated/partial/legacy production DB keeps the backup+confirmation hard stop; (R3) `is_new_db` requires no alembic_version table AND zero application tables so partial/half-created DBs are never treated as new. Subprocess Alembic runs before `_boot_session` opens (no SQLite lock); flag-off preserves migrate_schema → diagnostic exactly; seeds run only after a successful schema-authority step.*
