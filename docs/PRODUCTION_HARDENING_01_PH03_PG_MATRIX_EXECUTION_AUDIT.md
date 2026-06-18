# PRODUCTION-HARDENING-01-PH03 — PostgreSQL Matrix Execution + Launch Checklist

**Mode:** Audit + optional PG parity tests. **No accounting / GL / posting behavior change.**

**Date:** 2026-06-05  
**Authority:** Implements slice **PRODUCTION-HARDENING-01-PH03** from [PH-02 audit §7](./PRODUCTION_HARDENING_01_PH02_COMMIT_CHARACTERIZATION_AUDIT.md).  
**Tag:** `production-hardening-01-ph03-pg-matrix-execution`

**Prerequisites:** [PH-02](./PRODUCTION_HARDENING_01_PH02_COMMIT_CHARACTERIZATION_AUDIT.md) · [FASTAPI-REACT-07](./FASTAPI_REACT_07_PG_BOUNDARY_MATRIX_AUDIT.md) · [POSTGRES_PG_BUILD_DUAL_RUN_PARITY](./POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| PG boundary matrix inventory (machine-readable) | ✅ `registry/pg_matrix_execution_contract.py` |
| `bank_transaction` optional PG parity | ✅ `TestPostgresOptionalBoundaryMatrix` in PH-03 tests |
| `post_equity_movement` optional PG parity | ✅ same |
| Launch-readiness checklist (Streamlit vs API-write) | ✅ Documented below |
| Operator execution guide | ✅ `ERP_TEST_POSTGRES_URL` + `pytest -m optional_postgres` |

**Posting / GL behavior:** **UNCHANGED** — SQLite-only CI remains green; PG tests skip when env unset.

---

## 2. PostgreSQL optional matrix inventory

When `ERP_TEST_POSTGRES_URL` is set (validated disposable test DB — see [P4_1_LOCAL_POSTGRES_VALIDATION](./P4_1_LOCAL_POSTGRES_VALIDATION.md)):

| Flow ID | Family | Write path | Test |
|---------|--------|------------|------|
| **boundary_cash_sale** | `post_cash_sale` | `write_sales.create_and_post_sale` | `test_fastapi_react_07_pg_boundary_matrix.py` |
| **boundary_void_sale** | `void_cascade` | `write_voids.void_record` | `test_fastapi_react_07_pg_boundary_matrix.py` |
| **boundary_bank_deposit** | `bank_transaction` | `write_banking.create_manual_bank_transaction` | `test_production_hardening_01_ph03_pg_matrix_execution.py` |
| **boundary_equity_contribution** | `post_equity_movement` | `post_capital_contribution + audit` | `test_production_hardening_01_ph03_pg_matrix_execution.py` |

**Broader optional PG suite** (schema, migration, reports — not boundary-specific): see `registry/pg_matrix_execution_contract.py` → `OPTIONAL_POSTGRES_TEST_FILES`.

**Skipped without env:** 29+ tests across the repo use `@pytest.mark.optional_postgres` and skip safely when `ERP_TEST_POSTGRES_URL` is unset.

---

## 3. Launch-readiness checklist

### Streamlit-primary launch (current production path)

| Gate | Status | Notes |
|------|--------|-------|
| Core ERP + accounting engine | ✅ Ready | Streamlit `app.py` primary |
| Full SQLite pytest suite | ✅ Required | `pytest tests/` green without PG env |
| PostgreSQL runtime cutover | ✅ Testing | Flag-gated; SQLite rollback preserved |
| React / FastAPI API-write cutover | ⬜ Not required | Optional parallel path |

**Verdict:** **0 launch blockers** for Streamlit-only operation.

### FastAPI/React API-write production path

| Gate | Status | Notes |
|------|--------|-------|
| P0 commit characterization (all 14 families) | ✅ Complete | PH-02 closed scaffold gap |
| P2 API boundary commit count (9 write suites) | ✅ Complete | FR-08–16 |
| Optional PG boundary matrix | 🟡 Partial | 4 flows pinned; operator must run with `ERP_TEST_POSTGRES_URL` before cutover |
| Per-route `ERP_API_WRITE_*` flags | ⬜ Operator | Each write family off by default |
| `VITE_ERP_REACT_PAGES=1` | ⬜ Operator | React read pages |
| `COMMIT_MODE_*=boundary` production flip | ⬜ Operator | PH-04 characterization; **not flipped in this slice** |
| TD-PS-03 route-layer DTO cleanup | ⬜ Deferred | Not a Streamlit launch blocker |

**Verdict:** **2 production blockers** (COMMIT_MODE flip + operator flag rollout) · **1 ops blocker** (PG matrix must be green on disposable test DB before API-primary cutover).

---

## 4. Operator execution guide

```bash
# 1. Full SQLite baseline (required — no PG env)
pytest tests/ -q

# 2. Optional PG boundary matrix (disposable test DB only)
export ERP_TEST_POSTGRES_URL='postgresql+psycopg://localhost/erp_pytest'
pytest tests/test_fastapi_react_07_pg_boundary_matrix.py \
  tests/test_production_hardening_01_ph03_pg_matrix_execution.py \
  -m optional_postgres -q

# 3. Broader optional PG confidence (optional)
pytest -m optional_postgres -q
```

**Safety:** Never point `ERP_TEST_POSTGRES_URL` at production `erp_data.db`. See [POSTGRES_PG_BUILD_DUAL_RUN_PARITY](./POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md).

---

## 5. Deferred (out of PH-03 scope)

| Item | Notes |
|------|-------|
| **PRODUCTION-HARDENING-04** | `COMMIT_MODE_*` operator rollout characterization |
| **PRODUCTION-HARDENING-05** | Epic closure gate |
| **production COMMIT_MODE_* flip** | Operator rollout after PH-04 green |
| **TD-PS-03** | Route-layer DTO adapters |
| **CI optional_postgres job** | Requires managed test DB provisioning |

---

## 6. What must NOT change (verified)

- Default commit mode (`internal`)
- Journal math and GL pairs
- Streamlit primary UI
- No production `COMMIT_MODE_*` flip
- No Docker file edits
- `DATABASE_URL` / production SQLite unchanged by PG tests

---

## 7. Test plan

```bash
pytest tests/test_production_hardening_01_ph03_pg_matrix_execution.py -q
pytest tests/ -q
# With ERP_TEST_POSTGRES_URL:
pytest tests/test_production_hardening_01_ph03_pg_matrix_execution.py \
  tests/test_fastapi_react_07_pg_boundary_matrix.py -m optional_postgres -q
```

---

## 8. Recommendation / next slice

**PRODUCTION-HARDENING-01-PH04** — `COMMIT_MODE_*` operator rollout characterization (test/staging only; no production flip without operator).
