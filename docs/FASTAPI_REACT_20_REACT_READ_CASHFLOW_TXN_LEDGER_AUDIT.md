# FASTAPI-REACT-20 — Cash Flow + Transaction Ledger Read Pages

**Mode:** Read-only SPA pages behind feature flag. Thin P1 read API extraction included.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-20** from [FASTAPI_REACT_19 audit §7](./FASTAPI_REACT_19_REACT_READ_REPORTS_HUB_AUDIT.md).  
**Tag:** `fastapi-react-20-react-read-cashflow-txn-ledger`

**Prerequisites:** [FASTAPI-REACT-06](./FASTAPI_REACT_06_REACT_PAGES_AUDIT.md) · P1 read API spine

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Cash flow (`/reports/cash-flow`) | ✅ `/api/v1/reports/cash-flow` |
| Transaction ledger (`/transactions/ledger`) | ✅ `/api/v1/transactions` |
| Service extraction | ✅ `services/read_transaction_history.py` (Streamlit delegates) |
| Feature flag | ✅ `VITE_ERP_REACT_PAGES=1` (unchanged) |

**Accounting / GL behavior:** **UNCHANGED** — read extraction only; no posting kernel edits.

---

## 2. Page inventory

| React path | Component | P1 read APIs |
|------------|-----------|--------------|
| `/reports/cash-flow` | `CashFlowPage` | `/api/v1/reports/cash-flow` |
| `/transactions/ledger` | `TransactionLedgerPage` | `/api/v1/transactions` |

Contract: `registry/react_pages_contract.py` → `REAL_PAGE_ROUTES` (11 pages total).

Reports hub (`ReportsPage`) updated with links to both routes.

---

## 3. P1 read API additions (thin extraction)

| Path | Service |
|------|---------|
| `/api/v1/reports/cash-flow` | `read_reports.compute_cash_flow` |
| `/api/v1/transactions` | `read_transaction_history.compute_transaction_history_page` |

Frozen in `registry/api_read_contract.py`. Streamlit `_txh_fetch_filtered_rows` delegates to the same service.

---

## 4. Feature flag (unchanged from FR-06)

| Env | Effect |
|-----|--------|
| `VITE_ERP_REACT_PAGES` | Shell + read pages |

---

## 5. What must NOT change (verified)

- Streamlit primary UI (presentation unchanged; data path shared)
- No GL / posting kernel edits
- `apiGet` only on new React pages
- Docker untouched

---

## 6. Deferred (out of FR-20 scope)

| Item | Notes |
|------|-------|
| **chart-of-accounts picker** | GL ledger still uses `account_id` query |
| **partner picker** | Partner statement uses numeric `partner_id` |
| **full txh Streamlit filters** | API exposes search + type; method/category filters remain Streamlit-only |

---

## 7. Test plan

```bash
pytest tests/test_fastapi_react_20_react_read_cashflow_txn_ledger.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 8. Recommendation / next slice

**FASTAPI-REACT-21** — chart-of-accounts / partner pickers, or write-side match-type payload forms.
