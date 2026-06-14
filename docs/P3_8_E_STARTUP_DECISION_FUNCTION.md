# P3.8-E — Pure Startup Decision Function

**Status:** Shipped (pure decision logic + tests)  
**Mode:** Service implementation only. **Not wired into startup.**

**Related:** [P3.8-D Decision Plan](./P3_8_D_STARTUP_DECISION_PLAN.md) · `services/schema_startup.py`

---

## Purpose

Implement the **pure** `decide_schema_startup_action()` planned in P3.8-D. Callers pass a resolved input snapshot; the function returns an action and safety flags. **No I/O, no env reads, no migrations.**

| Does | Does not |
|------|----------|
| Return `SchemaStartupDecision` | Wire into `app.py` startup (P3.8-F) |
| Encode the P3.8-D decision matrix | Run `alembic upgrade` or stamp |
| Fail-safe when flag is off | Call `migrate_schema()` |
| Block logically unsafe paths | Change schema/models/API/UI |

**`migrate_schema()` remains authoritative** at runtime until P3.8-F wires this function.

---

## API

```python
from services.schema_startup import decide_schema_startup_action, SchemaStartupDecision

decision = decide_schema_startup_action(
    flag_authoritative=False,
    schema_status="unstamped",
    is_new_db=False,
    dialect="sqlite",
    backup_available=False,
    confirmation_given=False,
    db_revision=None,
    head_revision="0001",
)
```

### Inputs

| Input | Role |
|-------|------|
| `flag_authoritative` | Parsed `ERP_ALEMBIC_AUTHORITATIVE` (caller supplies) |
| `schema_status` | P3.7 status (`unstamped`, `at_head`, `behind_head`, …) |
| `is_new_db` | Empty/fresh database |
| `dialect` | `sqlite` or `postgresql` |
| `backup_available` | Operator precheck |
| `confirmation_given` | Operator confirmation |
| `db_revision` / `head_revision` | For messages |

### Output (`SchemaStartupDecision`)

| Field | Meaning |
|-------|---------|
| `action` | `run_migrate_schema` \| `verify_only` \| `alembic_upgrade_head` \| `require_stamp` \| `fail_closed` |
| `message` | Actionable human text |
| `blocks_startup` | Stop startup when `True` |
| `requires_backup` | Populated-DB DDL needs backup first |
| `requires_confirmation` | Operator must confirm |

---

## Decision matrix (flag on)

| State | Action | Blocks when |
|-------|--------|-------------|
| Flag **off** (any) | `run_migrate_schema` | Never |
| New / empty DB | `alembic_upgrade_head` | Never |
| `at_head` | `verify_only` | Never |
| `unstamped` / `unstamped_legacy` | `require_stamp` | Until backup + confirmation |
| `behind_head` | `alembic_upgrade_head` | Until backup + confirmation |
| `ahead_of_code` | `fail_closed` | Always |
| `unknown` / invalid | `fail_closed` | Always |

When `flag_authoritative` is **on**, `run_migrate_schema` is **never** returned (including PostgreSQL).

---

## Purity guarantees

`decide_schema_startup_action()` must not:

- Open DB connections (`create_engine`, `Session`)
- Read `os.environ`
- Call `migrate_schema()` or Alembic CLI
- Touch the filesystem

Unit tests enforce this via source contract.

---

## Future P3.8-F

P3.8-F will:

1. Read flag via `is_alembic_authoritative_enabled()`
2. Read schema status via `detect_schema_version()`
3. Call `decide_schema_startup_action()`
4. **Act** on the decision (run `migrate_schema`, log, block, etc.)

P3.8-E ships the decision only — **no execution, no startup wiring**.

---

## How to run tests

```bash
pytest tests/test_p3_8_e_startup_decision_function.py
pytest
```

---

*Pure decision only — not wired, no migration execution, `migrate_schema()` still authoritative.*
