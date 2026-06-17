# FASTAPI-REACT-07 — PG Boundary Matrix / TD-PS-01 Characterization

**Mode:** Verification + contract closure. **No accounting behavior change.**

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-07** from [FASTAPI_REACT_06 audit §9](./FASTAPI_REACT_06_REACT_PAGES_AUDIT.md).  
**Tag:** `fastapi-react-07-pg-boundary-matrix`

**Prerequisites:** [FASTAPI-REACT-04](./FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md) · P0.5d commit ownership · P2 write API · [POSTGRES_PG_BUILD_DUAL_RUN_PARITY](./POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Commit mode characterization (`internal` vs `boundary`) | ✅ Documented |
| API write-path dual-run (posting families) | ✅ `write_sales` + `write_expenses` |
| API write-path dual-run (void family) | ✅ `write_voids` |
| API void failure rollback (closed period guard) | ✅ boundary scope rollback |
| P0 family characterization inventory | ✅ `commit_boundary_contract.py` |
| P2 boundary commit count tests | ✅ 9 write suites |
| PostgreSQL optional matrix | ✅ When `ERP_TEST_POSTGRES_URL` set |
| Production `COMMIT_MODE_*` flip | ⬜ **Deferred** — operator rollout |
| React write pages | ⬜ **Deferred** — FR-08+ |

**Posting / GL behavior:** **UNCHANGED** — default `internal`; no math edits.

---

## 2. Commit ownership modes

| Mode | Owner | When |
|------|-------|------|
| **`internal`** | Kernels + `audit.record_audit` each `session.commit()` | Default for all families |
| **`boundary`** | Outer `boundary_commit_scope` / `posting_boundary_scope` commits once | `COMMIT_MODE_<FAMILY>=boundary` or test override |

**API write path:** `services/write_*` checks `is_boundary_mode(family)` and wraps GL + audit in `boundary_commit_scope`. Entity row commits (e.g. `Sale` insert) may precede the boundary commit — same as Streamlit Add Transaction.

**Streamlit path:** `services/posting_boundary.py` scopes (`posting_boundary_scope`, `void_boundary_scope`, `recon_boundary_scope`).

**Env override:** `COMMIT_MODE_<FAMILY_UPPER>=boundary` (e.g. `COMMIT_MODE_POST_CASH_SALE=boundary`). **Not enabled in production.**

---

## 3. API boundary matrix (SQLite)

Contract: `registry/pg_boundary_contract.py` → `API_MATRIX_*`.

| Flow | Write module | Families | Test |
|------|--------------|----------|------|
| Cash sale post | `write_sales` | `post_cash_sale` | `test_cash_sale_write_service_internal_vs_boundary_parity` |
| Expense post | `write_expenses` | `post_expense` | `test_expense_write_service_internal_vs_boundary_parity` |
| Sale void | `write_voids` | `void_cascade` | `test_void_sale_write_service_internal_vs_boundary_parity` |
| Expense void rollback | `write_voids` | `void_cascade` | `test_void_expense_write_service_boundary_rollback_on_closed_period` |

Helper: `tests/helpers/api_boundary_matrix.py`.

---

## 4. P0 + P2 characterization inventory

**P0 dual-run (kernel / shim):** `registry/commit_boundary_contract.py` → 14 families mapped to `test_fastapi_p0_commit_ownership_*.py`.

**P2 API HTTP boundary commit count:** 9 suites with `Test*BoundaryCommit` classes — one outer boundary commit per successful write.

**Scaffold-only families (risk):** `bank_transaction`, `post_equity_movement` still point at scaffold test — flip requires dedicated parity before production.

---

## 5. PostgreSQL optional matrix

When `ERP_TEST_POSTGRES_URL` is set (validated test DB name):

| Flow | Test | Compares |
|------|------|----------|
| Boundary cash sale via `write_sales` | `test_boundary_cash_sale_sqlite_postgres_parity` | `normalized_parity_summary` |
| Boundary void sale via `write_voids` | `test_boundary_void_sale_sqlite_postgres_parity` | `normalized_parity_summary` |

**Skipped** when env unset — SQLite-only CI remains green.

**Not in scope:** production PostgreSQL cutover, Docker changes, `COMMIT_MODE_*` production flip.

---

## 6. Remaining risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Float money on PostgreSQL | High | MONEY-DECIMAL-01 before production PG |
| Scaffold-only families | Medium | Extend P0 parity before env flip |
| Nested boundary depth | Medium | `boundary_depth()` guard at outer scope only |
| Operator env flip without dual-run green | High | This slice + full pytest before rollout |
| React write pages before boundary proof | Medium | FR-07 gate — pages stay read-only |

---

## 7. Deferred (out of FR-07 scope)

| Item | Notes |
|------|-------|
| **production COMMIT_MODE_* flip** | Operator choice after matrix green |
| **React write pages** | FASTAPI-REACT-08+ |
| **TD-PS-03** | Route-layer DTO adapters |
| **bank_transaction PG matrix** | Scaffold family — extend P0 parity before env flip |
| **equity_movement PG matrix** | Scaffold family — extend P0 parity before env flip |

---

## 8. What must NOT change (verified)

- Default commit mode (`internal`)
- Journal math and GL pairs
- Streamlit primary UI
- React pages flag (`VITE_ERP_REACT_PAGES`)
- Docker files
- No new API routes
- No new React pages

---

## 9. Test plan

```bash
pytest tests/test_fastapi_react_07_api_boundary_matrix.py \
  tests/test_fastapi_react_07_pg_boundary_matrix.py -q

# Optional PG (when ERP_TEST_POSTGRES_URL set):
ERP_TEST_POSTGRES_URL=postgresql://... pytest tests/test_fastapi_react_07_pg_boundary_matrix.py -k postgres -q

pytest tests/ -q
```

---

## 10. Recommendation / next slice

**FASTAPI-REACT-08** — first React write page behind `ERP_API_WRITE_*` + `COMMIT_MODE_*` test overrides **or** extend PG matrix to purchase/reconciliation families.
