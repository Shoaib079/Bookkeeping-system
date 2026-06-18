# FASTAPI-REACT-35 — Opening Balances Read Page

**Mode:** React read page expansion with thin P1 status API extraction.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-35** from [FASTAPI_REACT_34 audit §7](./FASTAPI_REACT_34_REACT_READ_RECON_HEALTH_AUDIT.md).  
**Tag:** `fastapi-react-35-react-read-opening-balances`

**Prerequisites:** [FASTAPI-REACT-34](./FASTAPI_REACT_34_REACT_READ_RECON_HEALTH_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Opening balances page (`/books/opening-balances`) | ✅ `OpeningBalancesPage` |
| `GET /api/v1/opening-balances` | ✅ `read_opening_balances.compute_opening_balances_status` |

**Accounting / GL behavior:** **UNCHANGED** — read-only OB equity summary and posting status. OB posting forms remain Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/books/opening-balances` | `OpeningBalancesPage` | `/api/v1/opening-balances` |

**Real React read routes:** 24 (was 23). **Placeholder routes:** 18 (was 19).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (including OB posting forms)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-35 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-36** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_35_react_read_opening_balances.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-36** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder.
