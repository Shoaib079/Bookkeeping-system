# P3.8-K2 — Flag-Gated Startup Wiring

**Mode:** Runtime wiring behind `ERP_ALEMBIC_AUTHORITATIVE` + contract tests.

**Default:** Flag off — **unchanged** startup (`migrate_schema()` then diagnostics).

## Flag off (default)

When `ERP_ALEMBIC_AUTHORITATIVE` is unset, `0`, or invalid:

1. `prepare_schema_startup_authoritative()` returns immediately (no subprocess).
2. Inside the boot session, `_run_schema_startup()` calls:
   - `migrate_schema(session)` **first**
   - `_log_schema_startup_diagnostic(session)` **second**
3. Seeds and the rest of startup run as before.

No Alembic runner invocation. No behavior change from pre-K2.

## Flag on (`ERP_ALEMBIC_AUTHORITATIVE=1`)

### Order (P3.8-K0)

1. **Before** `with get_session() as _boot_session:` — `prepare_schema_startup_authoritative()`:
   - read-only detection → decision (P3.8-E) → gate (P3.8-I) when needed
   - optional `run_upgrade_head` subprocess for **strict-new empty** DB only
   - raises `SchemaStartupError` on block (seeds never run)
2. **Inside** boot session — `_run_schema_startup()`:
   - skips `migrate_schema()` when authoritative path already satisfied schema
   - always logs diagnostics

### Branches

| Scenario | `migrate_schema()` | Runner | Outcome |
|----------|-------------------|--------|---------|
| **at_head** | Skipped | No | Continue startup |
| **strict-new empty** | Skipped | `run_upgrade_head` (gate + production auth) | Continue on success; block on failure |
| **unstamped legacy** | Not run | No stamp | **Block** with stamp instructions |
| **behind_head** (populated) | Not run | No auto-upgrade | **Block** (backup/confirm not enough for auto-upgrade in K2) |
| **ahead_of_code / unknown** | Not run | No | **Fail closed** |

No silent fallback to `migrate_schema()` when the flag is on.

### Operator inputs (optional env)

| Variable | Purpose |
|----------|---------|
| `ERP_SCHEMA_BACKUP_PATH` | Path to backup file for gate validation |
| `ERP_SCHEMA_MIGRATION_CONFIRMATION` | Exact phrase `I HAVE BACKED UP THIS DATABASE` |

## What remains blocked (flag on)

- Auto-stamp of legacy databases
- Auto-upgrade of populated databases (even with backup + confirmation)
- Downgrade or guess on ahead/unknown revision states
- Raw Alembic in `app.py` (runner only, via `services/alembic_runner`)

## Error handling

`SchemaStartupError` includes:

- `action` — decision action (e.g. `require_stamp`, `fail_closed`)
- `operator_step` — required operator action
- message — log/operator-facing text

No silent fallback when flag on.

## Rollback

1. Set `ERP_ALEMBIC_AUTHORITATIVE=0` (or unset) → immediate revert to `migrate_schema()` path.
2. Restore database backup if a flag-on upgrade misbehaved.
3. `migrate_schema()` is **retained** — not removed or disabled.

## Files

| File | Role |
|------|------|
| `services/schema_startup_wiring.py` | Pre-session + in-session orchestration |
| `app.py` | `prepare_schema_startup_authoritative()` before boot session; `_run_schema_startup()` replaces inline pair |
| `tests/test_p3_8_k2_startup_wiring.py` | Contract tests |

## Related slices

- P3.8-K0 — conflict resolution plan
- P3.8-K1 — helper hardening (`infer_is_new_database`, gate strict-new, `is_production_runner_authorized`)

---

*Flag off: unchanged `migrate_schema()` → diagnostics. Flag on: detection/decision/gate before boot session; at_head skips migrate_schema; strict-new empty runs gated upgrade via safe runner; legacy unstamped / behind_head / ahead / unknown block without migrate_schema. Rollback = disable flag; migrate_schema retained.*
