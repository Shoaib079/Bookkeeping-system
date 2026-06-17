# FASTAPI-REACT-25 — Chart of Accounts + Vendors Read Pages

**Mode:** React read page expansion. No new P1 read APIs — reuses existing list endpoints from FR-21 and FR-23.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-25** from [FASTAPI_REACT_24 audit §10](./FASTAPI_REACT_24_REACT_WRITE_FINAL_PICKERS_AUDIT.md).  
**Tag:** `fastapi-react-25-react-read-coa-vendors`

**Prerequisites:** [FASTAPI-REACT-21](./FASTAPI_REACT_21_REACT_READ_PICKERS_AUDIT.md) (COA list API) · [FASTAPI-REACT-23](./FASTAPI_REACT_23_REACT_WRITE_RECON_FORMS_AUDIT.md) (vendors list API)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Chart of Accounts page (`/books/chart-of-accounts`) | ✅ `ChartOfAccountsPage` |
| Vendors page (`/vendors`) | ✅ `VendorsPage` |
| New P1 read APIs | ❌ none — existing GET list endpoints |

**Accounting / GL behavior:** **UNCHANGED** — read-only list pages.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/books/chart-of-accounts` | `ChartOfAccountsPage` | `/api/v1/chart-of-accounts` |
| `/vendors` | `VendorsPage` | `/api/v1/vendors` |

COA rows link to `/books/general-ledger?account_id={id}` for drill-down.

**Real React read routes:** 14 (was 12). **Placeholder routes:** 28 (was 30).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`. Routes remain `PlaceholderPage` when flag off.

---

## 4. What must NOT change (verified)

- Streamlit primary UI
- No GL / posting kernel edits
- No new write API routes
- Read pages use `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-25 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-26** | Further read page expansion |
| **sales read page** | `/sales` remains PlaceholderPage |
| **expenses read page** | `/expenses` remains PlaceholderPage |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_25_react_read_coa_vendors.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-26** — sales/expenses read pages (need thin P1 read APIs) or production `COMMIT_MODE_*` characterization flip.
