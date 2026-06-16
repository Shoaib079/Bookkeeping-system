# P3.9-B — migrate_schema() Deprecation Warning

**Date:** 2026-06-05  
**Mode:** Phase B — emit `DeprecationWarning` on every `migrate_schema()` call. **Body retained**; no removal (P3.9-C). No startup/flag/Alembic/schema/model/accounting change.

**Prerequisites:** [P3_9_B_CHAR_MIGRATE_SCHEMA_CALLERS.md](./P3_9_B_CHAR_MIGRATE_SCHEMA_CALLERS.md) · [P3_9_A_AUDIT.md](./P3_9_A_AUDIT.md)

**Contract:** `tests/test_p3_9_b_deprecation.py`

---

## Verdict

**P3.9-B Phase B: SHIPPED** — `migrate_schema()` emits `DeprecationWarning` on every entry. Function body unchanged; legacy `ERP_ALEMBIC_AUTHORITATIVE=0` path still works.

**NOT removed** — P3.9-C removal remains gated on a warning-clean operational window.

---

## Implementation

| Item | Detail |
|------|--------|
| Constant | `app.MIGRATE_SCHEMA_DEPRECATION_MESSAGE` |
| Emission | `warnings.warn(..., DeprecationWarning, stacklevel=2)` at top of `migrate_schema` body |
| Every call | Including idempotent second run and flag-off startup |
| Default-on startup | Stamped `at_head` DBs skip `migrate_schema()` — no warning at startup |

Message:

```text
migrate_schema() is deprecated; use Alembic (ERP_ALEMBIC_AUTHORITATIVE=1). Removal planned in P3.9-C.
```

---

## Test harness updates

| File | Change |
|------|--------|
| `tests/p3_schema_equivalence_utils.py` | `catch_warnings` + ignore around harness call |
| `tests/test_phase14da_model.py` | `pytest.warns(DeprecationWarning)` on direct calls |

Mock-injection wiring tests unchanged (stubs bypass `app.migrate_schema`).

---

## Rollback

Set `ERP_ALEMBIC_AUTHORITATIVE=0` for legacy path. Warning is informational only — no schema change.

---

## Next slice

**P3.9-C** — remove `migrate_schema()` implementation after warning-clean window (major release gate).

---

## No-change statement (P3.9-B)

No `migrate_schema()` removal, no startup wiring change, no flag default change, no Alembic revision change, no schema/model/accounting/API/UI change beyond the deprecation warning.
