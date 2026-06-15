# P3.8-H — Safe Alembic Command Wrapper

**Status:** Shipped (wrapper + tests)  
**Mode:** Service helper only. **Not wired into startup.**

**Related:** [P3.8-F Decision Diagnostics](./P3_8_F_STARTUP_DECISION_DIAGNOSTICS.md) · `services/alembic_runner.py`

---

## Purpose

Provide a **centralized, safe** wrapper for future Alembic CLI operations so startup wiring never shells out ad hoc.

| Does | Does not |
|------|----------|
| Build argv for `upgrade head` and `stamp` | Wire into `app.py` |
| Dry-run by default | Execute against `erp_data.db` in tests |
| Require `allow_execute=True` to run | Make Alembic authoritative |
| Reject production-looking DB URLs | Disable `migrate_schema()` |
| Read current revision (SELECT only) | Expose downgrade or arbitrary commands |
| Use `subprocess` with `shell=False` | Use `shell=True` |

**`migrate_schema()` remains authoritative** until a future approved cutover.

---

## API

```python
from services.alembic_runner import (
    AlembicCommandResult,
    build_upgrade_head_command,
    build_stamp_command,
    get_alembic_heads,
    get_current_revision,
    run_upgrade_head,
    run_stamp,
)

argv = build_upgrade_head_command(database_url="sqlite:///:memory:")
result = run_upgrade_head(database_url="sqlite:///:memory:")  # dry-run
result = run_upgrade_head(database_url=test_url, allow_execute=True)  # explicit
```

### `AlembicCommandResult`

| Field | Meaning |
|-------|---------|
| `command` | `upgrade` or `stamp` |
| `target` | `head` or revision id |
| `success` | Command succeeded (or dry-run accepted) |
| `message` | Safe log-facing summary |
| `dry_run` / `executed` | Execution state |
| `argv` | Full command argv (no shell) |
| `stdout` / `stderr` | Set only when executed |

---

## Safety rules

1. **Dry-run default** — `allow_execute=False` unless explicitly set.
2. **Production guard** — URLs containing `erp_data.db`, `production.db`, `prod.db`, etc. are rejected (`allow_production=True` override for documented ops only).
3. **No downgrade** — downgrade subcommands are blocked; no `run_downgrade` API.
4. **No arbitrary commands** — only `upgrade head` and `stamp <revision>` builders.
5. **No `shell=True`** — argv list passed to `subprocess.run(..., shell=False)`.
6. **Tests** — use in-memory SQLite only; never touch production `erp_data.db`.

---

## Not wired (P3.8-H)

- `app.py` does not import `services.alembic_runner`.
- Startup still runs `migrate_schema()` unchanged.
- P3.8-F diagnostics log decisions only; they do not call this wrapper.

---

## Future P3.8-J

P3.8-J may invoke this wrapper **behind** `ERP_ALEMBIC_AUTHORITATIVE` when decision action is `alembic_upgrade_head` or `require_stamp`, with backup/confirmation gates. That wiring is a separate, explicit slice.

---

## How to run tests

```bash
pytest tests/test_p3_8_h_alembic_runner.py
pytest
```

---

*Wrapper only — dry-run default, `allow_execute` required, not wired, no production execution.*
