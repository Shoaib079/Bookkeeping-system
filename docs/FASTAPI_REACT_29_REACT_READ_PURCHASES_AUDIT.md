# FASTAPI-REACT-29 — Purchases Read Page

**Mode:** React read page expansion with thin P1 list API extraction.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-29** from [FASTAPI_REACT_28 audit §7](./FASTAPI_REACT_28_REACT_READ_CUSTOMERS_AUDIT.md).  
**Tag:** `fastapi-react-29-react-read-purchases`

**Prerequisites:** [FASTAPI-REACT-28](./FASTAPI_REACT_28_REACT_READ_CUSTOMERS_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Purchases page (`/purchases`) | ✅ `PurchasesPage` |
| `GET /api/v1/purchases` | ✅ `read_purchases.compute_purchases_list` |

**Accounting / GL behavior:** **UNCHANGED** — list reads only. POST write route unchanged.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/purchases` | `PurchasesPage` | `/api/v1/purchases` |

GET list coexists with POST write on `/api/v1/purchases` (different methods).

**Real React read routes:** 18 (was 17). **Placeholder routes:** 23 (was 24).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI
- No GL / posting kernel edits
- Write POST bodies and feature flags unchanged
- Read page uses `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-29 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-30** | Further read page expansion |
| **bank accounts read page** | `/banking/accounts` or similar remains PlaceholderPage |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_29_react_read_purchases.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-30** — bank accounts read page (reuse `/api/v1/bank-accounts`) or production `COMMIT_MODE_*` characterization flip.
