# BANKING-UX-03 P2.4 — Month-End Readiness & Tie-Out Characterization

**Mode:** Characterization only — no code, no implementation, no DB or posting changes.
**Inputs read:** BANKING_UX_01..03 docs, P2_1/P2_2/P2_2_B/P2_3 CHARs.
**Principle:** *Automation suggests; user approves; system posts only what it can explain.* Readiness is **advisory and read-only** — it never posts, never gates posting, and never replaces the fiscal-close guard (`perform_year_end_close`, PS-P6-4).

**Decisive data fact:** `BankStatementImport` captures **`starting_balance`** and **`ending_balance`** (both *nullable*), and `BankStatementRow.balance_after` exists. So a **true statement tie-out is possible when declared balances are present** — and must be reported as *unavailable* (never inferred) when they are absent.

---

## 1. Current state inventory

| Surface | Answers readiness? |
|---------|--------------------|
| **Cockpit (P2.1)** | Partly — import health (valid/error/flagged), postable count, bank balances, CC/settlement tile. No tie-out, no "complete/reconciled" status. |
| **Match Queue (P1.3)** | "N left" counter (per current scope) — workflow progress only. |
| **Review** | Per-import row table with statuses; skip. No tie-out. |
| **History** | Flat list of imports. No completion signal. |
| **Reconciliation Health** | GL-integrity: AR/AP/CC GL-vs-subledger, **per-bank stored-vs-derived balance**, CoA cache drift. Period-agnostic; off the posting loop; expensive. |
| **Settlement Health** | Card Sales Clearing balance, unsettled card sales, pending settlement batches, CC payable drift. Scattered. |

**Already answers readiness:** "how many rows left" (postable count), "do balances drift" (health page), "is clearing outstanding" (settlement).
**Missing:** statement **tie-out**, a per-statement **Complete/Reconciled** signal, a **review-pending** rollup tied to readiness, a period-level **Month Reconciled / Ready-for-Close** view, and a single non-inferred source of "reconciled."

---

## 2. Readiness definitions (four distinct levels)

| Level | Means | Condition |
|-------|-------|-----------|
| **A. Statement Complete** | *Every line dealt with* (workflow) | No rows left in `staging`/`duplicate_flagged` for the import → `get_postable_rows(import)=0`; all rows terminal (`posted`/`skipped`/`voided`) |
| **B. Statement Reconciled** | *Numbers agree with the bank* (financial) | A **AND** statement tie-out holds (declared `ending_balance` agrees with derived/posted) — **only assertable when `starting/ending_balance` present** |
| **C. Month Reconciled** | *All accounts agree for the period* | All statements/accounts for the period are B **AND** recon-health clean (AR/AP/CC, bank stored-vs-derived) within tolerance |
| **D. Month Ready for Close** | *No blockers remain* (advisory pre-flight) | C **AND** no review-required pending, no failed/pending postings, settlement/clearing resolved |

**Why they differ — the central trap:** "Is this statement finished?" conflates **Complete** (I touched every row) with **Reconciled** (the totals match the bank). A statement can be 100% Complete yet **not** Reconciled (e.g., a missed/duplicated line). Treating Complete as Reconciled is **false readiness**. D is advisory — the *actual* close gate stays in `perform_year_end_close`; readiness must agree with it, never override it.

---

## 3. Existing data sources (reuse map)

| Source | Reusable for |
|--------|--------------|
| `BankStatementImport.starting_balance / ending_balance` | **Statement tie-out** (declared side) — *nullable; gate on presence* |
| `BankStatementImport.row_count / valid_count / flagged_count / error_count` | **Import tie-out** (disposition consistency) |
| `BankStatementImport.start_date / end_date / status` | Period scoping, statement status |
| `BankStatementRow.status` (`staging`/`duplicate_flagged`/`posted`/`skipped`/`voided`/`parse_error`) | **Statement Complete** + remaining counts |
| `BankStatementRow.amount / balance_after` | Row-sum movement; running-balance cross-check |
| `get_postable_rows(cid)` | Remaining-to-do (company-wide today; per-import needs grouping) |
| `compute_cc_payable_recon_health` | CC tie-out (serializable dict — DTO precedent) |
| `calculate_account_balance(_for_period)` | Posted bank GL movement; AR/AP/RE balances |
| `render_reconciliation_health` logic | Bank stored-vs-derived; AR/AP GL-vs-subledger |
| settlement helpers (`get_unsettled_card_sales`, `get_matching_settlement_rows`) | Clearing/settlement resolution |

All are **read-only** and reusable. The gap is **aggregation + status derivation**, not new raw data — except per-import posted/remaining grouping, which doesn't exist yet (postable is company-wide).

---

## 4. Blocking conditions

| Condition | Class |
|-----------|-------|
| Unmatched/`staging` rows remain | **Hard blocker** (blocks Complete) |
| Statement tie-out mismatch (when balances present) | **Hard blocker** (blocks Reconciled) |
| Failed posting leaving a row non-terminal | **Hard blocker** |
| GL-vs-subledger difference > tolerance (AR/AP/CC/bank) | **Hard blocker** for Month Reconciled |
| Review-required rows pending (policy, P2.3) | **Warning** (allows Complete; blocks Ready-for-Close) |
| Transfer-charge review pending (P2.2-B) | **Warning** |
| Settlement discrepancy within tolerance | **Warning** |
| Card-clearing balance non-zero, explained by in-flight settlements | **Warning** (info if expected) |
| Unreconciled bank balance (stored ≠ derived) | **Hard blocker** for Reconciled |
| Open investigation / parked row | **Warning** |
| Skipped rows (intentional) | **Informational** |
| `duplicate_flagged` already reviewed | **Informational** |
| CoA cache drift | **Informational** (warning only if large) |
| **No declared `ending_balance`** | **Informational** — tie-out *unavailable*, not failed |

Principle: a **hard blocker** prevents asserting the next readiness level; a **warning** is surfaced but doesn't block Complete; **informational** is context. Absence of a declared balance is *informational* (can't tie out), **never** a silent pass.

---

## 5. Tie-out definitions

- **Statement tie-out** (financial): `ending_balance − starting_balance` (declared) **==** Σ signed row amounts **==** posted bank-GL movement over the statement period. Three numbers that must agree. **Requires declared balances.**
- **Import tie-out** (structural): `row_count == valid + flagged + error`; and `posted + skipped + voided + remaining == parsed`. Internal disposition consistency.
- **Reconciliation tie-out** (period): bank GL balance **==** `BankAccount.balance` (stored) **==** txn-derived (the health page already computes stored-vs-derived); plus AR/AP/CC GL-vs-subledger.

**What should never be inferred:**
- The bank's **declared closing balance** — must come from the statement; computing it from row sums and then "tying out" against the same rows is **circular** and a guaranteed false pass.
- A **"Reconciled" status** — must be *derived from real agreement*, never assumed because Complete.
- **Confidence as correctness** — match-suggestion confidence (P1.2) is not reconciliation truth.

---

## 6. Readiness scorecard (characterization — keep it small)

A useful month-end view needs ~4–6 indicators, **not** an enterprise checklist:

**Per statement:** (1) Complete? (rows remaining) · (2) Reconciled? — tie-out ✓ / ✗ / *unavailable (no declared balance)* · (3) Review pending (count) · (4) Failed/blocked (count).

**Per month/company:** (1) Statements reconciled X/Y · (2) Recon-health clean? (AR/AP/CC/bank within tolerance) · (3) Clearing/settlement resolved? · (4) Review queue empty?

Each indicator is a **tri-state** (ok / attention / unavailable) with a drill-through to the offending rows. Avoid dozens of green ticks; favor "what's blocking" over "everything we checked."

---

## 7. Accountant workflow (four users)

| User | Must see before "complete" | Unnecessary noise |
|------|----------------------------|-------------------|
| **Restaurant owner** | Statement Complete; anything unusual (unexpected fees, clearing not resolved) | CoA cache drift, GL-vs-subledger internals |
| **Small business owner** | Complete + a plain Reconciled/Not-yet signal + review queue empty | GL account-level detail, tie-out arithmetic |
| **Internal bookkeeper** | Statement Reconciled (tie-out numbers), review queue, recon health (AR/AP/CC/bank), clearing status | firm-level roll-ups |
| **External accountant** | Month Reconciled + **tie-out evidence** + audit trail + recon health + close-readiness; defensibility | the queue UX itself; cosmetic prefs |

Design implication: the **same readiness data**, **progressively disclosed** — owners see the headline status; bookkeepers/accountants expand to tie-out numbers and recon-health. Not separate products. (Disclosure depth ties to the P2.3 default-view preference — not restaurant-specific.)

---

## 8. Multi-company considerations (future-proof only)

- Readiness is **per-company** by construction (all sources are `cq`/company-scoped). Keep every readiness computation company-scoped so a future **firm roll-up** ("X/Y clients month-ready") is a clean aggregation, not a rewrite.
- A cross-client readiness board is a future multi-tenant feature (bookkeeping firms) — **out of scope now**; only ensure definitions don't bake in single-company assumptions that block aggregation.

---

## 9. FastAPI / React readiness

- **Summary endpoint** — `GET /reconciliation/readiness?period=…` → per-statement + per-month **status model**: `{ level: complete|reconciled|blocked|incomplete, tie_out: ok|mismatch|unavailable, counts: {remaining, review_pending, failed}, blockers: [...] }`. Pure read; `compute_cc_payable_recon_health` is the DTO precedent.
- **Detail endpoint** — `GET /reconciliation/readiness/{statement_id}` → blocker list with row drill-through.
- **Status model** should be an explicit enum + reasons[], not a boolean — so React can render tri-state (ok/attention/unavailable) and the "unavailable tie-out" case honestly.
- Keep readiness **read-only** (zero JEs) and **single-source** so the API and Streamlit cockpit can't drift.

---

## 10. Risks

- **Misleading indicators:** inferring `ending_balance` from row sums → false tie-out; showing "Reconciled ✓" when no declared balance exists (must be "tie-out unavailable"); presenting Complete as Reconciled.
- **False readiness:** marking a month "ready" while review items pend, or while `perform_year_end_close` would still hard-block — readiness must **agree with** the close guard, never contradict it.
- **Expensive calculations:** re-running the full `render_reconciliation_health` (per-GL-account `calculate_account_balance` + per-account txn sums) on every cockpit load (already flagged P2.1) — readiness must use cheap aggregates / cached health, not recompute per render.
- **Duplicated definitions:** two notions of "reconciled" (cockpit vs health page) drifting — derive from one source.
- **Settings that should not exist:** a manual "mark month ready" that overrides blockers; disabling tie-out; counting `skipped` rows as reconciled; any toggle that lets readiness assert without the underlying agreement.

---

## 11. Recommended MVP (smallest safe release)

**Must-have (read-only, cheap, reuse existing):**
- **Per-statement Complete** indicator — rows remaining via per-import grouping of `get_postable_rows` semantics.
- **Per-statement tie-out** — *only when `starting/ending_balance` present*: declared movement vs Σ signed rows vs posted bank-GL movement; explicit **"tie-out unavailable — no declared balance"** otherwise. (Never inferred.)
- **Review-pending count** + **failed/blocked count** per statement.

**Nice-to-have:**
- **Month roll-up** (statements reconciled X/Y) reusing cached recon-health.
- **Clearing/settlement-resolved** indicator (reuse settlement helpers).

**Defer to P3:**
- Full **Month-Ready-for-Close pre-flight** wired alongside (not duplicating) `perform_year_end_close`.
- **Firm multi-client** readiness roll-up.
- **Tie-out evidence export** for external accountants.
- Per-account period reconciliation **history**.

**Guardrails (non-negotiable):** readiness is advisory and read-only (zero JEs); tie-out is never inferred and degrades to "unavailable"; Complete ≠ Reconciled; readiness must not contradict the fiscal-close guard; single source of "reconciled."

---

*Characterization only. No code, no implementation, no DB or posting change. Core stance: distinguish Complete (workflow) from Reconciled (financial agreement); compute tie-out only from a declared bank balance and otherwise say "unavailable"; keep readiness advisory, read-only, cheap, single-source, and consistent with the existing close guard.*
