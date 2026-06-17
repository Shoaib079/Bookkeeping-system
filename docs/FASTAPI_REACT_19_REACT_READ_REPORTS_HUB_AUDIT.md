# FASTAPI-REACT-19 — Reports Hub + Profit & Loss Read Pages

**Mode:** Read-only SPA pages behind feature flag. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-19** from [FASTAPI_REACT_18 audit §7](./FASTAPI_REACT_18_REACT_READ_PARTNER_BANKING_AUDIT.md).  
**Tag:** `fastapi-react-19-react-read-reports-hub`

**Prerequisites:** [FASTAPI-REACT-06](./FASTAPI_REACT_06_REACT_PAGES_AUDIT.md) · P1 read API spine

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Reports hub (`/reports`) | ✅ Navigation + MTD P&L summary via `/api/v1/reports/profit-loss` |
| Profit & Loss (`/reports/profit-loss`) | ✅ `/api/v1/reports/profit-loss` |
| Transaction ledger (`/transactions/ledger`) | ⬜ **Deferred** — no P1 read endpoint (Streamlit-only `_txh_fetch_filtered_rows`) |
| Feature flag | ✅ `VITE_ERP_REACT_PAGES=1` (unchanged) |

**Accounting / GL behavior:** **UNCHANGED** — React consumes frozen P1 read endpoints only.

---

## 2. Page inventory

| React path | Component | P1 read APIs |
|------------|-----------|--------------|
| `/reports` | `ReportsPage` | `/api/v1/reports/profit-loss` (hub summary) |
| `/reports/profit-loss` | `ProfitLossPage` | `/api/v1/reports/profit-loss` |

Hub links (no extra API) to existing React read routes: Balance Sheet, Receivables, Payables.

Contract: `registry/react_pages_contract.py` → `REAL_PAGE_ROUTES` (9 pages total with FR-06/17/18).

---

## 3. Feature flag (unchanged from FR-06)

| Env | Effect |
|-----|--------|
| `VITE_ERP_REACT_PAGES` | Shell + read pages |

No new flags.

---

## 4. What must NOT change (verified)

- Streamlit primary UI
- No new FastAPI routes
- No GL / posting kernel edits
- `apiGet` only in read client
- Docker untouched

---

## 5. Deferred (out of FR-19 scope)

| Item | Notes |
|------|-------|
| **transaction ledger read page** | `/transactions/ledger` — needs `read_transaction_history` FastAPI extraction (not in P1 spine) |
| **cash flow read page** | `/reports/cash-flow` — no `/api/v1/reports/cash-flow` in frozen read contract |
| **chart-of-accounts picker** | Ledger still uses `account_id` query |
| **partner picker** | Partner statement uses numeric `partner_id` |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_19_react_read_reports_hub.py -q
pytest tests/test_fastapi_react_18_react_read_partner_banking.py -q
pytest tests/ -q
```

**Dev smoke:**
```bash
cd frontend && VITE_ERP_REACT_PAGES=1 npm run dev
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-20** — transaction ledger read page (requires P1 read API extraction first) or cash-flow read page when endpoint ships.
