# FASTAPI-REACT-45 — End-of-Day Close Read Page

**Mode:** React read page expansion with thin P1 EOD close history API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-45** from [FASTAPI_REACT_44 audit §7](./FASTAPI_REACT_44_REACT_READ_MY_ACCOUNT_AUDIT.md).  
**Tag:** `fastapi-react-45-react-read-eod-close`

**Prerequisites:** [FASTAPI-REACT-44](./FASTAPI_REACT_44_REACT_READ_MY_ACCOUNT_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| End-of-Day Close page (`/closings/eod`) | ✅ `EodClosePage` |
| `GET /api/v1/end-of-day-closes` | ✅ `read_eod_closes.compute_eod_closes_list` |

**Accounting / GL behavior:** **UNCHANGED** — read-only close history. Close and void actions remain Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/closings/eod` | `EodClosePage` | `/api/v1/end-of-day-closes` |

**Real React read routes:** 34 (was 33). **Placeholder routes:** 8 (was 9).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (today checklist, close day, void)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)
- Guard uses `close_day` (matches Streamlit history tab)

---

## 5. Deferred (out of FR-45 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-46** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_45_react_read_eod_close.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-46** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (cash recon, recurring expenses, recipes, etc.).
