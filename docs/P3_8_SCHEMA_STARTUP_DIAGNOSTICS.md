# P3.8-A — Schema Startup Diagnostics (Read-Only)

**Status:** Shipped (startup log wiring + tests)  
**Mode:** Read-only diagnostic wiring. **No migration execution.**

**Related:** [P3.7 Schema Version Detection](./P3_7_SCHEMA_VERSION_DETECTION.md) · `services/schema_startup.py` · `services/schema_version.py`

---

## Purpose

Report Alembic schema status at startup **without changing behavior**. Operators and developers see one INFO log line; the app continues normally.

| Does | Does not |
|------|----------|
| Call P3.7 `detect_schema_version` read-only | `alembic upgrade` |
| Log a safe human message at startup | `alembic stamp` |
| Return a diagnostic dict for tests/tools | Create/alter schema |
| Run after `migrate_schema()` in `main()` | Block or gate startup |
| | Make Alembic authoritative |
| | Remove/disable `migrate_schema()` |

**`migrate_schema()` remains authoritative** for schema evolution.

---

## API

```python
from services.schema_startup import (
    get_schema_startup_diagnostic,
    log_schema_startup_diagnostic,
    startup_message_for_status,
)

diag = get_schema_startup_diagnostic(session)  # or engine/connection
log_schema_startup_diagnostic(session)         # logs INFO, returns diag
```

### Diagnostic fields

| Field | Meaning |
|-------|---------|
| `status` | `unstamped` \| `at_head` \| `behind_head` \| `ahead_of_code` \| `unknown` |
| `db_revision` | Current `alembic_version.version_num` if present |
| `head_revision` | Local Alembic head from disk (currently `0001`) |
| `message` | Safe startup-facing text (see below) |
| `detail` | Technical message from P3.7 detector |
| `read_only` | Always `True` |
| `blocks_startup` | Always `False` (P3.8-A) |

### Startup messages

| Status | Message |
|--------|---------|
| `at_head` | Database schema is stamped at Alembic head {head}. |
| `unstamped` | Database is not Alembic-stamped; migrate_schema remains active. |
| `behind_head` | Database schema is behind Alembic head; no automatic upgrade will run. |
| `ahead_of_code` | Database schema is newer than this code; no migration will run. |
| `unknown` | Database schema version could not be determined safely. |

---

## Startup wiring

In `app.main()`, immediately **after** `migrate_schema(_boot_session)`:

```python
_log_schema_startup_diagnostic(_boot_session)
```

Thin shim in `app.py` delegates to `log_schema_startup_diagnostic()`. Logging only — no UI banner, no FastAPI middleware, no exceptions raised.

---

## Safety

- **Diagnostic only** — detection cannot mutate the database.
- **No startup blocking** — all statuses allow the app to continue.
- **No upgrade/stamp** — runtime path contains no Alembic CLI or `op.upgrade` calls.
- **Rollback** — disabling diagnostics is a code revert; DB state is unaffected.

---

## Future P3.8-B

A follow-up may add **flag-gated** behavior (e.g. warn in dev, optional strict mode in CI). P3.8-A deliberately ships **log-only** so production behavior is unchanged until explicitly approved.

---

## How to run tests

```bash
pytest tests/test_p3_8_schema_startup_diagnostics.py
pytest
```

---

*Read-only diagnostics only — no upgrade, no stamp, no startup blocking, `migrate_schema()` still authoritative.*
