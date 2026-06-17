# FASTAPI-REACT-18 — Partner Statement + Banking Readiness (Read Pages)

**Mode:** Read-only SPA pages behind feature flag. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-18** from [FASTAPI_REACT_17 audit §7](./FASTAPI_REACT_17_REACT_READ_EXPANSION_AUDIT.md).  
**Tag:** `fastapi-react-18-react-read-partner-banking`

**Prerequisites:** [FASTAPI-REACT-06](./FASTAPI_REACT_06_REACT_PAGES_AUDIT.md) · P1 read API spine

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Partner statement (`/partners`) | ✅ `/api/v1/partners/{partner_id}/statement` |
| Banking readiness (`/banking`) | ✅ `/api/v1/banking/readiness` |
| Feature flag | ✅ `VITE_ERP_REACT_PAGES=1` (unchanged) |
| Partner picker / COA picker | ⬜ **Deferred** — FR-19+ |

**Accounting / GL behavior:** **UNCHANGED** — React consumes frozen P1 read endpoints only.

---

## 2. Page inventory

| React path | Component | P1 read APIs |
|------------|-----------|--------------|
| `/partners` | `PartnerStatementPage` | `/api/v1/partners/{partner_id}/statement` |
| `/banking` | `BankingReadinessPage` | `/api/v1/banking/readiness` |

Contract: `registry/react_pages_contract.py` → `REAL_PAGE_ROUTES` (7 pages total with FR-06/17).

Partner statement uses query params `partner_id`, `from_date`, `to_date` (partner id also in API path).

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

## 5. Deferred (out of FR-18 scope)

| Item | Notes |
|------|-------|
| **chart-of-accounts picker** | Ledger still uses `account_id` query |
| **partner picker** | Statement page uses numeric `partner_id` input |
| **transaction ledger read page** | `/transactions/ledger` — FR-19+ |
| **full match-type payload forms** | Write-side — separate write slice |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_18_react_read_partner_banking.py -q
pytest tests/test_fastapi_react_17_react_read_expansion.py -q
pytest tests/ -q
```

**Dev smoke:**
```bash
cd frontend && VITE_ERP_REACT_PAGES=1 npm run dev
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-19** — transaction ledger read page + reports hub, or write-side match-type payload forms (operator choice).
