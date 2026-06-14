# P3.8-C — Alembic Authority Flag Parser (Parser Only)

**Status:** Shipped (env flag parser + tests)  
**Mode:** Tiny runtime helper. **Not wired into startup authority.**

**Related:** [P3.8-A Startup Diagnostics](./P3_8_SCHEMA_STARTUP_DIAGNOSTICS.md) · `services/schema_startup.py`

---

## Purpose

Provide a **fail-safe parser** for the future `ERP_ALEMBIC_AUTHORITATIVE` environment variable so P3.8-D+ can gate cutover behavior without ad-hoc string checks.

| Does | Does not |
|------|----------|
| Parse explicit env string values | Change startup behavior today |
| Default to `False` when unset/invalid | Make Alembic authoritative |
| Expose `is_alembic_authoritative_enabled()` | Disable/remove `migrate_schema()` |
| | Run `alembic upgrade` or stamp |
| | Read DB or invoke Alembic CLI |

**`migrate_schema()` remains authoritative** until a future approved cutover uses this flag.

---

## API

```python
from services.schema_startup import (
    ALEMBIC_AUTHORITATIVE_ENV_VAR,
    parse_alembic_authoritative_flag,
    is_alembic_authoritative_enabled,
)

parse_alembic_authoritative_flag(None)   # False
parse_alembic_authoritative_flag("1")    # True
is_alembic_authoritative_enabled(environ)  # reads ERP_ALEMBIC_AUTHORITATIVE
```

Environment variable name: **`ERP_ALEMBIC_AUTHORITATIVE`**

---

## Parsing rules (fail-safe → `False`)

| Input | Result |
|-------|--------|
| unset / `None` | `False` |
| `""` or whitespace only | `False` |
| `0`, `false`, `no`, `off` (case-insensitive, trimmed) | `False` |
| `1`, `true`, `yes`, `on` (case-insensitive, trimmed) | `True` |
| any other value | `False` |

No side effects. No schema or migration actions.

---

## Not wired (P3.8-C)

- **`app.main()`** does not read this flag.
- **`migrate_schema()`** still runs on every startup unchanged.
- P3.8-A diagnostics still log read-only status only.

---

## Future P3.8-D

P3.8-D will **consume** `is_alembic_authoritative_enabled()` to branch startup authority (e.g. skip redundant DDL when stamped and flag is on). That phase is separate and requires explicit approval.

---

## How to run tests

```bash
pytest tests/test_p3_8_c_alembic_authority_flag.py
pytest
```

---

*Parser only — default false, fail-safe false, not wired, `migrate_schema()` still authoritative.*
