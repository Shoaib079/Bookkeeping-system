# P3.8-D — Flag-Aware Startup Decision Plan

**Mode:** Documentation + lightweight contract test only. **No runtime change in this slice.** `ERP_ALEMBIC_AUTHORITATIVE` is **not wired into startup**; `app.py` behavior is unchanged; `migrate_schema()` is **not removed, not disabled**; no `alembic upgrade`, no `alembic stamp`, no schema/model/accounting/API/UI change.
**Status:** **No runtime change yet.** `migrate_schema()` **remains authoritative now.** This document specifies the exact pure decision function to be implemented **later** when the flag is wired.
**Context:** P3.7 added read-only schema-version detection (`services.schema_version`); P3.8-A added read-only startup diagnostics after `migrate_schema()`; P3.8-B designed the authority flag plan; P3.8-C added the flag parser (not wired). This slice defines the decision logic that will sit between the parser and any future startup wiring.

## 1. Inputs

The decision function is **pure** — it takes a fully-resolved input snapshot and returns a decision. It performs **no I/O and executes no migration**.

| Input | Source | Type | Notes |
|-------|--------|------|-------|
| `flag_authoritative` | P3.8-C parser of `ERP_ALEMBIC_AUTHORITATIVE` | bool | default `False` (fail-safe to current behavior) |
| `schema_status` | `services.schema_version` (P3.7, read-only) | enum/str | `at_head` / `behind_head` / `unstamped_legacy` / `ahead_of_code` / `unknown` |
| `is_new_db` | `services.schema_version` (no app tables present) | bool | empty/fresh DB |
| `dialect` | active SQLAlchemy engine dialect | str | `"sqlite"` or `"postgresql"` |
| `backup_available` | operator-provided / startup precheck | bool | required before any upgrade on a populated DB |
| `confirmation_given` | operator-provided | bool | required before upgrade-on-populated or stamp-legacy |

- Inputs are **resolved by callers** (parser, `schema_version`, engine) and passed in explicitly — the function never reads env vars, the DB, or the filesystem itself (keeps it unit-testable and side-effect-free).

## 2. Outputs

The function returns a single immutable decision object.

| Field | Type | Meaning |
|-------|------|---------|
| `action` | enum/string | one of: `run_migrate_schema`, `verify_only`, `alembic_upgrade_head`, `require_stamp`, `fail_closed` |
| `message` | str | human-readable, actionable: names the DB state, current vs expected revision, and the required operator action |
| `blocks_startup` | bool | `True` when startup must stop (e.g. `fail_closed`, or a `require_*` precondition unmet) |
| `requires_backup` | bool | `True` when the action would run DDL on a populated DB |
| `requires_confirmation` | bool | `True` when explicit operator confirmation is needed (upgrade-on-populated, stamp-legacy) |

Action meanings:
- **`run_migrate_schema`** — current behavior: hand off to `migrate_schema()` (flag off).
- **`verify_only`** — DB already at head; confirm and start, no migration.
- **`alembic_upgrade_head`** — run `alembic upgrade head` (only safe automatically for a new/empty DB; for populated DBs gated by backup + confirmation).
- **`require_stamp`** — legacy unstamped DB: verify equivalence, back up, `alembic stamp 0001` under confirmation; **never auto-upgrade**.
- **`fail_closed`** — stop startup with a clear message; never guess, never downgrade, never auto-migrate.

## 3. Decision matrix

| # | flag | DB state | `action` | `blocks_startup` | `requires_backup` | `requires_confirmation` |
|---|------|----------|----------|------------------|-------------------|--------------------------|
| 1 | **off** | any | `run_migrate_schema` | False | False | False |
| 2 | on | **new / empty DB** | `alembic_upgrade_head` | False | False | False (empty — nothing to back up) |
| 3 | on | **at_head** | `verify_only` | False | False | False |
| 4 | on | **unstamped legacy** | `require_stamp` | True until backup+confirm | True | True |
| 5 | on | **behind_head** | `alembic_upgrade_head` | True until backup+confirm | True | True |
| 6 | on | **ahead_of_code** | `fail_closed` | True | False | False |
| 7 | on | **unknown / ambiguous** | `fail_closed` | True | False | False |

- **Flag off short-circuits everything** → `run_migrate_schema` regardless of DB state (row 1 wins first).
- **Unstamped legacy is never auto-upgraded** (row 4) — it is verified, backed up, and stamped under confirmation only.
- **Behind-head populated DB** (row 5) requires **backup + confirmation** before `alembic_upgrade_head`; absent either, the decision **blocks startup** with the required-action message rather than proceeding.
- **Ahead-of-code and any unknown/ambiguous state** → `fail_closed` (rows 6–7).

## 4. Safety rules

- **Fail-safe default** — flag unset/absent/invalid → `flag_authoritative=False` → `run_migrate_schema` (today's behavior).
- **No destructive migrations** — the decision never selects a drop/destructive path; actions are additive or verify/stamp only.
- **No automatic upgrade of a populated DB without backup** — `alembic_upgrade_head` on a non-empty DB requires `requires_backup` and `requires_confirmation`; if unmet, `blocks_startup=True`.
- **No automatic stamp of a legacy DB without confirmation** — `require_stamp` always carries `requires_confirmation=True` (and `requires_backup=True`).
- **`migrate_schema()` fallback only when the flag is off** — when flag on, `migrate_schema()` is not the chosen action; it remains retained as a legacy no-op safety net but is not driven by this function.
- **PostgreSQL never uses `migrate_schema`** — on `dialect == "postgresql"`, `run_migrate_schema` is never returned; a PG path that would otherwise fall to `migrate_schema` resolves to `fail_closed` (PG must be Alembic-driven). PG’s SQLite-only DDL/PRAGMA is invalid.
- **Fail closed on ambiguity** — any unrecognized/conflicting input combination → `fail_closed`.

## 5. Future implementation boundaries

- **Decision function first** — implement the pure function (inputs → decision) as `services/`-layer logic, fully unit-tested, **before** any startup wiring.
- **Tests before startup wiring** — the decision matrix is covered by unit tests prior to touching `app.py`.
- **Startup wiring later** — wiring `ERP_ALEMBIC_AUTHORITATIVE` into `app.py` startup (calling the decision function and acting on it) is a **separate future slice**, not P3.8-D.
- **No migration execution in the decision function itself** — the function only **decides**; it never runs `alembic upgrade`, `alembic stamp`, `migrate_schema()`, backups, or any DDL/IO. Execution belongs to the future startup wiring, gated on the decision’s flags.

## No-change decisions (P3.8-D)

- **No runtime/startup change; flag not wired; `app.py` untouched; `migrate_schema()` stays authoritative now.**
- **No `alembic upgrade`, no `alembic stamp`, no PostgreSQL switch, no schema/model/accounting/API/UI change, no `Float → Decimal`.**
- **The decision function is specified, not implemented** — implementation, tests, and wiring are future slices.

---

*Design only — no runtime change yet, flag not wired, `migrate_schema()` authoritative now. Specifies a pure decision function: inputs (parsed flag, `services.schema_version` status, is-new-DB, dialect, backup/confirmation availability) → outputs (`action` ∈ {run_migrate_schema, verify_only, alembic_upgrade_head, require_stamp, fail_closed}, message, blocks_startup, requires_backup, requires_confirmation). Matrix: flag off → run_migrate_schema; on+new → alembic_upgrade_head; on+at_head → verify_only; on+unstamped legacy → require_stamp (never auto-upgrade); on+behind_head → upgrade only after backup+confirmation; on+ahead_of_code or unknown → fail_closed. Safety: fail-safe default, no destructive migrations, no auto-upgrade of populated DB without backup, no auto-stamp without confirmation, migrate_schema fallback only when flag off, PostgreSQL never uses migrate_schema. Boundaries: decision function first, tests before wiring, startup wiring later, the function never executes a migration.*
