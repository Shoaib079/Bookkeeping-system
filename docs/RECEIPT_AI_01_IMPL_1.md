# RECEIPT-AI-01-IMPL-1 — Pure Receipt-AI Service Skeleton

**Status:** Implemented (2026-06). **Pure service only.** No DB writes, no `ExpenseRecord`/`JournalEntry`, no approval/posting, no bank transaction, no network/OCR/AI, no Streamlit, no `app.py`/`models.py` edit, no schema change.

## What was added

- **`services/receipt_ai.py`** — a pure, FastAPI-ready skeleton. The OCR/AI step is an **injected callable** (`ExtractorFn`); this module only *suggests* an expense draft and never posts.
- **`tests/test_receipt_ai_01_service.py`** — fake-extractor tests, vendor normalization, payment detection, suggestion-only mapping, and AST-based purity guarantees.

## DTOs (all frozen + `to_dict()` serializable)

- **`ReceiptLineItem`** — `description`, `quantity?`, `unit_price?`, `amount?`.
- **`ReceiptExtraction`** — `vendor_text?`, `receipt_date?`, `total_amount?`, `tax_amount?`, `currency?`, `line_items`, `confidence`, `raw_text?`, plus payment fields **`payment_method: Literal["Cash","Card","Unknown"]`**, **`payment_confidence: float`**, **`payment_evidence: list[str]`**.
- **`PaymentDetection`** — `payment_method`, `payment_confidence`, `payment_evidence`.
- **`CreateSuggestion`** — `kind ∈ {vendor, category, subcategory, item}`, `label` (a "create-if-missing" hint; never auto-created).
- **`DraftSuggestion`** — maps onto `services.staff_capture.ExpenseDraftInput` (`date`, `amount`, `currency`, `description`, `tx_category_id`, `tx_subcategory_id`) plus `vendor_signature`, advisory payment fields, `payment_prefilled`, `user_must_choose_payment`, `create_suggestions`, `extraction_confidence`.

## Pure functions

- **`normalize_vendor_signature(text)`** — Turkish-fold + uppercase + strip non-alphanumerics → stable key. `"BİM" / "BIM" / "Bim" / "B.İ.M"` → `"BIM"`.
- **`detect_payment_method(text)`** — keyword evidence on a Turkish-folded copy. Cash (`NAKİT/CASH/…`), Card (`POS/VISA/KREDİ KARTI/TEMASSIZ/…`), `Unknown` when no — or **conflicting** — evidence (conflict → low confidence, never a guess).
- **`extract_receipt_with(extractor, …)`** — calls the **injected** extractor; if it left payment empty but provided `raw_text`, backfills via `detect_payment_method` (still no network). The module never self-extracts.
- **`map_extraction_to_draft_suggestion(extraction, …)`** — builds a `DraftSuggestion`. Payment is **prefilled only** when method is Cash/Card and `payment_confidence > 0.6`; otherwise `user_must_choose_payment=True`. Missing vendor/category/items → `CreateSuggestion`s only.
- **`detect_duplicate_by_sha256(sha256, known)`** — advisory dedup over `DraftAttachment.sha256`.

## Phase-1 guarantees (mapping rule)

- Receipt-AI **creates an expense draft first** (suggestion); posting stays on the existing `approve_expense_draft(..., post_fn=…)` path — **not in this slice**.
- Payment method is **advisory only**: high confidence prefills; low/`Unknown` forces user choice. **No auto-post, no bank transaction, no card/bank settlement** based on detection.
- **No silent create** — missing entities return suggestions for the user to confirm.

## Test results

- `python -m py_compile services/receipt_ai.py tests/test_receipt_ai_01_service.py` → **OK**.
- In-sandbox harness (module loaded directly; `services/__init__` pulls sqlalchemy, absent here): **all behavioral checks pass** — vendor variants → `BIM`; `NAKİT`→Cash; `POS/VISA/KREDİ KARTI`→Card; ambiguous/empty → Unknown; conflict → Unknown(<0.6); seam called exactly once; raw_text backfill; high-conf prefill vs low-conf user-choice; missing vendor/category → suggestions only; known item not re-suggested; sha256 dedup; DTOs JSON-serializable.
- **AST purity:** imports only `__future__, dataclasses, datetime, re, typing, unicodedata`; **no** `sqlalchemy/models/app/db` import, **no** network/OCR libs, **no** `create_journal_entry/approve/commit/add/post_*` calls.
- pytest can't execute in-sandbox (no sqlalchemy for `services/__init__`); the test file is standard pytest and runs under the local venv where sqlalchemy is installed.

## No-change confirmation

- **No posting, no schema, no UI, no `app.py`/`models.py`, no auto-post, no bank transaction.** Two files added only (`services/receipt_ai.py`, `tests/test_receipt_ai_01_service.py`) + this doc.

Run locally:
```
pytest tests/test_receipt_ai_01_service.py
pytest tests/test_receipt_ai_01_audit.py
pytest
```
