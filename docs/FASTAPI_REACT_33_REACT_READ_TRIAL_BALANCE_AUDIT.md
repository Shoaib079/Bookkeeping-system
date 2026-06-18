# FASTAPI-REACT-33 — Trial Balance Read Page

**Mode:** React read page expansion with thin P1 report API extraction.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-33** from [FASTAPI_REACT_32 audit §7](./FASTAPI_REACT_32_REACT_READ_JOURNAL_ENTRIES_AUDIT.md).  
**Tag:** `fastapi-react-33-react-read-trial-balance`

**Prerequisites:** [FASTAPI-REACT-32](./FASTAPI_REACT_32_REACT_READ_JOURNAL_ENTRIES_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Trial balance page (`/books/trial-balance`) | ✅ `TrialBalancePage` |
| `GET /api/v1/reports/trial-balance` | ✅ `read_trial_balance.compute_trial_balance` |

**Accounting / GL behavior:** **UNCHANGED** — read-only aggregation using existing `calculate_account_balance` helpers.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/books/trial-balance` | `TrialBalancePage` | `/api/v1/reports/trial-balance` |

**Real React read routes:** 22 (was 21). **Placeholder routes:** 20 (was 21).

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

## 5. Deferred (out of FR-33 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-34** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_33_react_read_trial_balance.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-34** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (e.g. recon health, opening balances).
