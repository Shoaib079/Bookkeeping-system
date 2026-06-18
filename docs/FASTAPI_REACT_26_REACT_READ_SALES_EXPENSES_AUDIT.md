# FASTAPI-REACT-26 — Sales + Expenses Read Pages

**Mode:** React read page expansion with thin P1 list API extraction.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-26** from [FASTAPI_REACT_25 audit §7](./FASTAPI_REACT_25_REACT_READ_COA_VENDORS_AUDIT.md).  
**Tag:** `fastapi-react-26-react-read-sales-expenses`

**Prerequisites:** [FASTAPI-REACT-25](./FASTAPI_REACT_25_REACT_READ_COA_VENDORS_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Sales page (`/sales`) | ✅ `SalesPage` |
| Expenses page (`/expenses`) | ✅ `ExpensesPage` |
| `GET /api/v1/sales` | ✅ `read_sales.compute_sales_list` |
| `GET /api/v1/expenses` | ✅ `read_expenses.compute_expenses_list` |

**Accounting / GL behavior:** **UNCHANGED** — list reads only. POST write routes unchanged.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/sales` | `SalesPage` | `/api/v1/sales` |
| `/expenses` | `ExpensesPage` | `/api/v1/expenses` |

GET list coexists with POST write on same paths (different methods).

**Real React read routes:** 15 (was 13). **Placeholder routes:** 26 (was 28).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI
- No GL / posting kernel edits
- Write POST bodies and feature flags unchanged
- Read pages use `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-26 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-27** | Further read page expansion |
| **workers read page** | `/workers` remains PlaceholderPage |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_26_react_read_sales_expenses.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-27** — workers read page (reuse `/api/v1/workers`) or production `COMMIT_MODE_*` characterization flip.
