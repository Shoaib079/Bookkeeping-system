# FASTAPI-REACT-28 — Customers Read Page

**Mode:** React read page expansion with thin P1 list API extraction.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-28** from [FASTAPI_REACT_27 audit §7](./FASTAPI_REACT_27_REACT_READ_WORKERS_AUDIT.md).  
**Tag:** `fastapi-react-28-react-read-customers`

**Prerequisites:** [FASTAPI-REACT-27](./FASTAPI_REACT_27_REACT_READ_WORKERS_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Customers page (`/customers`) | ✅ `CustomersPage` |
| `GET /api/v1/customers` | ✅ `read_customers.compute_customers_list` |

**Accounting / GL behavior:** **UNCHANGED** — list reads only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/customers` | `CustomersPage` | `/api/v1/customers` |

**Real React read routes:** 17 (was 16). **Placeholder routes:** 24 (was 25).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-28 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-29** | Further read page expansion |
| **purchases read page** | `/purchases` remains PlaceholderPage |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_28_react_read_customers.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-29** — purchases read page (need thin P1 read API) or production `COMMIT_MODE_*` characterization flip.
