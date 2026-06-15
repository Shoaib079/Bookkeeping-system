# RECEIPT-AI-01-IMPL-3 — Receipt Review UI / Manual Extractor Stub: Plan

**Mode:** Planning only. **No OCR, no AI API, no auto-post, no new schema, no direct `ExpenseRecord`, no `JournalEntry`, no `app.py`/`models.py` edit.** Thin UI over the existing Staff Expenses draft flow; implementation is a later, separately-approved slice.

## Context confirmed in code

- **Draft payment already supports Cash/Card/Unknown.** `services/staff_capture.py:39` defines `DRAFT_PAYMENT_METHODS = {"Cash", "Card", "Unknown"}`, used by `create_expense_draft` / `update_expense_draft` (`:394, :446`). The Cash-only `V1_PAYMENT_METHODS = {"Cash"}` (`:37`) is the **posting-side** default, not the draft constraint. **So a Card/Unknown receipt can already be stored and reviewed as a draft** — no schema change needed.
- **Attachments exist:** `add_draft_attachment(...)` (`staff_capture.py:733`) with `DraftAttachment` (sha256, jpg/png/webp/pdf, ≤10 MB, ≤5/draft).
- **Pure suggestion service exists:** `services/receipt_ai.py` (IMPL-1) produces a `DraftSuggestion` from an injected extractor; IMPL-2 already creates draft-only `ExpenseDraft` records.
- **Review/approval flow exists:** `ui/staff_capture.py` (Submit / My Submissions / Inbox) gated by `submit_expense_drafts` / `approve_expense_drafts` / `upload_receipts`.

## 1. Recommended UI location — **A. Staff Expenses page**

Reuse the existing Staff Expenses page; add a thin **"Receipt capture"** entry (a sub-tab or an expander within the Submit tab), behind a feature flag (§ below). Rationale:

- It already owns the **draft → review → approve** lifecycle, the **attachment uploader**, the **category/subcategory pickers**, and the **permission gates** — IMPL-3 adds only an upload + a (manual/fake) field-fill step that produces a normal draft.
- **Reject B (Add Transaction):** that page posts directly — the wrong model; Receipt-AI must be draft-first/approval-first.
- **Reject C (new Receipt-AI page):** duplicates the entire draft/review/approval flow and its gates; more surface, more drift, no benefit in Phase 1. (A dedicated page can be reconsidered at the React migration.)

## 2. Exact user workflow

1. **Upload** a receipt image/PDF (reuse the existing `st.file_uploader` + `add_draft_attachment` validation: mime/size/sha256).
2. **Field fill** — a **manual/fake extractor** supplies (or the user types): vendor text, date, total amount, currency, **payment method (Cash/Card/Unknown)**, optional category/subcategory. In IMPL-3 the "extractor" is the injected stub from IMPL-1 (`extract_receipt_with(fake_extractor, ...)`) and/or direct user entry — **no OCR/AI**.
3. **Map → suggestion** via `map_extraction_to_draft_suggestion(...)` (pure) → `DraftSuggestion` (prefill where confident; create-if-missing hints for unknown vendor/category — **suggestion only, never silent create**).
4. **Create draft** — call the existing `create_expense_draft(session, company_id, actor_id, ExpenseDraftInput(...))` with `status="draft"`. **No posting.**
5. **Attach receipt** — `add_draft_attachment(...)` links the uploaded file to the new draft (`draft_type="expense"`).
6. **Review** — the draft appears in the existing **My Submissions** list; submit → **Inbox** review → **approve** posts via the existing `approve_expense_draft(..., post_fn=_staff_capture_post_expense_draft)`. IMPL-3 changes **nothing** about the posting boundary.

## 3. Permission model (reuse, unchanged)

- **`upload_receipts`** — attach the receipt file (existing gate on attachments).
- **`submit_expense_drafts`** — create/update/submit the receipt draft; **Receipt capture is visible iff the user has this permission** (consistent with the S5 permission-derived Staff Expenses nav).
- **`approve_expense_drafts`** — approve → post (the GL boundary; unchanged).
- No new permission is introduced. The manual extractor is a submitter-side convenience; approval remains the privileged, posting action.

## 4. Payment method handling (Cash-only posting constraint)

- **Draft stage:** store the detected/chosen method using `DRAFT_PAYMENT_METHODS` (Cash/Card/Unknown — already supported). Prefill from `DraftSuggestion.payment_method` only when confident; otherwise `user_must_choose_payment=True` and the user picks. **Advisory only.**
- **Approval/posting stage:** posting is **Cash-oriented today** (`V1_PAYMENT_METHODS`). Therefore a **Card/Unknown** draft must have its payment **resolved to a postable method by the approver before approval** — the approver explicitly confirms how it posts. If the posting path cannot yet represent a non-Cash expense, **approval of Card/Unknown is blocked with a clear message** ("resolve payment method before approval") rather than silently posting as Cash. The implementation slice must **verify `_staff_capture_post_expense_draft` behavior for non-Cash** and choose block-vs-resolve accordingly.
- **Hard rules:** payment detection **never** triggers auto-post, **never** creates a `BankTransaction`, and **never** settles card/bank accounts. Card simply records the draft's payment dimension for the human to act on.

## 5. Feature flag / module setting

**Yes — hide behind a company/module setting**, default **off** (registry `get_setting` / `get_effective_config`, consistent with the configurable-ERP + VENDOR-NEUTRAL principles). Receipt-AI is industry-optional; the flag keeps the Staff Expenses page unchanged for companies that don't use it and lets owners enable it deliberately. The flag controls only **visibility of the Receipt-capture entry**, not posting.

## 6. Tests needed (for the implementation slice)

- **Draft-first, no posting:** uploading + field-fill creates an `ExpenseDraft` with `status="draft"` and **no** `ExpenseRecord`/`JournalEntry` (only `approve_expense_draft` posts).
- **Attachment linked:** the uploaded file becomes a `DraftAttachment` on the new draft (sha256 recorded).
- **Payment prefill vs choose:** confident detection prefills Cash/Card; low/Unknown forces user choice (advisory).
- **Card/Unknown approval guard:** a Card/Unknown draft cannot be approved until payment is resolved (block-or-resolve per the verified post_fn behavior); approval never auto-creates a bank transaction.
- **Create-if-missing:** unknown vendor/category surfaces a suggestion, never an auto-created row.
- **Permission gates:** Receipt capture requires `submit_expense_drafts`; attachment requires `upload_receipts`; approval requires `approve_expense_drafts`.
- **Feature flag:** entry hidden when the module setting is off; visible when on (and the user has `submit_expense_drafts`).
- **Thin UI:** the UI delegates to `services/receipt_ai.py` + `services/staff_capture.py`; no posting/accounting logic in the page (structural).

## 7. Implementation slices (for Cursor — DO NOT implement here)

- **RECEIPT-AI-01-IMPL-3a — manual extractor + review entry:** add the Receipt-capture UI to the Staff Expenses page (upload → field-fill → `create_expense_draft` + `add_draft_attachment`), behind the feature flag; reuse existing pickers/uploader. + the §6 tests.
- **RECEIPT-AI-01-IMPL-3b — payment resolution at approval:** verify `_staff_capture_post_expense_draft` for non-Cash; implement the Card/Unknown block-or-resolve guard at approval.
- **RECEIPT-AI-01-IMPL-3c — fake extractor wiring:** wire the IMPL-1 injected-extractor seam so a deterministic stub can pre-fill fields (still no OCR/AI).

## Risks

**LOW–MODERATE.** No posting/schema/auto-post change; the feature rides a tested draft→approve→post seam behind a default-off flag. The one real consideration is the **Cash-only posting constraint**: Card/Unknown drafts must be **explicitly resolved at approval** (block-or-resolve), never silently posted as Cash and never auto-settled to a bank/card account. Verifying the post_fn's non-Cash behavior is the gating task for IMPL-3b. UI must stay thin (logic in services) to remain FastAPI/React-portable.

## No-change statement (RECEIPT-AI-01-IMPL-3 planning)

- **No OCR, no AI API, no auto-post, no new schema, no direct `ExpenseRecord`/`JournalEntry`, no `app.py`/`models.py` edit.** UI-location recommendation + workflow + permission model + payment handling + feature flag + tests + slices + risks only.

---

*Planning only. Recommend UI location **A (Staff Expenses page)** — a thin Receipt-capture entry behind a default-off company/module flag, reusing the existing draft/attachment/picker/permission flow; reject Add Transaction (posts directly) and a new page (duplicates the flow). Workflow: upload → manual/fake field-fill → `map_extraction_to_draft_suggestion` → `create_expense_draft(status=draft)` → `add_draft_attachment` → existing My Submissions/Inbox review → existing approve→post_fn. Permissions reused unchanged (upload_receipts / submit_expense_drafts / approve_expense_drafts); visible iff submit permission. Payment: drafts already accept Cash/Card/Unknown (DRAFT_PAYMENT_METHODS); detection is advisory/prefill; because posting is Cash-only (V1_PAYMENT_METHODS), Card/Unknown must be resolved by the approver before approval (block-or-resolve), never auto-posted, never auto-creating a BankTransaction or settling card/bank. Tests: draft-first/no-posting, attachment linked, prefill-vs-choose, Card/Unknown approval guard, create-if-missing, permission gates, feature flag, thin-UI. Risk LOW–MODERATE — only the Cash-only posting constraint needs the resolve guard (verify post_fn for non-Cash).*
