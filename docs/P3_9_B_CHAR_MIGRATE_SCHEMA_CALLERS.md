# P3.9-B-CHAR — migrate_schema() Caller Inventory & Deprecation Contract

**Mode:** Tests + documentation only (2026-06-05). **No production behavior change.** No deprecation warnings emitted yet — that is **P3.9-B**.

**Goal:** Characterize every `migrate_schema()` call site before Phase B adds `DeprecationWarning`. Pins the warning contract P3.9-B must implement without changing runtime today.

**Prerequisites:** [P3_9_A_AUDIT.md](./P3_9_A_AUDIT.md) · [P3_8_L_TESTS.md](./P3_8_L_TESTS.md) · [P3_9_MIGRATE_SCHEMA_RETIREMENT_PLAN.md](./P3_9_MIGRATE_SCHEMA_RETIREMENT_PLAN.md)

**Contract:** `tests/test_p3_9_b_char_migrate_schema_callers.py`

---

## Executive summary

| Category | Count | Files |
|----------|-------|-------|
| **Runtime wiring (production)** | 1 injection + 2 dispatch calls | `app.py` → `services/schema_startup_wiring.py` |
| **Test harness — direct `app.migrate_schema`** | 4 call expressions | `tests/p3_schema_equivalence_utils.py` (1) · `tests/test_phase14da_model.py` (3) |
| **Test harness — mock `migrate_schema_fn`** | 5 modules | wiring/exec/k2 tests inject lambdas or local stubs |
| **Source inspection only** | 1 | `tests/test_receipt_ai_02_impl_3_learning_map.py` (`inspect.getsource`) |
| **Comment / doc references** | several | `models.py`, `alembic/`, `services/schema_*.py` — not call sites |

**Pre-B behavior (pinned):** `migrate_schema()` emits **no** `DeprecationWarning`.

---

## 1. Production runtime path

| Step | Location | Behavior |
|------|----------|----------|
| Definition | `app.py` — `def migrate_schema(session)` | SQLite-only DDL evolution body |
| Injection | `app.py` — `_run_schema_startup` | Exactly one `migrate_schema_fn=migrate_schema` |
| Dispatch | `services/schema_startup_wiring.py` — `run_schema_startup_in_session` | Calls `migrate_schema_fn(session)` when plan does **not** skip migrate (flag-off / legacy path) |

**Invariant (from P3.8-L-TESTS):** No other production module imports or calls `app.migrate_schema`. No direct `migrate_schema(session)` in `app.py` outside the dispatcher wiring.

**Default-on (P3.8-N):** Stamped `at_head` production DBs **do not** reach `migrate_schema_fn(session)` at startup. Explicit `ERP_ALEMBIC_AUTHORITATIVE=0` restores the legacy path.

---

## 2. Test harness — direct callers

These modules call **`app.migrate_schema`** directly (not via wiring). They exist for schema equivalence and idempotency characterization:

| File | Calls | Purpose |
|------|-------|---------|
| `tests/p3_schema_equivalence_utils.py` | 1 × `app.migrate_schema(session)` | Build schema B for Alembic ≡ migrate_schema drift harness |
| `tests/test_phase14da_model.py` | 3 × `app.migrate_schema(db)` | Idempotency + Phase 14D-A column presence |

**P3.9-B impact:** After deprecation warnings ship, these tests must either:
- use `pytest.warns(DeprecationWarning)` / `warnings.filterwarnings("ignore", …)` at module scope, or
- route through a shared test helper that expects the warning.

No harness caller may be deleted without updating the equivalence gate (P3.4-D / P3.8-L-TESTS).

---

## 3. Test harness — mock injections

These tests pass a **stub** `migrate_schema_fn` (lambda or local `def migrate_schema`) into `run_schema_startup_in_session` — they never invoke `app.migrate_schema`:

| Module | Pattern |
|--------|---------|
| `tests/test_p3_8_k2_startup_wiring.py` | local `def migrate_schema` stub |
| `tests/test_p3_8_l_exec_bakein_execution.py` | `lambda _s: migrate_calls.append("migrate")` |
| `tests/test_p3_8_l_tests_bakein_characterization.py` | lambda stubs + static wiring guards |

**P3.9-B impact:** None — mocks bypass `app.migrate_schema` body.

---

## 4. Source inspection only

| File | Pattern |
|------|---------|
| `tests/test_receipt_ai_02_impl_3_learning_map.py` | `inspect.getsource(erp_app.migrate_schema)` — asserts index DDL strings present |

Not a runtime call. P3.9-B warnings do not apply to source inspection.

---

## 5. P3.9-B deprecation warning contract (future — NOT implemented)

P3.9-B must add **at the top of** `app.migrate_schema` body:

```python
warnings.warn(
    "migrate_schema() is deprecated; use Alembic (ERP_ALEMBIC_AUTHORITATIVE=1). "
    "Removal planned in P3.9-C.",
    DeprecationWarning,
    stacklevel=2,
)
```

| Rule | Detail |
|------|--------|
| Category | `DeprecationWarning` |
| `stacklevel` | `2` — warning attributes to caller, not `migrate_schema` itself |
| Emission | **Every** entry to `migrate_schema` (including idempotent second run) |
| Flag-off startup | Warning fires once per startup when legacy path runs |
| Test harness | Direct callers (§2) will see warnings — update tests in P3.9-B slice |
| Mock injections | Unaffected (§3) |

**P3.9-B must not:** remove body logic, change startup wiring, change flag default, or alter Alembic behavior.

---

## 6. PostgreSQL

Production PostgreSQL **must never** invoke `migrate_schema()` — body is SQLite-only. Flag-on default prevents dispatch; operator must not set `=0` on PG.

---

## Next slice

**P3.9-B** — implement §5 warning in `app.migrate_schema`; update §2 test harness callers to expect/filter warnings; docs sync.

---

## No-change statement (P3.9-B-CHAR)

Characterization only — no `DeprecationWarning` added, no `migrate_schema()` removal, no startup/flag/Alembic/schema/model/accounting/API/UI change.
