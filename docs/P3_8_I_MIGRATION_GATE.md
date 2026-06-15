# P3.8-I — Backup / Confirmation Migration Gate

**Status:** Shipped (validation gate + tests)  
**Mode:** Validation helper only. **Not wired into startup.**

**Related:** [P3.8-E Decision Function](./P3_8_E_STARTUP_DECISION_FUNCTION.md) · [P3.8-H Alembic Runner](./P3_8_H_SAFE_ALEMBIC_RUNNER.md) · `services/schema_migration_gate.py`

---

## Purpose

Provide a **validation-only gate** that future Alembic-authoritative startup wiring (P3.8-J) will consult before any populated-database migration action.

| Does | Does not |
|------|----------|
| Validate backup path exists and is a non-empty file (when strict) | Create or restore backups |
| Validate exact confirmation phrase | Run Alembic upgrade/stamp |
| Return `MigrationGateDecision` with allow/block reason | Mutate database or files |
| Apply stricter rules for production-looking DB paths | Wire into `app.py` |
| | Disable `migrate_schema()` |

**`migrate_schema()` remains authoritative** until P3.8-J.

---

## API

```python
from services.schema_migration_gate import (
    REQUIRED_CONFIRMATION_PHRASE,
    evaluate_migration_gate,
    validate_backup_path,
    validate_confirmation_phrase,
)

decision = evaluate_migration_gate(
    db_path_or_url="sqlite:///:memory:",
    action="upgrade_head",          # upgrade_head | stamp | verify_only
    is_populated=True,
    backup_path="/path/to/backup.db",
    confirmation_value=REQUIRED_CONFIRMATION_PHRASE,
    require_backup=True,
    require_confirmation=True,
)
```

### Confirmation phrase (exact)

```
I HAVE BACKED UP THIS DATABASE
```

Whitespace is trimmed before comparison; case must match exactly.

### Gate behavior

| Scenario | Allowed without backup/confirm |
|----------|------------------------------|
| `verify_only` | Always |
| `upgrade_head` on empty DB (non-production) | Yes |
| `upgrade_head` on populated DB | No — requires valid backup + phrase |
| `stamp` (legacy) | No — always requires backup + phrase |
| Production-looking DB (`erp_data.db`, etc.) | No — stricter backup + phrase even for empty upgrade |

---

## Output (`MigrationGateDecision`)

| Field | Meaning |
|-------|---------|
| `allowed` | Whether gate passes |
| `message` | Human-readable reason |
| `requires_backup` / `requires_confirmation` | What was required for this action |
| `backup_valid` / `confirmation_valid` | Validation outcomes |
| `production_database` | Stricter path detected |

---

## Not wired (P3.8-I)

- `app.py` startup unchanged.
- No backup creation in this module.
- P3.8-F diagnostics log decisions only; they do not call this gate.

---

## Future P3.8-J

P3.8-J will combine:

1. P3.8-E decision (`requires_backup`, `requires_confirmation`, `blocks_startup`)
2. This gate (`evaluate_migration_gate`)
3. P3.8-H Alembic runner (`allow_execute=True` only when gate passes)

That wiring is explicit approval only.

---

## How to run tests

```bash
pytest tests/test_p3_8_i_migration_gate.py
pytest
```

Tests use temp files and in-memory URLs — never `erp_data.db`.

---

*Validation only — no backup creation, no Alembic execution, not wired into startup.*
