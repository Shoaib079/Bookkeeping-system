# BANKING-UX-02 — Banking UX Design

**Mode:** Design only. No code, no implementation plan, no DB changes, no accounting/posting changes, no service extraction. All `services.posting` and `reconciliation/match_post` contracts preserved.
**Inputs:** `docs/BANKING_UX_01_AUDIT.md`, `docs/POSTING_SERVICE_01_STATUS.md`.
**Scope of businesses:** restaurants, retail, trading, services, partnerships, bookkeeping firms, general SMB. **Not restaurant-specific.**

**Design invariant (non-negotiable):** every bulk/batch/queue action in this design is a *UI orchestration* over the **existing** per-row posters (`post_deposit_clearing_match`, `post_generic_deposit`, `post_partner_statement_match`, `post_worker_statement_match`, `post_equity_statement_match`, `post_vendor_outflow`, `post_bank_charge_outflow`) and the existing suggestion helpers. "Post 30 rows" = call the same contract 30 times. No new posting path, no changed debit/credit, no changed accounting. Reconciliation keeps owning orchestration; the GL kernel is untouched.

**Classification key (applied per recommendation):**
**A** = default behavior · **B** = optional *user* preference · **C** = *company-level* setting · **D** = future FastAPI/React impact.

---

## 1. Current workflow analysis

**Upload** → pick account, header row (auto-detected but needs an Apply click), file, per-field column mapping, preview, commit to staging.
**Review** → pick import from dropdown, read-only row table, skip via raw "Row IDs" multiselect, CC-bill unpost lives here.
**Match** → `get_postable_rows` → **one row chosen from a dropdown** → summary → 7-option radio → kind-specific sub-form → Post → **full-page rerun** → repeat.
**History** → flat list of prior imports.

**Biggest bottlenecks**
1. **Single-row dropdown in Match** — strictly one row per cycle; the dominant month-end cost (~5–8 interactions/row, ~200–320 for 40 rows).
2. **Full-page rerun per post** — context/scroll reset every cycle.
3. **No bulk / no auto-post** despite the system already detecting kinds with reasonable confidence.

**Biggest operator frustrations**
- Review and Match are separate tabs; selection doesn't carry across.
- Raw DB ids surfaced ("Row IDs to skip").
- Suggested kind is applied silently, with no "accept" affordance.
- No progress signal ("how many left?") and no statement tie-out.

**Scalability limits**
- Linear interaction + a rerun per row → fine at 20 rows, painful at 100, impractical at 500.
- No way to triage (filter, sort, group) the postable set.
- No "work to zero" loop and no completion signal.

> **Assumption check:** the audit's headline fix ("list with inline post") is correct but *partial* — it speeds the doing-surface yet still leaves no overview, no month-end readiness, and no batch. The design below treats that as one ingredient, not the whole answer.

---

## 2. Banking UX vision

The banking experience should feel like **"land on a status board that tells you what needs attention, then drop into a fast queue that clears it — with the obvious stuff posted in bulk and only the genuinely ambiguous rows asking for a human decision."**

Three idioms are in play; they are **complementary, not competing**:
- **Dashboard / cockpit** — *orientation & month-end readiness* (what's the state, am I done?).
- **Work queue / inbox** — *throughput* (clear rows fast, one decision each, keyboard-able).
- **Batch processing** — *leverage* (post all high-confidence rows at once after review).

A pure classic ERP grid optimizes for none of these. A pure queue lacks orientation/readiness. A pure cockpit is a board you can't *work* in. The vision is a **cockpit that launches a queue, with batch as the bridge** — and a classic table retained as an optional power view.

---

## 3. Compare alternative designs

### Design A — Classic ERP (refined tables + forms)
| | |
|---|---|
| Pros | Familiar to bookkeepers; full grid visibility; low build risk; good for ad-hoc edits/audit |
| Cons | Doesn't reduce clicks/reruns; no triage or batch; weak month-end readiness; poor on phone |
| Complexity | Low |
| FastAPI readiness | Medium — grids map to list endpoints, but the edit-in-place pattern is Streamlit-ish |
| Best user type | Experienced bookkeepers who want a ledger grid |

### Design B — Work Queue (inbox-style)
| | |
|---|---|
| Pros | Fastest throughput; one decision/row; keyboard/next-advance; mobile-tolerable; **maps cleanly to API** (get-next / list + post-decision) |
| Cons | Weak whole-statement overview and tie-out; batch must be bolted on; can feel "blind" to power users who want the grid |
| Complexity | Medium |
| FastAPI readiness | **High** — stateless per-row decisions; suggestion helpers are pure |
| Best user type | Operators/owners clearing volume; non-accountants |

### Design C — Reconciliation Cockpit (dashboard + drill-in)
| | |
|---|---|
| Pros | Best visibility and **month-end readiness**; surfaces health (import/statement/settlement); great landing page |
| Cons | A board, not a doing-tool, on its own; needs a queue/table behind it to act; more aggregate queries |
| Complexity | Medium–High |
| FastAPI readiness | **High** — pure read aggregates → clean GET endpoints |
| Best user type | Owners/managers/firms overseeing close; multi-client bookkeepers |

### Recommendation — **C fronting B, with A as an optional view**
A **Reconciliation Cockpit (C)** is the landing surface and readiness gauge; its primary action **launches a Work Queue (B)** scoped to whatever the operator clicked (an import, "all unmatched", "high-confidence", a date range). **Batch** lives at the seam (cockpit "post N auto-matched" → confirmation → queue for the rest). A **classic table (A)** remains available as an opt-in "ledger view" (**B** user preference; **C** can default it on for firm/bookkeeper tenants).

Rationale: this serves both audiences without forking the product — non-accountants get orientation + a guided queue; bookkeepers get batch + an optional grid. All three reuse the same per-row contracts.

---

## 4. Match queue redesign

Replaces the single-row dropdown. Still one decision per row at the atomic level, but presented as a **scannable, filterable, batch-capable queue** with no full-page rerun per item.

### 4.1 Queue list (default Match surface)

```
┌─ Match — Import #42 · acme_bank_may.csv ································· 18 left ─┐
│ Filter: [ All ▾ ] [ Deposits ] [ Withdrawals ]   Confidence: [ High ▾ ]        │
│ Sort: [ Date ▾ ]                         Search ⌕ [ description… ]              │
│                                                                                │
│ ☐  03 May  −1,240.00  "ACME SUPPLIES LTD"      ● High  → Vendor: ACME [accept] │
│ ☐  03 May  −  38.50   "KOMISYON POS"           ● High  → Bank fee: POS comm.   │
│ ☐  04 May  +5,000.00  "PESIN SATIS"            ● High  → Card clearing         │
│ ☐  05 May  −2,000.00  "MAAS ODEME"             ◐ Med   → Worker payroll  [review]│
│ ☐  06 May  + 900.00   "TRANSFER 8842"          ○ Low   → Needs you      [review]│
│ …                                                                              │
│ [ Select all High ]   [ Post 11 selected ▸ ]            [ Open ledger view ]   │
└────────────────────────────────────────────────────────────────────────────────┘
```

- **Confidence chips** (●High ◐Med ○Low) come from the *existing* `suggest_*` / `looks_like_*` heuristics surfaced as a label — **no new logic** (A).
- **Inline "accept"** posts a single row via its existing poster; **"review"** opens the detail panel (4.2).
- **"Post N selected"** iterates the existing posters with a pre/post confirmation summary (batch = loop, §1 invariant).
- Whether Low-confidence rows can be batch-selected at all is a **company setting (C)**; default **A** = only High is bulk-selectable.

### 4.2 Row detail (slide-over, no tab switch — merges Review + Match)

```
┌ Row #7 · 05 May · −2,000.00 ······························· [ ▲ prev | next ▼ ] ┐
│ Description: "MAAS ODEME PERSONEL"                                              │
│ Suggested: Worker payroll  ◐ Medium                                            │
│ What is this?  (•)Worker payroll ( )Vendor ( )Bank fee ( )Equity/Loan ( )Other │
│ ── Worker payroll ──────────────────────────────────────────────────────────  │
│ Worker:[ A. Yılmaz ▾]  Gross:[2,000]  Deduct:[0]  Adv.recovery:[0]             │
│ Net pay must equal bank withdrawal (2,000.00) ✓                                │
│ [ Post & next ▸ ]   [ Skip ]   [ Cancel ]                                      │
└────────────────────────────────────────────────────────────────────────────────┘
```

- **Prev/next** keeps the operator in flow; **Post & next** advances without a full-page reset.
- The 7 kinds map exactly to today's renderers/posters; the sub-forms are unchanged in *meaning*.

### 4.3 State transitions (per row — unchanged semantics)

```
staging ──accept/post──▶ posted
staging ──skip────────▶ skipped
staging ──(closed period guard)──▶ stays staging + inline error (no partial post)
posted  ──unpost──────▶ staging        (where permitted; see §5)
duplicate_flagged ─(same as staging, with a dup badge)
parse_error ─────────▶ (not postable; fix at upload)
```

These mirror the current `BankStatementRow.status` lifecycle — **no new states**.

### 4.4 Navigation flow

```
Cockpit ─▶ [Work this import] ─▶ Queue list ─▶ (accept inline)  ─▶ next row
                                   │           (review) ─▶ detail ─▶ Post & next
                                   └─ [Post N High selected] ─▶ batch confirm ─▶ results
```

### 4.5 Progress tracking & confidence

- Header counter **"18 left"** + a thin progress bar (posted / total postable).
- Per-row confidence chip; an aggregate **"11 High · 4 Med · 3 Low"** summary.
- Completion signal: when postable = 0, show **"Statement reconciled"** with the tie-out (§6).
- Confidence is *presentation of existing heuristics*; thresholds are configurable (§5).

### 4.6 Manual review handling

- Low/Med rows are never auto-selected by default (A); they carry a **"review"** affordance and stay in the queue until a human decides.
- A **company setting (C)** can require manager review for specific kinds (e.g. equity/loan, ad-hoc expense) before posting; default **A** = no extra review.

---

## 5. Configuration strategy

| Feature | Default (A) | User preference (B) | Company setting (C) |
|---------|-------------|---------------------|---------------------|
| **Auto-match suggestion** | On — show suggested kind + confidence | Hide chips / always expand detail | Turn suggestions off tenant-wide |
| **Bulk post of High-confidence** | Allowed for High only | Per-user "always confirm each" | Disable bulk entirely; or allow Med in bulk |
| **Confidence thresholds** | Built-in heuristic bands | — (presentation only) | Tune High/Med cutoffs per tenant |
| **Header-row detection** | Use detected value automatically | Per-user "always ask" | Lock a default header row per bank account |
| **Default landing view** | Cockpit | Per-user: Cockpit / Queue / Ledger table | Tenant default (e.g. firms → Ledger) |
| **Default queue filter** | All postable | Per-user remembered filter/sort | — |
| **Unpost permission** | Role-gated (existing perms) | — | Which roles may unpost; reason required Y/N |
| **Review requirement** | None | — | Require review/approval for chosen kinds before post |
| **Ad-hoc expense from statement** | Allowed (existing) | — | Restrict to payable-match only (no ad-hoc) |
| **Mobile match actions** | Read + approve High batch only | Per-user enable single-row post on mobile | Disable mobile posting entirely |

Principle: **sensible defaults that work out-of-the-box for a non-accountant**, with company-level overrides for firms/bookkeepers who want stricter control. Nothing here changes accounting — only *who can do what, when, and how it's presented*.

---

## 6. Reconciliation cockpit (landing page)

```
┌ Banking · Reconciliation ································ Company: ACME ▾ · May ▾ ┐
│                                                                                 │
│  IMPORT HEALTH                          STATEMENT HEALTH                        │
│  ┌───────────────────────────┐         ┌───────────────────────────────────┐   │
│  │ Imported   320            │         │ Outstanding rows      18          │   │
│  │ Posted     290  ▓▓▓▓▓▓▓░   │         │ Outstanding amount    4,310.00    │   │
│  │ Unmatched   18            │         │ Oldest unmatched      02 May (7d)  │   │
│  │ Skipped     12            │         │ Tie-out: book 1,240,880 vs bank … │   │
│  │ Errors       0            │         │          ▲ diff 4,310.00 (=outst.) │   │
│  └───────────────────────────┘         └───────────────────────────────────┘   │
│                                                                                 │
│  SETTLEMENT HEALTH (if card/POS used)   MONTH-END READINESS                     │
│  ┌───────────────────────────┐         ┌───────────────────────────────────┐   │
│  │ Card clearing balance 920 │         │ ☑ All imports reviewed            │   │
│  │ Unsettled card sales   3  │         │ ☐ 18 rows unmatched               │   │
│  │ Pending settlements    1  │         │ ☑ No parse errors                 │   │
│  │ CC GL vs subledger  ✓ ok  │         │ ☐ Clearing balance not zero (920) │   │
│  └───────────────────────────┘         │ Readiness: 2 of 4 ▓▓▓▓░░░░          │   │
│                                         └───────────────────────────────────┘   │
│                                                                                 │
│  [ Work 18 unmatched ▸ ]   [ Post 11 high-confidence ▸ ]   [ Open ledger view ] │
└─────────────────────────────────────────────────────────────────────────────────┘
```

- **Settlement health** card only renders when card/POS settlement is enabled (**C** gate) — keeps it neutral for trading/service firms with no card sales.
- **Tie-out** reuses existing balance reads (`calculate_account_balance`, `compute_cc_payable_recon_health`) — read-only, no posting (A).
- Every tile is a **drill-through** into a scoped queue.
- Month-end readiness is a **checklist derived from existing data**, not a new gate on posting — purely advisory (A).

---

## 7. Month-end workflow (scaling)

| Volume | Shape of the work | Where batch | Where manual |
|--------|-------------------|-------------|--------------|
| **20 rows** | Cockpit → "Work 20" → queue; accept inline | Optional "post all High" | A few Low rows reviewed in detail |
| **100 rows** | Cockpit shows 70 High / 20 Med / 10 Low. "Post 70 High" (batch confirm), then queue the 30 | Batch the High block up front | Med/Low worked in the queue with prev/next |
| **500 rows** | Triage first: filter by kind/confidence/date; batch High by group (commissions, card deposits, payroll), then attack the residual | Batch per group; repeated bulk passes | Only genuinely ambiguous residual reaches a human |

Scaling principle: **the human's effort should grow with ambiguity, not with row count.** High-confidence volume is absorbed by batch; manual review is reserved for Low/Med and policy-flagged kinds. Batch always = the existing posters in a loop with a confirmation summary and a per-row result report (so one failure doesn't obscure 69 successes).

---

## 8. Error UX (wording + help + recovery — no accounting change)

| Situation (current) | Operator-friendly wording | Help text | Recovery action |
|---------------------|---------------------------|-----------|-----------------|
| Closed period/year (`ValueError` from kernel) | "This date falls in a closed period — it can't be posted." | "The period or year is locked. Reopen it, or post to an open date." | Link to Fiscal Periods; offer "skip for now" |
| Bank charges disabled, fee detected | "A processor fee was detected but bank-charge posting is off." | "Turn on Bank charges in Company Setup to book the fee." | Inline "enable" link (if permitted) + retry |
| Inferred fee needs confirm | "We think {amount} is a processor fee. Confirm to post it to Bank Charges." | "Fees are inferred when the deposit is smaller than the matched sales." | "Confirm fee" / "Not a fee — choose another match" |
| Settlement gross/net/fee mismatch | "These figures don't balance: gross − fee ≠ net." | "Check the settlement batch against the bank deposit." | Show the three numbers; "re-pick batch" |
| Deposit exceeds clearing | "This deposit is larger than the sales you matched." | "Likely a refund/chargeback — handle separately." | "Match fewer/more sales" |
| Already posted / wrong direction | "This row is already posted." / "This looks like a {deposit/withdrawal}, not a {…}." | — | Jump to its posted entry / switch kind |
| Raw "Row IDs to skip" | "Select rows to skip" (checkboxes, no ids) | — | — |
| Worker net-pay ≠ withdrawal | "Net pay ({net}) must equal the bank withdrawal ({paid})." | "Adjust gross, deductions, or advance recovery." | Inline recompute hint |

Rules honored: messages are **re-worded, not re-behaved**; all surfaced through `_t(...)` (fix the two untranslated literals); every post action **catches both `MatchPostError` and `ValueError`** so closed-period rows show a friendly inline message instead of an exception page.

---

## 9. Mobile & small-laptop strategy

| Device | Should work well | Stays desktop-first |
|--------|------------------|---------------------|
| **13" laptop** | Everything — cockpit, queue, detail slide-over, batch, ledger table (it just gets denser) | — |
| **Tablet** | Cockpit (read), queue list with inline accept, "post High batch", single-row detail | Column-mapping upload wizard |
| **Phone** | Cockpit read-only + month-end readiness; approve a **queued High-confidence batch**; view status | Upload + column mapping; complex sub-forms (settlement, worker payroll); ad-hoc expense |

- Fix the 7-option **horizontal radio** → vertical/segmented on narrow viewports (A).
- Phone posting beyond "approve batch" is a **user opt-in (B)**, off by default; a company can disable mobile posting entirely (**C**).
- Import/mapping is explicitly a desktop task; the phone is for *oversight and approval*, not data wrangling.

---

## 10. FastAPI / React readiness (observational — no architecture change)

| Screen | API mapping | Coupling note |
|--------|-------------|---------------|
| **Cockpit** | Pure read aggregates → clean `GET /reconciliation/summary` shape | None — already pure reads |
| **Queue list** | `GET` postable rows (+ suggested kind/confidence) → list endpoint | Suggestion helpers are pure; today's `get_postable_rows` is the seed |
| **Row detail / post** | `POST` decision per row (the existing poster signatures) | Posters already take explicit `company_id`, return dicts, raise `MatchPostError` — API-shaped |
| **Batch post** | `POST` list of decisions → per-row result array | Pure loop over the same contract |
| **Upload + column mapping** | Multi-step; file + mapping state | **Most Streamlit-coupled**; React would own wizard state client-side |

- **Naturally API-ready:** cockpit, queue, suggest-kind, single/batch post.
- **Streamlit-coupled today:** the upload/mapping wizard and the `bsi_match_kind*` session-state juggling — both are *UI state*, not accounting, so they move to React without touching services.
- **Likely React screens:** a Recon Cockpit page; a Queue (virtualized list, keyboard nav, slide-over detail, batch toolbar); an Upload wizard (drag-drop + mapping). All consume the existing service contracts.
- **Carry-forward risks already logged in PS-P7** (do not fix here): ambient-vs-explicit company stamping on statement JEs (multi-tenant), and the absence of reconciliation-layer audit (`log_audit`) — both matter for an API serving multiple tenants/users.

---

## 11. Prioritized roadmap

> Value/complexity/risk are design-level estimates. P1 items are UI-only over existing contracts.

### P1 — Immediate UX wins
| Item | Business value | Complexity | Risk |
|------|----------------|------------|------|
| Match **queue list** (replace single-row dropdown) with inline accept + prev/next detail (no full rerun) | High — removes the dominant month-end friction | Medium | Low (UI over existing posters) |
| Surface **suggested kind + confidence chip** with one-click accept | High — turns silent default into a fast decision | Low | Low |
| Friendly **error wording** + catch `ValueError` alongside `MatchPostError`; fix the 2 untranslated literals; hide raw Row IDs | Medium — fewer dead-ends/exception pages | Low | Low |

### P2 — Major UX improvements
| Item | Business value | Complexity | Risk |
|------|----------------|------------|------|
| **Reconciliation Cockpit** landing (import/statement/settlement/readiness) with drill-through | High — visibility + month-end readiness | Medium–High | Low–Med (read-only aggregates) |
| **Batch post** of High-confidence rows with confirm + per-row result report | High — scales to 100–500 rows | Medium | Med (must report partial failures clearly; still per-row contract) |
| **Merge Review+Match** (detail slide-over) + statement **tie-out** completion signal | Medium–High | Medium | Low |
| **Configuration surface** (A/B/C settings in §5), incl. default-view + thresholds + review requirements | Medium — fits the configurable-ERP philosophy | Medium | Low |
| Default the **detected header row**; unify **unpost** affordance | Medium — fewer clicks, less fragmentation | Low–Med | Low |

### P3 — Future enhancements
| Item | Business value | Complexity | Risk |
|------|----------------|------------|------|
| **Mobile/tablet oversight** view (cockpit read + approve High batch) | Medium — owner oversight on the go | Medium | Low |
| **Learned match memory** (remember kind per description pattern, per tenant) | Medium — fewer manual decisions over time | High | Med (must stay suggestion-only; never auto-post Low) |
| **React Recon Cockpit + Queue** (when FastAPI lands) | High (strategic) | High | Med (depends on PS-P7 hardening: company stamping, audit) |
| **Reconciliation audit trail** for posting (ties to PS-P7) | Medium — traceability/compliance | Medium | Low (additive) |

---

*Design only. No code, no implementation plan, no DB or accounting changes. Every batch/queue behavior is UI orchestration over the existing `reconciliation/match_post` posters and `services.posting` kernel — accounting behavior is preserved exactly.*
