# RECEIPT-AI-01 — Receipt Upload / OCR / Categorization Pre-Design Audit

**Mode:** Audit only. **No OCR/AI implementation, no AI calls, no schema change, no posting change, no auto-post, no runtime UI change.** Read-only characterization of the structures a future receipt-AI feature would build on.

## Headline

The ERP **already has the exact substrate** receipt-AI needs: an **`ExpenseDraft` + `DraftAttachment` + approve→`post_fn`** pipeline (`services/staff_capture.py`, `models.py:1182-1226`) that is **FastAPI-ready, company-scoped, attachment-aware, and approval-gated**. Receipt-AI should be built as a **suggestion layer that populates an expense draft** and rides the existing approval→post path — **no new posting code and no schema change are required for the approval-first phase.** What does **not** exist yet: any **OCR / AI / image / import** dependency (greenfield, must sit behind a clean seam).

## 1. Current capability map

| Area | State | Evidence |
|---|---|---|
| **Expense draft model** | **Exists** — `ExpenseDraft` (status: draft/submitted/approved/rejected/returned; `expense_record_id` link set on post; category/subcategory, amount, currency, payment_method, description; created_by/reviewed_by/notes; company-scoped) | `models.py:1182-1207` |
| **Receipt attachment** | **Exists** — `DraftAttachment` (file_path, original_name, mime, size_bytes, **sha256**, draft_type+draft_id); jpg/png/webp/pdf, ≤10 MB, ≤5/draft | `models.py:1209-1226`, `services/staff_capture.py:39-55` |
| Draft service | **Exists, FastAPI-ready** — `services/staff_capture.py`: create/update/submit/approve/return/reject + attachment CRUD; explicit `company_id`/`user_id`, serializable DTOs, **no Streamlit** | `services/staff_capture.py:1-58` |
| **Posting seam** | **Approval posts via injected `post_fn`** (`ExpensePostFn`) — posting lives **outside** the service | `services/staff_capture.py:57-58`; `app.py:5673 _staff_capture_post_expense_draft` |
| Draft types | `DraftType` = `expense / salary / sales_total / cash_count` — **extensible** | `services/staff_capture.py:28` |
| Expense posting | `post_expense` → `ExpenseRecord` + `create_journal_entry` (double-entry) | `app.py` posting wrappers |
| Categories | `TransactionCategory` / `TransactionSubcategory` (+ **inline add** UI) | `models.py:479-491`; `test_ux03_inline_category.py` |
| Vendor | `Vendor` (+ **quick-add** UI) | `models.py:254`; `test_vendor_quick_add.py` |
| Items / products | `Product` (company-scoped, SKU) | `models.py:377` |
| Purchases | `Purchase` flow + payable lifecycle | `models.py:271`; `test_purchase_payable_lifecycle.py` |
| Void / reversal | `void_*` → reversing `JournalEntry`; `expense_record_id` lets a posted draft be traced | posting-service void tests |
| **OCR / AI / image / import** | **None** — no tesseract/opencv/Pillow/openai/anthropic/vision deps; only `reportlab` (PDF gen) | `requirements.txt` |

## 2. Reusable components (answer to Q1–Q3)

- **Q2 — Is there already an expense draft model?** **Yes** — `ExpenseDraft`, with a full status lifecycle and an `expense_record_id` posting link.
- **Q3 — Is the staff-expense draft flow reusable for receipt AI?** **Yes, almost entirely.** The draft + attachment + submit/approve/return/reject + **inject-post_fn** pipeline is exactly what receipt-AI needs. A receipt becomes a `DraftAttachment`; AI fills the draft fields as **suggestions**; the existing approval posts it.
- **Q1 — What can be reused as-is:**
  - `DraftAttachment` for the **uploaded receipt** (already validates mime/size, stores sha256 — **dedup-ready**).
  - `ExpenseDraft` as the **pending receipt** carrier (no posting until approved).
  - `approve_expense_draft(..., post_fn=...)` as the **posting boundary** — unchanged.
  - `TransactionCategory`/`Subcategory` inline-add + `Vendor` quick-add for **"create if missing"** suggestions.
  - The S5 permission model: `upload_receipts`, `submit_expense_drafts`, `approve_expense_drafts`.

## 3. Gaps (what does NOT exist)

- **No OCR / vision / AI dependency or service** — greenfield.
- **No extraction result store** — nowhere to persist detected vendor/date/total/tax/line-items + confidence + raw OCR text.
- **No vendor→category learning store** — no table mapping a recognized vendor (e.g. "BİM" / BIM → Grocery) to a category with an approval count/confidence.
- **No line-item extraction → `Product`/`Purchase` linkage** — receipts capture items, but expense drafts are single-amount; multi-line itemization is a later, optional path (purchases/inventory).
- **No confidence/auto-post machinery** — no confidence threshold, owner toggle, or auto-post audit trail.
- **`ExpenseDraft` payment_method is V1 Cash-only** (`V1_PAYMENT_METHODS={"Cash"}`) — card/credit receipts need the payment dimension widened later.

## 4. Recommended architecture

**Q4 — Should receipt-AI create an expense draft first instead of posting directly? YES — emphatically.** Reuse the draft→approve→post seam:

```
Upload receipt ─► DraftAttachment (existing)
      │
      ▼
services/receipt_ai (NEW, pure/injectable extractor seam — like post_fn)
   • OCR/AI is an INJECTED callable; the service itself does no network/AI
   • returns a ReceiptExtraction DTO: vendor?, date?, total?, tax?, items[], confidence
      │
      ▼
Map extraction ─► ExpenseDraftInput (suggested category/subcategory via learning)
      │  (vendor/category/item missing → suggest create, reuse inline-add/quick-add)
      ▼
ExpenseDraft (status=draft, AI-suggested)  ── user reviews/edits ──►
      │
      ▼
approve_expense_draft(..., post_fn=_staff_capture_post_expense_draft)  ◄ existing posting boundary
      ▼
ExpenseRecord + JournalEntry (existing, double-entry, voidable)
```

- **Phase 1 (approval-first)** needs **no posting change and no posting-schema change** — it produces a normal draft that a human approves. The only new pieces are the **extractor seam** and a place to stash the **AI suggestion/confidence** (can start in the draft's `description`/session, formalized into a table later).
- **Extractor as a seam** (mirrors `post_fn`): the OCR/AI call is an **injected callable**, so the service is testable with a fake extractor and the real AI/OCR is swappable and deferrable to FastAPI.

## 5. Learning model proposal

- **Store:** a future `receipt_vendor_category_map` table (company-scoped): `vendor_signature` (normalized text/heuristic) → `tx_category_id`/`tx_subcategory_id`, `approval_count`, `last_approved_at`. Populated **on each human approval** of an AI-suggested draft.
- **Suggest:** on a new receipt, look up the vendor signature → propose the most-approved category; **confidence = f(approval_count, recency, match strength)**.
- **Where it lives:** a new `services/receipt_ai` (pure functions: `extract` seam, `suggest_category`, `record_approval`) — explicit `company_id`, serializable DTOs, **no Streamlit** (same contract as `staff_capture.py`). Learning writes happen **only on approval**, never on upload.
- **"Create if missing":** if the suggested vendor/category/item does not exist, surface a **create suggestion** reusing the existing inline-category-add and vendor-quick-add; never auto-create silently in Phase 1.

## 6. Auto-post safety rules (future phases)

Auto-post is the **highest-risk** capability; gate it like the Alembic cutover:

- **Owner-controlled:** a company-level **owner-only** toggle enables auto-post; default **off**.
- **Confidence-gated:** auto-post only above an explicit confidence threshold (and only for a vendor with sufficient approval history); below threshold → normal draft for approval.
- **Auditable:** every auto-post writes an `AuditLog` entry identifying it as AI auto-posted, the source `DraftAttachment` (sha256), the extraction, and the confidence.
- **Reversible:** auto-posted expenses use the **existing void/reversal** path (reversing `JournalEntry`); nothing about auto-post bypasses the posting kernel.
- **Fail-safe:** any extraction ambiguity, missing vendor/category, or duplicate (sha256 match) → **fall back to approval**, never auto-post.
- **Bake-in:** enable per-vendor only after a window of consistent human approvals (telemetry-gated, like NAV-S6 / Alembic bake-in).

## 7. FastAPI / React migration design

- **Q7 — Defer to FastAPI:** the **OCR/AI network calls**, heavy image processing, and any async/long-running extraction belong in **API endpoints**, not the Streamlit request loop. Phase-1 Streamlit can call a synchronous injected extractor (or skip extraction until the API exists).
- **API shape:** `POST /api/v1/expense-drafts/{id}/attachments` (exists conceptually via `DraftAttachment`), `POST /api/v1/receipts/extract` (AI seam), `POST /api/v1/expense-drafts/{id}/approve` (posting boundary, exists), auto-post behind a company flag. Permissions: `upload_receipts` / `submit_expense_drafts` / `approve_expense_drafts` (existing).
- **React:** upload → show extraction + suggested category with confidence → user confirms/edits → approve. The draft DTOs are already serializable (`staff_capture` dataclasses), so the contract is migration-ready.

## 8. Contract tests (audit-recommended; for a later slice)

- **Draft reuse:** a receipt-AI draft is a normal `ExpenseDraft` and posts **only** via `approve_expense_draft` + `post_fn` (no direct post).
- **Extractor is a seam:** the receipt-AI service accepts an **injected extractor**; with a fake extractor it produces an `ExpenseDraftInput` and **makes no network/AI call** (pure).
- **Attachment dedup:** identical receipt bytes → same `sha256`; duplicate detection is possible before posting.
- **No silent create:** a missing vendor/category yields a **suggestion**, not an auto-created row, in Phase 1.
- **Auto-post gates (future):** auto-post is off by default, owner-gated, confidence-gated, writes an `AuditLog`, and is voidable; below-threshold falls back to approval.
- **No posting-kernel change:** `create_journal_entry` / void paths are unchanged (regression guard).

## 9. Implementation slices (for Cursor — DO NOT implement here)

- **RECEIPT-AI-01-IMPL-1 — service skeleton (pure):** `services/receipt_ai` with `ReceiptExtraction` DTO + **injected extractor seam** (no AI call), reusing `DraftAttachment`/`ExpenseDraft`. + tests with a fake extractor.
- **RECEIPT-AI-01-IMPL-2 — suggestion mapping:** extraction → `ExpenseDraftInput` (vendor/date/total; suggested category); user approval required; **no auto-post**.
- **RECEIPT-AI-01-IMPL-3 — learning store (read-mostly):** `receipt_vendor_category_map` table + `suggest_category` / `record_approval` (write only on approval).
- **RECEIPT-AI-01-IMPL-4 — confidence model:** confidence scoring + UI display; still approval-first.
- **RECEIPT-AI-01-IMPL-5 — real OCR/AI (FastAPI):** implement the extractor behind an API endpoint; deferred network/image work.
- **RECEIPT-AI-01-IMPL-6 — trusted auto-post (flag + bake-in):** owner toggle, confidence gate, audit, void-reversible, telemetry bake-in — last and most guarded.

## 10. Risk assessment

**Audit: LOW.** Nothing changes here. The strategic win is that **Phase 1 reuses an existing, well-tested draft→approve→post seam**, so the approval-first feature carries **no posting risk** and needs **no schema/posting change**. Risk concentrates in the **later** slices: OCR/AI accuracy (mitigated by approval-first + confidence), and **auto-post** (mitigated by owner-gating, confidence threshold, audit, void-reversibility, and bake-in). The Cash-only `payment_method` and single-amount draft shape are known constraints to widen deliberately, not silently.

## No-change statement (RECEIPT-AI-01 audit)

- **No OCR/AI implementation, no AI calls, no schema change, no posting change, no auto-post, no runtime UI change, no `app.py`/`models.py` edit.** Capability map + reusable components + gaps + architecture + learning model + auto-post safety + migration design + contract tests + slices + risk only.

---

*Audit only. The ERP already has the receipt-AI substrate: `ExpenseDraft` + `DraftAttachment` (sha256, jpg/png/webp/pdf) + the FastAPI-ready `services/staff_capture.py` draft pipeline whose **approval posts via an injected `post_fn`** — so receipt-AI should create an **expense draft first** (Q4 = yes) and ride the existing approval→post→voidable path with **no posting or schema change in Phase 1**. Missing: any OCR/AI/image dependency (greenfield), an extraction-result store, and a vendor→category learning store. Recommended: a new pure `services/receipt_ai` with the OCR/AI as an **injected extractor seam** (testable, deferrable to FastAPI); learning = a company-scoped vendor→category map written only on approval, confidence from approval history; "create if missing" reuses inline-category-add + vendor-quick-add (suggest, never silent). Auto-post is the high-risk future phase — owner-controlled, confidence-gated, audited, void-reversible, fail-safe to approval, telemetry bake-in. Defer real OCR/AI network calls to FastAPI endpoints. Risk LOW (audit) — Phase 1 reuses a tested seam; risk concentrates in later OCR-accuracy and auto-post slices, all gated.*
