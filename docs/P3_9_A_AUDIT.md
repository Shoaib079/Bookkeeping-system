# P3.9-A — migrate_schema() Retirement Readiness Audit

**Mode:** Audit only. **No implementation, no deprecation, no removal, no schema/model change, no Alembic revision change.**

**Context:** P3.8-K2 wiring · P3.8-L-EXEC ✅ · P3.8-L-TESTS ✅ · P3.8-N ✅ (default-on). [P3_9_MIGRATE_SCHEMA_RETIREMENT_PLAN.md](./P3_9_MIGRATE_SCHEMA_RETIREMENT_PLAN.md) defines Phases A/B/C.

---

## Verdict — **NOT READY to remove `migrate_schema()`; Phase A (default Alembic authority) is DONE via P3.8-N**

| Phase | Status |
|-------|--------|
| **Phase A** — Alembic authoritative at startup by default | **DONE** (P3.8-N) — stamped `at_head` DBs skip `migrate_schema()`; explicit `=0` retains legacy path |
| **Phase B** — deprecate + warn on call | **NOT STARTED** |
| **Phase C** — remove implementation | **NOT STARTED** — blocked on Phase B + clean operational window |

Retirement **characterization and deprecation** slices remain before any removal.

---

## 1. P3.9 §2 prerequisite checklist (post P3.8-N)

| Prerequisite | Status | Evidence |
|--------------|--------|----------|
| P3.8-L bake-in executed | **PASS** | [P3_8_L_BAKEIN_EXEC.md](./P3_8_L_BAKEIN_EXEC.md) |
| P3.8-M local smoke (optional) | **PASS** (prior record) | [P3_8_M_LOCAL_SMOKE_TEST.md](./P3_8_M_LOCAL_SMOKE_TEST.md) |
| Schema equivalence | **PASS** | P3.4-D + [P3_8_L_TESTS.md](./P3_8_L_TESTS.md) |
| Rollback via explicit `=0` | **PASS** | L-EXEC + N parser tests |
| All production DBs stamped at head | **OPERATOR** — must verify before each deploy without `=0` | Unstamped legacy **blocks** under default-on |
| No unstamped legacy DBs in production | **OPERATOR** | Default-on design assumes stamped fleet |

---

## 2. Current runtime behavior (post P3.8-N)

| Env | Startup schema path |
|-----|---------------------|
| `ERP_ALEMBIC_AUTHORITATIVE` unset / empty | **Alembic authoritative** (default-on) |
| `=1` / `true` / `on` | Alembic authoritative |
| `=0` / `false` / `off` | **`migrate_schema()` then diagnostics** (legacy rollback) |
| invalid value | Fail-safe → legacy `migrate_schema()` path |

**Single runtime dispatch:** `app._run_schema_startup` → `migrate_schema_fn=migrate_schema` (see P3.8-L-TESTS single-caller guard).

---

## 3. Remaining callers and SQLite-only body

- **Runtime caller:** one — `run_schema_startup_in_session(... migrate_schema_fn=migrate_schema ...)` when plan is not skip-migrate (flag-off / legacy path).
- **Test harness:** `tests/p3_schema_equivalence_utils.py`, `tests/test_phase14da_model.py` — not production startup.
- **Body:** SQLite-only (`ALTER ADD COLUMN`, raw `sqlite3` backup, `PRAGMA`, partial indexes) — **invalid on PostgreSQL**; PG requires Alembic-only schema (P4.0/P4.2).

---

## 4. Gap analysis vs P3.9 Phases B/C

| Gap | Required before Phase B/C |
|-----|---------------------------|
| Deprecation warning on direct `migrate_schema()` call | Phase B implementation |
| Inventory of test-only / manual callers | Phase B characterization |
| Operational window with zero `=0` production deploys | Operator evidence |
| Phase B warning-free window | Phase C gate |
| PostgreSQL parity on Alembic-only builds | P4.0/P4.2 (parallel) |

---

## 5. PostgreSQL implications

- Production PG **must not** rely on `migrate_schema()` — ever.
- Default-on Alembic path is **required** for PG; explicit `=0` on PG would attempt invalid SQLite DDL if ever reached — flag-off on PG remains unsafe (decision layer blocks some states; operator must use Alembic-only on PG).

---

## 6. Required implementation slices (sequenced — NOT this audit)

1. **P3.9-B-CHAR** — characterize all non-wiring `migrate_schema()` call sites; pin deprecation warning contract.
2. **P3.9-B** — emit `DeprecationWarning` from `migrate_schema()` body; docs update.
3. **P3.9-C** — remove implementation after warning-clean window (major release gate).

---

## 7. Rollback

- **Before Phase C:** set `ERP_ALEMBIC_AUTHORITATIVE=0` → legacy path restored; no schema change.
- **After Phase C:** restore from backup + Alembic downgrade/rebuild — not hand-edit accounting tables.

---

## ROADMAP update recommendation

- Record **P3.9-A ✅** audit; **Phase A done via P3.8-N**; next **P3.9-B-CHAR** → P3.9-B → P3.9-C.
- Keep **ALEMBIC-01** Partial until Phase C or explicit “legacy no-op” milestone.

---

## No-change statement (P3.9-A)

Audit only — no `migrate_schema()` removal, no deprecation warnings, no startup behavior change beyond already-shipped P3.8-N, no schema/model/Alembic/accounting/API/UI change.
