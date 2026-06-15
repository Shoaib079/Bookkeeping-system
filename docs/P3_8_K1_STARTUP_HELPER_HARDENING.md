# P3.8-K1 — Startup Wiring Helper Hardening

**Mode:** Service/helper implementation + tests only. **No startup behavior change in this slice.**

**Status:** Helper-level fixes for the three P3.8-K audit blockers (R1, R2, R3). Runtime wiring is deferred to **P3.8-K2**.

## Scope

| In scope | Out of scope |
|----------|--------------|
| Harden `infer_is_new_database()` | Change `app.py` startup |
| Add `is_production_runner_authorized()` | Make Alembic authoritative |
| Reconcile gate for strict-new empty production DB | Run `alembic upgrade` / `stamp` |
| Contract tests + this doc | Disable/remove `migrate_schema()` |
| | Schema/model/accounting/API/UI changes |

`migrate_schema()` remains authoritative and runs first on every startup (unchanged).

## Audit blockers resolved (helpers only)

### R1 — Production runner authorization

`is_production_runner_authorized(flag_authoritative, decision, gate_decision)` returns `True` only when:

1. `ERP_ALEMBIC_AUTHORITATIVE` is on (`flag_authoritative=True`),
2. `decision.action` requires runner execution (`alembic_upgrade_head` or `require_stamp`),
3. `gate_decision.allowed` is `True`.

Pure function — no DB access, no environment reads, no side effects. P3.8-K2 will use this to decide when `allow_production=True` may be passed to `alembic_runner`.

### R2 — Gate vs decision on new empty `erp_data.db`

`evaluate_migration_gate(..., is_strict_new_empty=True)` reconciles the P3.8-E / P3.8-I conflict:

- **`upgrade_head` + strict-new empty** (`is_populated=False`, `is_strict_new_empty=True`): allowed **without** backup or confirmation, even when the path matches `erp_data.db`.
- **Populated / partial / legacy production DBs**: backup + confirmation still required.
- **`stamp`**: backup + confirmation always required (no strict-new exemption).

Decision proposes; gate disposes. The gate never invents a new action.

### R3 — New DB detection hardening

`infer_is_new_database()` now requires **both**:

1. No `alembic_version` table, **and**
2. Zero application tables from `Base.metadata`.

Partial DBs (some app tables present), stamped DBs, and fully migrated legacy DBs are **not** new. Helpers `count_application_tables()` and `has_alembic_version_table()` support tests and future wiring.

## Files

| File | Change |
|------|--------|
| `services/schema_startup.py` | Hardened detection; `is_production_runner_authorized()` |
| `services/schema_migration_gate.py` | `is_strict_new_empty` parameter on `evaluate_migration_gate()` |
| `tests/test_p3_8_k1_startup_helper_hardening.py` | Contract tests |
| `docs/P3_8_K1_STARTUP_HELPER_HARDENING.md` | This document |

## Future: P3.8-K2 wiring

P3.8-K2 will connect these helpers into startup **outside** the boot session (per P3.8-K0):

1. Detect strict-new via `infer_is_new_database()` before any table creation.
2. Build decision (P3.8-E) and evaluate gate (P3.8-I) with `is_strict_new_empty`.
3. Call `is_production_runner_authorized()` before any production `alembic_runner` invocation.
4. Flag-off path unchanged: `migrate_schema()` → diagnostics only.

---

*Helper-only slice. No startup behavior change. Resolves R1/R2/R3 at the service layer. P3.8-K2 implements runtime wiring under P3.8-K0 rules.*
