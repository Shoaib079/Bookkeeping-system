# BANKING-UX-03 P1.3 — Match Tab Characterization

**Mode:** Characterization only — no code, no implementation.
**Purpose:** Map the existing Match tab in full before replacing the single-row dropdown with a queue.
**Surface:** `render_bank_statement_import` Match section (`app.py:17598–17688`) and its helpers (`_bsi_*`, `_render_bsi_*`, `app.py:16254–16800` region); `reconciliation/match_post.py` posters/heuristics.

---

## 1. Current Match section render flow

```
section == "match"
 ├─ header + caption
 ├─ guard: can_import else "access denied"
 ├─ postable = get_postable_rows(session, cid)          # COMPANY-WIDE, all imports
 ├─ if empty → info "no rows"
 └─ else:
     ├─ row_labels = {id: "#idx · date · ±amount · desc[:40]"}
     ├─ sel_row_id = st.selectbox(key="bsi_match_row")    # SINGLE ROW
     ├─ sel_row = session.get(BankStatementRow, sel_row_id)
     ├─ is_deposit / is_withdrawal  (from credit_amount/debit_amount)
     ├─ _render_bsi_match_line_summary(sel_row)           # disabled fields + desc text_area
     ├─ kind_options = _bsi_deposit_kind_options | _bsi_withdrawal_kind_options
     ├─ kind default/reset logic (see §3)
     ├─ match_kind = st.radio(key="bsi_match_kind", horizontal=True)
     └─ dispatch:
          card_clearing → _render_bsi_deposit_clearing
          other_income  → _render_bsi_other_deposit
          equity_loan   → _render_bsi_partner_owner_loan_match
          vendor        → _render_bsi_vendor_payment
          worker_payroll→ _render_bsi_worker_payroll
          cc_bill       → _render_bsi_cc_bill
          bank_fee      → _render_bsi_bank_fee
```

Each `_render_bsi_<kind>` renders its own sub-form, then a primary **Post** button that calls the matching `match_post` poster, calls `log_audit("Post","BankStatementRow", row.id, …)` on success, shows `st.success`, and calls **`st.rerun()`**. Failures are caught as `(MatchPostError, ValueError)` and rendered via `_bsi_render_statement_post_error(exc)`.

> **Audit correction (challenge):** BANKING-UX-01/02 implied the closed-period `ValueError` may surface unhandled. In these renderers the post handlers **already catch `(MatchPostError, ValueError)`** and render a friendly error. So P1.1's "catch ValueError" is **already satisfied in the Match posters**; the remaining P1.1 gap is only at *other* call sites (e.g. Review unpost) and the two untranslated literals — smaller than the audit suggested.

> **Audit correction (challenge):** BANKING-UX-01 said `match_post` posts with "no audit." True at the *service* layer, but the **UI layer does call `log_audit("Post","BankStatementRow", …)`** after each poster. A queue must preserve **one audit per posted row**.

---

## 2. Session-state keys used (Match flow)

| Key | Set by | Role | Row-scoped? |
|-----|--------|------|-------------|
| `bsi_section` | sub-section selector | upload/review/match/history | n/a |
| `bsi_match_row` | row selectbox | currently-selected row **id** | no (holds one id) |
| `bsi_match_kind` | kind radio | current match kind | no (single "current") |
| `bsi_match_kind_row` | kind reset logic | the row id the kind belongs to | tracks 1 row |
| `bsi_pos_entry` | POS-settlement deep link | popped flag → force `card_clearing` | no |
| `bsi_line_desc_{row.id}` | line summary | disabled description text area | **yes** (keyed by id) |
| `bsi_match_sales` | clearing multiselect | picked sale ids | **no** ⚠ |
| `bsi_match_settlement` | settlement selectbox | settlement batch id | **no** ⚠ |
| `bsi_confirm_fee` | fee checkbox | confirm inferred fee | **no** ⚠ |
| `bsi_match_credit_acct` | other-deposit selectbox | credit GL choice | **no** ⚠ |
| `bsi_other_income_use_sales_revenue` | checkbox | advanced toggle | **no** ⚠ |
| `bsi_post_clearing` / `bsi_post_deposit` / per-kind button keys | buttons | submit | no |
| (vendor/worker/cc_bill/bank_fee/partner renderers) | their sub-forms | kind-specific inputs | mostly **no** ⚠ |

⚠ = **not row-scoped**: these widgets keep their value across a row switch within the single-current-row model. Today that is masked because only one row is shown at a time and `st.rerun()` after a post resets context — but it is a latent leakage (see §8).

---

## 3. Row-selection lifecycle

1. `postable = get_postable_rows(cid)` (company-wide; status ∈ {`staging`,`duplicate_flagged`}, `parsed_successfully`).
2. `sel_row_id = selectbox(bsi_match_row)` → `sel_row = session.get(...)`.
3. Kind default/reset (exact current logic):
   - if `bsi_pos_entry` popped truthy → if `card_clearing` available set `bsi_match_kind="card_clearing"`; set `bsi_match_kind_row = sel_row_id`.
   - **elif `bsi_match_kind_row != sel_row_id`** (new row) → `bsi_match_kind_row = sel_row_id`; `bsi_match_kind = _bsi_default_match_kind(sel_row, is_deposit)`.
   - elif `bsi_match_kind not in kind_ids` → fallback `kind_ids[0]`.
4. `radio(bsi_match_kind)` → dispatch to `_render_bsi_<kind>`.
5. Poster button → `post_*` → `log_audit` → `st.success` → **`st.rerun()`**.
6. After rerun: posted row leaves `get_postable_rows` (now `status="posted"`); `bsi_match_row` holds a now-absent id → Streamlit selectbox **falls back to the first remaining option**; the `bsi_match_kind_row != sel_row_id` branch then re-derives the default kind for that new first row.

Selection is keyed on **row id**, not list index.

---

## 4. Current rerun behavior

- **Every widget interaction** (selectbox, radio, multiselect, checkbox) triggers a **full-script rerun** (Streamlit default) — re-running `render_bank_statement_import` top-to-bottom, re-querying `get_postable_rows`, etc.
- **After a successful post**, an explicit **`st.rerun()`** forces a fresh full run; context/scroll reset; the posted row disappears and the next first row auto-selects.
- There is **no `st.fragment`** scoping in the Match section today — the whole page reruns each time.

---

## 5. Existing helper functions (in scope)

| Helper | Role |
|--------|------|
| `get_postable_rows(session, cid)` | company-wide postable rows (status + parsed filter) — **read-only** |
| `_render_bsi_match_line_summary(sel_row)` | disabled summary fields + `bsi_line_desc_{id}` text area |
| `_bsi_deposit_kind_options(session)` | deposit kinds (card_clearing if settlement on; equity_loan; other_income) |
| `_bsi_withdrawal_kind_options(session)` | withdrawal kinds (vendor; +worker if workers; +cc_bill if company card; +bank_fee if charges; equity_loan) |
| `_bsi_default_match_kind(session, row, is_deposit)` | wraps `suggest_deposit_match_kind` / `suggest_withdrawal_match_kind`, validated against available kinds |
| `_render_bsi_deposit_clearing / _other_deposit / _partner_owner_loan_match / _vendor_payment / _worker_payroll / _cc_bill / _bank_fee` | per-kind sub-form + Post button |
| `_bsi_render_statement_post_error(exc)` | friendly error rendering (already handles `MatchPostError`+`ValueError`) |
| `match_post.suggest_deposit_match_kind / suggest_withdrawal_match_kind / looks_like_* / card_deposit_style` | **pure** heuristics — basis for confidence chips |
| `match_post.get_same_day_deposit_rows` | gross+commission pairing helper (not wired as a Match filter) |

---

## 6. Existing filters / search capabilities

**None in the Match tab.** The row `selectbox` lists **all** postable rows (company-wide) with no filter by deposit/withdrawal, no confidence filter, no sort control, and no search box. (Review has a skip `multiselect`; `get_same_day_deposit_rows` exists for pairing but is not a Match filter.) A queue therefore *adds* triage that does not exist today — it does not need to preserve any existing filter behavior.

---

## 7. Dependencies on selected row index

- Selection is by **row id** (`bsi_match_row`), not numeric index — good (resilient to list reordering).
- `bsi_match_kind_row` couples the current kind to **one** row id; the single-current-row assumption is baked into the reset logic (§3).
- **Implicit dependency:** after post+rerun, the dropdown relies on Streamlit's "missing key value → first option" fallback to advance to the next row. A queue must make "advance to next" explicit rather than leaning on this fallback.
- `bsi_pos_entry` deep-link assumes a single "the selected row" to force into `card_clearing`.
- Per-kind widgets (`bsi_match_sales`, `bsi_confirm_fee`, `bsi_match_credit_acct`, …) are **not** keyed by row id (§2) — they implicitly belong to "whatever row is current."

---

## 8. Risks of replacing the selectbox with a queue

1. **Non-row-scoped widget keys (highest risk).** `bsi_match_kind`, `bsi_match_sales`, `bsi_match_settlement`, `bsi_confirm_fee`, `bsi_match_credit_acct`, and per-kind inputs are shared singletons. A queue that shows/opens multiple rows must **row-scope every key** (`…_{row.id}`) or selections will collide/leak between rows. (Today this is masked by one-row-at-a-time + post-rerun.)
2. **Single-current-row kind model.** The `bsi_match_kind_row != sel_row_id` reset logic must become **per-row kind state** in a queue.
3. **Rerun model.** To avoid full-page resets, per-row detail+post should be wrapped in **`st.fragment`** — a Streamlit-version dependency; fragment reruns must still respect the `status=="posted"` guard to avoid double-post.
4. **Deep link (`bsi_pos_entry`).** The "arrive from POS entry → force card_clearing on the selected row" behavior must be preserved (pre-select/scroll to that row).
5. **Audit parity.** The UI calls `log_audit("Post","BankStatementRow", …)` once per post — a queue/batch must preserve **one audit per posted row** (no merge, no omission).
6. **Heavy kinds resist inline-accept.** `card_clearing` (sale multiselect, settlement batch, fee confirm, preview/visibility blocks) and `worker_payroll` (gross/deduction/recovery) cannot collapse to a one-line inline action — they must open the **detail slide-over**. Only trivial kinds could ever inline-accept.
7. **Scope mismatch.** `get_postable_rows` is **company-wide** (all imports). If the cockpit later scopes the queue per-import/date, the query scope must be parameterized — but for P1.3 the queue should match today's company-wide scope to avoid a behavior change.
8. **Idempotency on rapid clicks.** Fragment reruns + a list of buttons raise double-submit risk; rely on the existing `_row_context` `status=="posted"` guard and disable the button mid-post.

---

## 9. Minimal viable queue design (lowest-risk P1.3)

**MVP = "list instead of dropdown," same sub-forms, row-scoped state, fragment-wrapped — single-post only (no batch; batch is P2.2).**

- Render `get_postable_rows` (unchanged, company-wide) as a **scannable list**: date, signed amount, description, **confidence chip** + **suggested-kind label** (from the existing `_bsi_default_match_kind`/`suggest_*` — presentation only).
- Optional **client-side filter/sort/search** over the already-fetched list (deposit/withdrawal, confidence, date, text) — pure UI, no new query.
- **Selecting a row opens the existing per-kind sub-form** in a detail area/slide-over (reuse `_render_bsi_<kind>` verbatim), with **all widget keys row-scoped**.
- **Post path unchanged** — same `match_post` poster + the same `log_audit` call; wrap the detail+post in `st.fragment` so only the fragment reruns; on success, drop the row and advance.
- **Preserve** the `bsi_pos_entry` deep link (pre-select + force `card_clearing`).
- **Do not** add batch, do not change scope, do not touch `match_post.py` or `services.posting`.

This keeps the change UI-only and behavior-identical at the per-row level while removing the dropdown + full-page-rerun friction.

---

## 10. Tests needed before implementation (test-first)

1. **`get_postable_rows` characterization** — company-wide scope; status ∈ {staging, duplicate_flagged}; `parsed_successfully` filter; ordering.
2. **Kind-suggestion pins** — `_bsi_default_match_kind`, `_bsi_deposit_kind_options`, `_bsi_withdrawal_kind_options` for representative rows × settings (settlement/company-card/charges/workers/partners on-off).
3. **Kind-reset lifecycle** — new-row → default kind; `bsi_pos_entry` → `card_clearing`; fallback to `kind_ids[0]`.
4. **Audit parity** — each poster path fires exactly one `log_audit("Post","BankStatementRow", row.id, …)` on success; none on failure.
5. **Contract preservation (guardrail)** — posting a given row via the (future) queue path yields an **identical** JE + BankTransaction + row finalize to the current dropdown path.
6. **Widget-key isolation** — characterize that the current shared keys (`bsi_match_sales`, `bsi_confirm_fee`, `bsi_match_credit_acct`) **leak** across row switches today; assert the queue's row-scoped keys do **not** (documented improvement, not a regression).
7. **Idempotency** — double/rapid post does not double-post (the `status=="posted"` guard holds under fragment rerun).
8. **Deep-link** — `bsi_pos_entry` still lands on the right row in `card_clearing`.
9. **Error rendering** — `MatchPostError` and closed-period `ValueError` both render via `_bsi_render_statement_post_error` from the queue path.

---

*Characterization only. No code, no implementation. P1.3 must remain UI-only over the unchanged `reconciliation/match_post` posters and `services.posting` kernel; the MVP queue preserves per-row posting behavior and audit exactly.*
