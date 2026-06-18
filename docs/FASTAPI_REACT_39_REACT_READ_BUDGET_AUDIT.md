# FASTAPI-REACT-39 — Budget vs Actual Read Page

**Mode:** React read page expansion with thin P1 budget report API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-39** from [FASTAPI_REACT_38 audit §7](./FASTAPI_REACT_38_REACT_READ_INVENTORY_AUDIT.md).  
**Tag:** `fastapi-react-39-react-read-budget`

**Prerequisites:** [FASTAPI-REACT-38](./FASTAPI_REACT_38_REACT_READ_INVENTORY_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Budget page (`/books/budget`) | ✅ `BudgetPage` |
| `GET /api/v1/reports/budget-vs-actual` | ✅ `read_budget.compute_budget_vs_actual` |

**Accounting / GL behavior:** **UNCHANGED** — read-only monthly budget vs GL actual comparison. Budget entry forms remain Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/books/budget` | `BudgetPage` | `/api/v1/reports/budget-vs-actual` |

**Real React read routes:** 28 (was 27). **Placeholder routes:** 14 (was 15).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (budget entry forms)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-39 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-40** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_39_react_read_budget.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-40** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (permissions, company settings, year-end close, backup-restore, etc.).
