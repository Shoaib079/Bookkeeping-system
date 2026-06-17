# FASTAPI-REACT-23 — Reconcile/Closing Pickers + Match-Type Forms

**Mode:** Write-tab UX completion for reconcile/closing. Thin P1 list API extraction included.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-23** from [FASTAPI_REACT_22 audit §9](./FASTAPI_REACT_22_REACT_WRITE_PICKERS_AUDIT.md).  
**Tag:** `fastapi-react-23-react-write-recon-forms`

**Prerequisites:** [FASTAPI-REACT-16](./FASTAPI_REACT_16_REACT_WRITE_RECON_CLOSING_AUDIT.md) · FR-22 write pickers

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Statement row picker (reconcile tab) | ✅ `/api/v1/bank-statement-rows` |
| Fiscal period picker (closing tab) | ✅ `/api/v1/fiscal-periods` |
| Vendor picker (vendor_outflow match) | ✅ `/api/v1/vendors` |
| Full match-type payload forms | ✅ all 8 `ALLOWED_RECONCILIATION_MATCH_TYPES` |
| Reused pickers | ✅ COA · partner · worker · bank (credit card) |

**Accounting / GL behavior:** **UNCHANGED** — list reads + existing P2 match/closing POST bodies.

---

## 2. Picker inventory

| Write tab | Field | Component | List API |
|-----------|-------|-----------|----------|
| Reconcile | Statement row | `StatementRowPicker` | `/api/v1/bank-statement-rows` |
| Reconcile | Credit account (`generic_deposit`) | `CoaAccountPicker` | `/api/v1/chart-of-accounts` |
| Reconcile | Vendor (`vendor_outflow`) | `VendorPicker` | `/api/v1/vendors` |
| Reconcile | Partner / worker / CC account | reused FR-21/22 pickers | partners · workers · bank-accounts |
| Closing | Fiscal period | `FiscalPeriodPicker` | `/api/v1/fiscal-periods` |

---

## 3. Match-type payload forms

| `match_type` | Form fields |
|--------------|-------------|
| `generic_deposit` | COA credit account (name sent to API) |
| `bank_charge` | optional `charge_subtype` |
| `deposit_clearing` | comma-separated `sale_ids`, optional `settlement_row_id`, `confirm_inferred_fee` |
| `vendor_outflow` | vendor, optional payable id, expense category, create expense flag |
| `partner` | partner + movement type |
| `worker` | worker + movement type; salary fields when `Salary` |
| `equity` | `equity_kind` select |
| `cc_bill_payment` | credit card bank account (`kind=credit_card`) |

---

## 4. P1 read API additions

| Path | Service |
|------|---------|
| `/api/v1/bank-statement-rows` | `read_bank_statement_rows.compute_bank_statement_rows_list` |
| `/api/v1/fiscal-periods` | `read_fiscal_periods.compute_fiscal_periods_list` |
| `/api/v1/vendors` | `read_vendors.compute_vendors_list` |

Frozen in `registry/api_read_contract.py`.

---

## 5. Feature flags (unchanged)

| Env | Effect |
|-----|--------|
| `VITE_ERP_REACT_WRITE_RECONCILIATION` | Reconcile tab |
| `VITE_ERP_REACT_WRITE_CLOSING` | Closing tab |
| `ERP_API_WRITE_RECONCILIATION` / `ERP_API_WRITE_CLOSING` | 404 when off |

---

## 6. Client validation

| Case | Message |
|------|---------|
| Missing statement row | `Select a statement row.` |
| Missing fiscal period | `Select a fiscal period.` |
| `generic_deposit` without account | `Select a credit account for generic deposit.` |
| `deposit_clearing` without sale ids | `Enter one or more sale ids (comma-separated).` |
| `vendor_outflow` without vendor | `Select a vendor.` |
| `cc_bill_payment` without card account | `Select a credit card account.` |

---

## 7. What must NOT change (verified)

- Streamlit primary UI
- No GL / posting kernel edits
- No new write API routes
- `apiGet` in pickers; `apiPost` only in `writeClient.ts`
- Docker untouched

---

## 8. Deferred (out of FR-23 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-24** | Receivable credit sale picker |
| **allocation id picker** | Closing void-allocation tab |
| **production COMMIT_MODE_* flip** | Ops slice |

---

## 9. Test plan

```bash
pytest tests/test_fastapi_react_23_react_write_recon_forms.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 10. Recommendation / next slice

**FASTAPI-REACT-24** — receivable sale picker + allocation picker, or expand React read page coverage.
