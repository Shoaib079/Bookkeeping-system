# P3.8-L-TESTS — Alembic Authority Bake-In Characterization Gate

**Date:** 2026-06-16  
**Mode:** Tests + documentation only. **No production code change, no flag default change, no schema/model change, no `migrate_schema()` retirement.**

**Prerequisites:** [P3_8_L_BAKEIN_AUDIT.md](./P3_8_L_BAKEIN_AUDIT.md) §6 · [P3_8_L_BAKEIN_EXEC.md](./P3_8_L_BAKEIN_EXEC.md)

---

## Verdict

**P3.8-L-TESTS characterization gate: PASS** — all §6 retirement-prep invariants are pinned by automated tests.

**Still NOT ready to retire `migrate_schema()`** — P3.8-N default flip and P3.9 retirement remain gated on operational bake-in window + all DBs stamped at head.

---

## §6 gate matrix (audit → test)

| Invariant | Primary test module |
|-----------|---------------------|
| Schema equivalence (Alembic `0001` ≡ `migrate_schema`-evolved) | `test_p3_8_l_tests_bakein_characterization.py` · `test_p3_4_d_alembic_baseline.py` |
| Single runtime caller of `migrate_schema()` | `test_p3_8_l_tests_bakein_characterization.py` |
| Flag-on never invokes `migrate_schema_fn` when plan skips migrate | `test_p3_8_l_tests_bakein_characterization.py` · `test_p3_8_k2_startup_wiring.py` |
| PostgreSQL + flag-on decision never `run_migrate_schema` | `test_p3_8_l_tests_bakein_characterization.py` · `test_p3_8_e_startup_decision_function.py` |
| Lock-safety (`prepare` before boot session) | `test_p3_8_l_tests_bakein_characterization.py` · `test_p3_8_k2_startup_wiring.py` |
| Flag-off parity (migrate then diagnostics, same order) | `test_p3_8_l_tests_bakein_characterization.py` · `test_p3_8_k2_startup_wiring.py` |
| End-to-end flag-on SQLite DB states | `test_p3_8_l_exec_bakein_execution.py` · `test_p3_8_k2_startup_wiring.py` |

Contract runner: `tests/test_p3_8_l_tests_bakein_characterization.py`

---

## Operational notes

- **Flag-off on PostgreSQL** still resolves to `run_migrate_schema` in the pure decision function — PG production requires flag-on + Alembic-only schema (P4.0/P4.2).
- Schema equivalence uses ephemeral in-memory SQLite only; never touches `erp_data.db`.
- Legacy `migrate_schema()` path requires **explicit** `ERP_ALEMBIC_AUTHORITATIVE=0` after **P3.8-N ✅** (unset no longer opts out).

---

## Next slices

1. **P3.9** — phased `migrate_schema()` retirement.
2. **MD-05** — Numeric migration (parallel critical path).

---

## No-change statement (P3.8-L-TESTS)

No feature-flag default change, no production DB mutation, no Alembic revision change, no `migrate_schema()` removal, no PostgreSQL runtime switch.
