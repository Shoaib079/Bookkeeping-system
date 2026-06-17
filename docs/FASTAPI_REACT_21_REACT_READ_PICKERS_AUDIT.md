# FASTAPI-REACT-21 — COA + Partner Pickers

**Mode:** Read-only picker UX behind feature flag. Thin P1 list API extraction included.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-21** from [FASTAPI_REACT_20 audit §8](./FASTAPI_REACT_20_REACT_READ_CASHFLOW_TXN_LEDGER_AUDIT.md).  
**Tag:** `fastapi-react-21-react-read-pickers`

**Prerequisites:** [FASTAPI-REACT-06](./FASTAPI_REACT_06_REACT_PAGES_AUDIT.md) · P1 read API spine

---

## 1. Executive summary

| Item | Status |
|------|--------|
| COA picker on Ledger (`/books/general-ledger`) | ✅ `/api/v1/chart-of-accounts` |
| Partner picker on Partner Statement (`/partners`) | ✅ `/api/v1/partners` |
| Shared components | ✅ `CoaAccountPicker`, `PartnerPicker` |
| Feature flag | ✅ `VITE_ERP_REACT_PAGES=1` (unchanged) |

**Accounting / GL behavior:** **UNCHANGED** — list reads only; ledger/statement APIs unchanged.

---

## 2. Picker inventory

| Page | Component | List API | Detail API (unchanged) |
|------|-----------|----------|------------------------|
| `LedgerPage` | `CoaAccountPicker` | `/api/v1/chart-of-accounts` | `/api/v1/ledger` |
| `PartnerStatementPage` | `PartnerPicker` | `/api/v1/partners` | `/api/v1/partners/{partner_id}/statement` |

---

## 3. P1 read API additions (thin extraction)

| Path | Service |
|------|---------|
| `/api/v1/chart-of-accounts` | `read_coa.compute_chart_of_accounts_list` |
| `/api/v1/partners` | `read_partners.compute_partners_list` |

Frozen in `registry/api_read_contract.py`.

---

## 4. Feature flag (unchanged from FR-06)

| Env | Effect |
|-----|--------|
| `VITE_ERP_REACT_PAGES` | Shell + read pages + pickers |

---

## 5. What must NOT change (verified)

- Streamlit primary UI
- No GL / posting kernel edits
- `apiGet` only in pickers
- Docker untouched

---

## 6. Deferred (out of FR-21 scope)

| Item | Notes |
|------|-------|
| **bank account picker** | Write tabs still use numeric bank account ids |
| **worker picker** | Worker write tab still uses numeric worker id |
| **standalone COA read page** | `/books/chart-of-accounts` remains PlaceholderPage |
| **full match-type payload forms** | Write-side — separate write slice |

---

## 7. Test plan

```bash
pytest tests/test_fastapi_react_21_react_read_pickers.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 8. Recommendation / next slice

**FASTAPI-REACT-22** — bank account / worker pickers on write tabs, or match-type payload forms.
