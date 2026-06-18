# FASTAPI-REACT-31 — Fiscal Periods Read Page

**Mode:** React read page expansion. No new P1 read APIs — reuses existing list endpoint from FR-23.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-31** from [FASTAPI_REACT_30 audit §7](./FASTAPI_REACT_30_REACT_READ_BANK_ACCOUNTS_AUDIT.md).  
**Tag:** `fastapi-react-31-react-read-fiscal-periods`

**Prerequisites:** [FASTAPI-REACT-23](./FASTAPI_REACT_23_REACT_WRITE_RECON_FORMS_AUDIT.md) (fiscal periods list API)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Fiscal periods page (`/books/fiscal-periods`) | ✅ `FiscalPeriodsPage` |
| New P1 read APIs | ❌ none — existing `GET /api/v1/fiscal-periods` |

**Accounting / GL behavior:** **UNCHANGED** — read-only list page.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/books/fiscal-periods` | `FiscalPeriodsPage` | `/api/v1/fiscal-periods` |

**Real React read routes:** 20 (was 19). **Placeholder routes:** 22 (was 23).

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

## 5. Deferred (out of FR-31 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-32** | Further read page expansion |
| **journal entries read page** | `/books/journal-entries` remains PlaceholderPage |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_31_react_read_fiscal_periods.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-32** — journal entries read page (need thin P1 read API) or production `COMMIT_MODE_*` characterization flip.
