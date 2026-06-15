# RECEIPT-AI-02-IMPL-4 — Void-Aware Learning

**Status:** Implemented (2026-06). **Service + store only** — void reversals decrement map rows; **not** wired to `void_expense` yet.

## What was added

- **`record_void_reversal(store, event)`** — decrements mappings for voided posted expenses.
- **`reconcile_voided_receipt_learning`** — alias seam for future void hooks.
- **`should_reconcile_void(event)`** — guards (must be voided, posted, valid vendor).
- **`decrement_approval_hit`** on `LearningStore` / `InMemoryLearningStore` / `PersistentLearningStore`.
- **`learning_event_from_posted_draft(ctx)`** — pure builder from draft + expense record fields.
- **`PostedDraftLearningContext`** — DTO for wiring without Streamlit.
- **`tests/test_receipt_ai_02_impl_4_void_reversal.py`**

## Void behavior

When a previously learned approval is voided:

1. `approval_count` decrements by 1 (never below 0).
2. `correction_count` increments when a decrement actually occurs.
3. `confidence_cached` / suggestion confidence recalculates (lower).
4. Persistent rows with `approval_count == 0` set `is_active = False`.
5. Missing map row → no-op (`records_updated = 0`).

## Source of truth (for future wiring)

| Field | Source |
|---|---|
| `expense_record_id` | `ExpenseDraft.expense_record_id` |
| `vendor_signature` | `ReceiptDraftSuggestion.vendor_signature` or draft description |
| Category/payment | Final `ExpenseDraft` fields at approval |
| `is_voided` | `ExpenseRecord.is_void` after void |

Build events with `learning_event_from_posted_draft(PostedDraftLearningContext(...))`.

## Not in this slice

- No hook in `void_expense` / `approve_expense_draft`.
- No auto-post, OCR, POS AI, cash/card reconciliation.
- No UI or posting behavior change.
- No schema migration (uses existing `ReceiptLearningMap.correction_count`).

## Next slice

- **RECEIPT-AI-02-IMPL-5** — surface learned suggestions in capture UI (approval-first).

## Run

```bash
pytest tests/test_receipt_ai_02_learning_service.py
pytest tests/test_receipt_ai_02_impl_3_learning_map.py
pytest tests/test_receipt_ai_02_impl_4_void_reversal.py
pytest
```
