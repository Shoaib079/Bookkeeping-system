# P3.8-F — Startup Decision Diagnostics (Log Only)

**Status:** Shipped (diagnostic wiring + tests)  
**Mode:** Log-only integration of flag + schema status + decision. **No action execution.**

**Related:** [P3.8-E Decision Function](./P3_8_E_STARTUP_DECISION_FUNCTION.md) · [P3.8-A Startup Diagnostics](./P3_8_SCHEMA_STARTUP_DIAGNOSTICS.md) · `services/schema_startup.py`

---

## Purpose

Wire P3.8-C (flag parser), P3.7 (schema status), and P3.8-E (decision function) into startup **logging only**. Operators see what the future authority path *would* do; behavior is unchanged.

| Does | Does not |
|------|----------|
| Log schema diagnostic (P3.8-A) | Run `alembic upgrade` or stamp |
| Log decision `action` + `would_block_startup` | Block startup (even for `fail_closed`) |
| Read `ERP_ALEMBIC_AUTHORITATIVE` for decision input | Execute `decision.action` |
| Run after `migrate_schema()` | Disable/remove `migrate_schema()` |
| | Make Alembic authoritative |

**`migrate_schema()` remains authoritative** and still runs on every startup.

---

## API

```python
from services.schema_startup import (
    build_schema_startup_decision,
    log_schema_startup_decision_diagnostics,
)

bundle = build_schema_startup_decision(session)  # diagnostic + decision
log_schema_startup_decision_diagnostics(session)  # logs both; returns bundle
```

### Log lines (example)

```
[schema] Database is not Alembic-stamped; migrate_schema remains active.
[schema] decision action=run_migrate_schema would_block_startup=False (diagnostics only; not enforced) — ...
```

When flag is on and DB is unstamped:

```
[schema] decision action=require_stamp would_block_startup=True (diagnostics only; not enforced) — ...
```

Startup **continues** regardless of `would_block_startup`.

---

## Startup wiring (`app.py`)

After `migrate_schema(_boot_session)`:

```python
_log_schema_startup_diagnostic(_boot_session)
```

Shim delegates to `log_schema_startup_decision_diagnostics()`. No branching on `decision.action`.

---

## Safety

- **Diagnostics only** — decision is never executed in P3.8-F.
- **No startup blocking** — `(diagnostics only; not enforced)` is always logged.
- **No upgrade/stamp** — runtime path has no Alembic CLI or `op.upgrade`.
- **Read-only inputs** — flag + `detect_schema_version` + pure `decide_schema_startup_action`.

---

## Future P3.8-G

P3.8-G may add **flag-gated behavior**: act on `decision.action`, optionally block startup when `blocks_startup` is true. That requires explicit approval and is **out of scope** for P3.8-F.

---

## How to run tests

```bash
pytest tests/test_p3_8_f_startup_decision_diagnostics.py
pytest
```

---

*Diagnostics only — no action execution, no startup blocking, `migrate_schema()` still authoritative.*
