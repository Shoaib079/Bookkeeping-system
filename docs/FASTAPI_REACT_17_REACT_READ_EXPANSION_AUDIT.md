# FASTAPI-REACT-17 — Read Page Expansion (Balance Sheet + AR/AP)

**Mode:** Read-only SPA pages behind feature flag. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-17** from [FASTAPI_REACT_16 audit §8](./FASTAPI_REACT_16_REACT_WRITE_RECON_CLOSING_AUDIT.md).  
**Tag:** `fastapi-react-17-react-read-expansion`

**Prerequisites:** [FASTAPI-REACT-06](./FASTAPI_REACT_06_REACT_PAGES_AUDIT.md) · P1 read API spine

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Balance sheet (`/reports/balance-sheet`) | ✅ `/api/v1/reports/balance-sheet` |
| Receivables (`/receivables`) | ✅ `/api/v1/receivables` |
| Payables (`/payables`) | ✅ `/api/v1/payables` |
| Feature flag | ✅ `VITE_ERP_REACT_PAGES=1` (unchanged) |
| Partner statement / banking readiness | ⬜ **Deferred** — FR-18 |

**Accounting / GL behavior:** **UNCHANGED** — React consumes frozen P1 read endpoints only.

---

## 2. Page inventory

| React path | Component | P1 read APIs |
|------------|-----------|--------------|
| `/reports/balance-sheet` | `BalanceSheetPage` | `/api/v1/reports/balance-sheet` |
| `/receivables` | `ReceivablesPage` | `/api/v1/receivables` |
| `/payables` | `PayablesPage` | `/api/v1/payables` |

Contract: `registry/react_pages_contract.py` → `REAL_PAGE_ROUTES` (5 pages total with FR-06).

---

## 3. Feature flag (unchanged from FR-06)

| Env | Effect |
|-----|--------|
| `VITE_ERP_REACT_PAGES` | Shell + read pages |

No new flags. Write tabs remain on separate `VITE_ERP_REACT_WRITE_*` gates.

---

## 4. What must NOT change (verified)

- Streamlit primary UI
- No new FastAPI routes
- No GL / posting kernel edits
- `apiGet` only in read client (no write methods on new pages)
- Docker untouched

---

## 5. Deferred (out of FR-17 scope)

| Item | Notes |
|------|-------|
| **partner statement page** | `/api/v1/partners/{id}/statement` — FR-18 |
| **banking readiness page** | `/api/v1/banking/readiness` — FR-18 |
| **chart-of-accounts picker** | Ledger still uses `account_id` query |
| **full match-type payload forms** | Write-side — FR-18+ |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_17_react_read_expansion.py -q
pytest tests/test_fastapi_react_06_react_pages.py -q
pytest tests/ -q
```

**Dev smoke:**
```bash
cd frontend && VITE_ERP_REACT_PAGES=1 npm run dev
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-18** — partner statement + banking readiness read pages.
