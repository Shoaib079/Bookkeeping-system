# BANKING-SERVICE-01-BS-03 — CC Bill Payment JE Company Scope

**Status:** Complete (verified closure 2026-06-16)  
**Implementation commit:** `713ac3c` — *BANKING-SERVICE-01 use explicit posting service for card bill JE*  
**Prior tag:** `banking-service-01-bs03-card-bill-posting`  
**Closure tag:** `banking-service-01-bs03-company-card-company-scope`

## Scope

`reconciliation.company_card.post_credit_card_bill_payment` posts GL via **`services.posting.create_journal_entry(..., company_id=company_id)`** — not `app.create_journal_entry` or ambient session company.

| Check | Result |
|-------|--------|
| Explicit `company_id` on JE | ✅ |
| GL lookup via `posting_svc.get_account_by_name(..., company_id=company_id)` | ✅ |
| Bank/CC sub-ledger txns stamped `company_id` | ✅ |
| No `app.create_journal_entry` in bill-payment path | ✅ |

## Regression guard

`tests/test_banking_service01_char_cc_bill_je_company_stamp.py` — BS-03 contract + multi-tenant stamp tests (17 tests).

## Out of scope (remaining BANKING debt)

- Other `company_card.py` paths still lazy-import `app` via `_app()` (charge posting, void helpers)
- `match_post.py` `_app()` coupling (TD-POSTING-06)

## Verification

```bash
pytest tests/test_banking_service01_char_cc_bill_je_company_stamp.py
pytest tests/test_cc_bill_payment_void.py
```
