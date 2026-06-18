# FASTAPI-REACT-43 — Year-End Close Read Page

**Mode:** React read page expansion with thin P1 year-end close history API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-43** from [FASTAPI_REACT_42 audit §7](./FASTAPI_REACT_42_REACT_READ_BACKUP_RESTORE_AUDIT.md).  
**Tag:** `fastapi-react-43-react-read-year-end-close`

**Prerequisites:** [FASTAPI-REACT-42](./FASTAPI_REACT_42_REACT_READ_BACKUP_RESTORE_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Year-End Close page (`/books/year-end-close`) | ✅ `YearEndClosePage` |
| `GET /api/v1/year-end-closes` | ✅ `read_year_end_closes.compute_year_end_closes_list` |

**Accounting / GL behavior:** **UNCHANGED** — read-only close history. Close and void actions remain Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/books/year-end-close` | `YearEndClosePage` | `/api/v1/year-end-closes` |

**Real React read routes:** 32 (was 31). **Placeholder routes:** 10 (was 11).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (close-year validation, perform, void)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-43 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-44** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_43_react_read_year_end_close.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-44** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (my account, closings, recipes, etc.).
