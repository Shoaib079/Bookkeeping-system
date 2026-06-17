# FASTAPI-REACT-24 — Receivable Sale + Allocation Pickers

**Mode:** Final write-tab picker UX for receivable payments and closing void. Thin P1 list API extraction included.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-24** from [FASTAPI_REACT_23 audit §10](./FASTAPI_REACT_23_REACT_WRITE_RECON_FORMS_AUDIT.md).  
**Tag:** `fastapi-react-24-react-write-final-pickers`

**Prerequisites:** [FASTAPI-REACT-13](./FASTAPI_REACT_13_REACT_WRITE_RECEIVABLE_PAYMENT_AUDIT.md) · [FASTAPI-REACT-16](./FASTAPI_REACT_16_REACT_WRITE_RECON_CLOSING_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Credit sale picker (receivable tab) | ✅ `/api/v1/receivable-sales` |
| Profit allocation picker (void closing) | ✅ `/api/v1/profit-allocations` |
| Write POST bodies | ✅ unchanged |

**Accounting / GL behavior:** **UNCHANGED** — list reads only.

---

## 2. Picker inventory

| Write tab | Field | Component | List API |
|-----------|-------|-----------|----------|
| Receivable payment | Credit sale | `ReceivableSalePicker` | `/api/v1/receivable-sales` |
| Closing (void allocation) | Profit allocation | `ProfitAllocationPicker` | `/api/v1/profit-allocations` |

---

## 3. P1 read API additions

| Path | Service |
|------|---------|
| `/api/v1/receivable-sales` | `read_receivable_sales.compute_receivable_sales_list` |
| `/api/v1/profit-allocations` | `read_profit_allocations.compute_profit_allocations_list` |

Frozen in `registry/api_read_contract.py`. GET list coexists with POST write on `/api/v1/profit-allocations` (different methods).

---

## 4. Feature flags (unchanged)

Receivable tab: `VITE_ERP_REACT_WRITE_RECEIVABLE_PAYMENTS` + `ERP_API_WRITE_RECEIVABLE_PAYMENTS`.  
Closing tab: `VITE_ERP_REACT_WRITE_CLOSING` + `ERP_API_WRITE_CLOSING`.

---

## 5. Client validation

| Case | Message |
|------|---------|
| Missing credit sale | `Select a credit sale.` |
| Missing allocation | `Select a profit allocation.` |

---

## 6. What must NOT change (verified)

- Streamlit primary UI
- No GL / posting kernel edits
- No new write API routes
- `apiGet` in pickers; `apiPost` only in `writeClient.ts`

---

## 7. Deferred (out of FR-24 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-25** | React read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 8. Write picker track complete

All `NewTransactionPage` write tabs now use pickers instead of raw numeric ids for master-data references. Remaining React work is **read page expansion** (30 placeholder routes) or **ops** slices.

---

## 9. Test plan

```bash
pytest tests/test_fastapi_react_24_react_write_final_pickers.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 10. Recommendation / next slice

**FASTAPI-REACT-25** — React read page expansion (domain-by-domain) or production `COMMIT_MODE_*` characterization flip.
