# RECEIPT-AI-02-IMPL-3 — Persistent Learning Map

**Status:** Implemented (2026-06). **Table + store only** — `record_approval` / `suggest_for_vendor` work against SQLite; **not** wired to `approve_expense_draft` yet.

## What was added

- **`models.ReceiptLearningMap`** — additive table `receipt_learning_map` with unique `(company_id, signature_type, signature_key, target_kind, target_id, target_value)`.
- **`services/receipt_learning_store.py`** — `PersistentLearningStore` implementing the `LearningStore` protocol from `services/receipt_learning.py`.
- **Schema indexes** in `migrate_schema()` and `alembic/versions/0001_baseline.py` (`ix_rcptlearn_company_id`, `ix_rcptlearn_signature`).
- **`tests/test_receipt_ai_02_impl_3_learning_map.py`**

## Signature types

| `signature_type` | `target_kind` | Stored in |
|---|---|---|
| `vendor_category` | `category_id` | `target_id` |
| `vendor_subcategory` | `subcategory_id` | `target_id` |
| `vendor_payment` | `payment_method` | `target_value` |
| `item_product` | `product_id` | `target_id` |
| `source_format` | `document_type` | `target_value` |

The learning service still passes string `target_value`; the store encodes/decodes to `target_kind` + `target_id` / `target_value`. Unused columns use sentinels (`target_id=-1`, `target_value=""`) so SQLite enforces the composite unique key.

## Behavior (unchanged service API)

- `record_approval(store, event)` increments map rows via `record_approval_hit`.
- `suggest_for_vendor(store, company_id, vendor)` reads active rows — company-scoped.
- Blank/unknown vendor → no rows written.
- Payment suggestions remain **advisory only** (`advisory_only=True`).
- `confidence_cached` refreshed on write for all targets sharing a signature.

## Not in this slice

- No hook from `approve_expense_draft` → `record_approval`.
- No auto-post, OCR, AI API, POS AI, or cash/card reconciliation.
- No posting / `ExpenseRecord` / `JournalEntry` behavior change.
- No UI change.

## Next slices

- **RECEIPT-AI-02-IMPL-4** — void-aware reconciliation (decrement / correction_count).
- **RECEIPT-AI-02-IMPL-5** — surface learned suggestions in capture UI (still approval-first).

## Run

```bash
pytest tests/test_receipt_ai_02_learning_service.py
pytest tests/test_receipt_ai_02_impl_3_learning_map.py
pytest
```
