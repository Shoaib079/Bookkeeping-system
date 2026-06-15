# RECEIPT-AI-02-IMPL-1 — Pure Receipt Learning Service

**Status:** Implemented (2026-06). **Learning service only** — no schema, no DB table, no UI, no posting change, no auto-post, no OCR/AI API.

## What was added

- **`services/receipt_learning.py`** — company-scoped learning over an injected `LearningStore` seam.
- **`InMemoryLearningStore`** — test/dev implementation (no persistence).
- **`tests/test_receipt_ai_02_learning_service.py`** — contract + behavioral tests.

## No schema / no table

This slice **does not** create `receipt_learning_map` or any migration. Persistent storage is **RECEIPT-AI-02-IMPL-3** (future).

## Learned mappings

| Signature type | Key | Target |
|---|---|---|
| `vendor_category` | `vendor_signature` | `category_id` |
| `vendor_subcategory` | `vendor_signature` | `subcategory_id` |
| `vendor_payment` | `vendor_signature` | `payment_method` (advisory) |
| `item_product` | `item_text` | `product_id` |
| `source_format` | `source_signature` | `document_type` |

## API

- **`should_learn_from_approval(event)`** — guards: posted (`expense_record_id`), not voided, non-blank vendor, safe category/amount.
- **`record_approval(store, event)`** — increment mappings on approval+post only.
- **`suggest_for_vendor(store, company_id, vendor_signature)`** — company-scoped suggestions + confidence tiers.
- **`calculate_confidence(...)`** — approval_count, consistency, recency placeholder, correction_penalty placeholder.
- **`classify_confidence_tier(confidence, approval_count)`** — `<80` manual · `80–95` prefill · `>95+N` auto-post-eligible · `>99` trusted.

## Safety (locked)

- Learn only from **approved + posted** drafts (`expense_record_id` required).
- Never learn blank/Unknown vendor signatures.
- Never learn payroll/tax/bank-transfer/large-outlier categories.
- Payment learning is **advisory only** — never posts or creates bank transactions.
- Company isolation on every store key.
- Void decrement is **designed** (`is_voided` guard) but **not persisted** yet (IMPL-4).

## Run

```bash
pytest tests/test_receipt_ai_02_learning_audit.py
pytest tests/test_receipt_ai_02_learning_service.py
pytest
```
