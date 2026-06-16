# P3.8-L-EXEC — Alembic Authority Bake-In Execution Record

**Date:** 2026-06-16  
**Mode:** Operational bake-in execution (automated throwaway DBs + prior manual smoke). **No flag default change, no `migrate_schema()` retirement, no schema/model change.**

**Prerequisites:** [P3_8_L_BAKEIN_AUDIT.md](./P3_8_L_BAKEIN_AUDIT.md) · [P3_8_L_BAKE_IN_REVIEW_PLAN.md](./P3_8_L_BAKE_IN_REVIEW_PLAN.md) · [P3_8_M_LOCAL_SMOKE_TEST.md](./P3_8_M_LOCAL_SMOKE_TEST.md)

---

## Verdict

**P3.8-L bake-in execution: PASS** on automated throwaway-DB matrix + prior P3.8-M manual smoke on stamped `erp_data.db`.

**Still NOT ready to retire `migrate_schema()`** — P3.8-L-TESTS (schema-equivalence gate, single-caller guard, never-on-PG wiring test, lock-safety) and P3.8-N default flip remain gated.

---

## Automated execution (throwaway SQLite only)

Contract + scenario runner: `tests/test_p3_8_l_exec_bakein_execution.py`

| Scenario | Expected | Result |
|----------|----------|--------|
| Flag **off** — normal startup | `migrate_schema()` runs, then diagnostics | **PASS** |
| Flag **on** — stamped `at_head` | `verify_only`; `migrate_schema` **skipped** | **PASS** |
| Flag **on** — unstamped legacy (populated) | Block (`require_stamp`); no migrate, no auto-upgrade | **PASS** |
| Flag **on** — ahead-of-code (`0002` stamp) | Fail closed | **PASS** |
| Flag **on** — unknown revision | Fail closed | **PASS** |
| Flag **on** — strict-new empty DB | Gate + mocked `alembic upgrade head`; skip migrate | **PASS** |
| Flag **on** — populated `behind_head` | Block even with backup+confirmation (K2 never auto-upgrades populated) | **PASS** |
| **Rollback** — flag off after flag-on block | `migrate_schema()` path restored | **PASS** |

Supporting unit coverage: `tests/test_p3_8_k2_startup_wiring.py` (P3.8-K2 machinery).

---

## Manual execution (P3.8-M — prior record)

| Scenario | Result |
|----------|--------|
| Flag off on `erp_data.db` | **PASS** ([P3_8_M_LOCAL_SMOKE_TEST.md](./P3_8_M_LOCAL_SMOKE_TEST.md)) |
| Flag on on stamped `erp_data.db` at `0001` | **PASS** |
| Rollback (unset flag) | **PASS** |

Backups verified; no data loss observed during manual smoke.

---

## §3 Required evidence checklist (review plan)

| Evidence | Status |
|----------|--------|
| Full `pytest` green | **PASS** — **4231 passed**, 9 skipped, 2 xfailed |
| App starts flag off (`migrate_schema`) | **PASS** (P3.8-M + automated flag-off scenario) |
| App starts flag on `at_head` (`verify_only`) | **PASS** (P3.8-M + automated at_head scenario) |
| No data loss | **PASS** (manual smoke; automated uses throwaway DBs only) |
| No schema drift | **OPEN** — requires P3.8-L-TESTS schema-equivalence gate |
| Rollback verified (disable flag) | **PASS** |
| Logs reviewed | **PASS** (P3.8-M manual; `[schema]` diagnostics in K2/EXEC tests) |

---

## §4 Do-not-proceed criteria

None triggered during this execution window.

---

## Next slices (sequenced)

1. **P3.8-L-TESTS** — add §6 characterization tests from [P3_8_L_BAKEIN_AUDIT.md](./P3_8_L_BAKEIN_AUDIT.md) (schema equivalence, single-caller guard, never-on-PG, lock-safety, flag-off parity).
2. **P3.8-N** — default flip to flag-on (after L-TESTS + equivalence green).
3. **P3.9** — retire `migrate_schema()` implementation.
4. **MD-05** — Numeric migration (parallel critical path).
5. **P4.2** — PostgreSQL cutover (after Alembic authority + Numeric).

---

## Rollback

Disable `ERP_ALEMBIC_AUTHORITATIVE` → `migrate_schema()` authoritative again; **no schema change**.

---

## No-change statement (P3.8-L-EXEC)

No feature-flag default change, no production DB mutation for strict-new upgrade path, no Alembic revision change, no `migrate_schema()` removal, no PostgreSQL runtime switch.
