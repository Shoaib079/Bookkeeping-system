# BANKING-UX-03 P2.2 — Batch Posting Characterization

**Mode:** Characterization only — no code, no implementation.
**Context:** P1.3 Queue + P2.1 Cockpit implemented. Inputs read: BANKING_UX_03_ROADMAP, BANKING_UX_03_P1_3_CHAR.
**Purpose:** Characterize the existing per-row posting path before introducing high-confidence batch posting.

**Headline finding (challenges the design's optimism):** **confidence-of-kind ≠ completeness-of-inputs.** Knowing a row *is* a vendor payment does not tell us *which* vendor/payable. A kind is batch-safe only when its posting inputs are **fully derivable from the row alone**. By that bar, today **only `bank_fee` is unattended-batch-safe** (and `cc_bill` *only* when exactly one company card exists). Card deposits and payroll — which the design listed as batchable — are **not**, because they require per-row human selection.

---

## 1. Current per-row posting lifecycle

```
Queue row → _render_bsi_<kind> sub-form (row-scoped keys, P1.3) →
  Post button → match_post.post_*(row_id, company_id, …, user_id) →
    _row_context guard (status / parse / company) →
    _create_bank_txn (BankTransaction + apply_account_balance_delta) →
    [kind-specific record mutations] →
    app.create_journal_entry(...)  [kernel COMMIT] →
    _finalize_row (status="posted" + links) →
    session.commit()               [explicit COMMIT] →
  log_audit("Post","BankStatementRow", row.id, …)  [audit COMMIT]  ← UI layer
  st.success → st.rerun()  (or st.fragment rerun)
  except (MatchPostError, ValueError) → _bsi_render_statement_post_error
```

Each row is **independent and self-committing**; there is no cross-row transaction.

---

## 2. Poster inventory (with batch-input requirement)

| Kind | Poster | Human input required at post time | Batch-safe? |
|------|--------|-----------------------------------|-------------|
| `bank_fee` | `post_bank_charge_outflow(row_id, company_id, user_id, [subtype])` | **None** — subtype inferred from description inside the poster | **Yes** |
| `cc_bill` | `post_credit_card_bill_payment(…, credit_card_account_id)` | Card selection (auto only if a single company card) | **Only if single card** |
| `other_income` | `post_generic_deposit(…, credit_account_name)` | Credit GL choice (default exists but is a judgment) | No (review) |
| `card_clearing` | `post_deposit_clearing_match(…, sale_ids, settlement_row_id, confirm_inferred_fee)` | Sale multiselect + fee/settlement confirm | No |
| `vendor` | `post_vendor_outflow(…, vendor_id, payable_id / create_expense)` | Vendor + payable/ad-hoc choice | No |
| `worker_payroll` | `post_worker_statement_match(…, worker_id, gross/deductions/recovery)` | Worker + payroll figures | No |
| `equity_loan` | `post_partner_statement_match` / `post_equity_statement_match(…, partner_id/equity_kind, movement_type)` | Partner/kind selection | No |

`_render_bsi_bank_fee` confirms the bank_fee path takes only `row_id/company_id/user_id` — the captions are advisory; no widget feeds the poster.

---

## 3. Audit behavior

- **UI layer** calls `log_audit("Post", "BankStatementRow", row.id, "<kind> · <amount>…")` after each successful poster (the service `match_post` does **not** audit).
- One audit per posted row; **none on failure**.
- `log_audit` itself commits (its own commit) and stamps the **ambient** `_current_user` as `performed_by` (the explicit `user_id` goes to the row's `posted_by_user_id`).
- **Batch must preserve one audit per successfully posted row** — no merge, no omission.

## 4. Commit behavior

- Per row: **kernel commit** (inside `create_journal_entry`) + **explicit `session.commit()`** (persists bank txn + row finalize) + **audit commit** = effectively 2–3 commits per row.
- **No shared transaction across rows.** This is forced by TD-PS-01 (kernel commits internally) and is explicitly *not* changeable in P2.2 (no posting/service change).
- Therefore a batch of N rows = **N independent commit sequences** — there is no atomic "all-or-nothing" batch available without touching services.

## 5. Failure behavior

- A poster raises `MatchPostError` (validation) or `ValueError` (closed-period/YEC kernel guard) **before or during** its commit. On the kernel guard, `create_journal_entry` rolls back its own pending work (TD-PS-04) — but **rows already committed earlier in the batch stay committed.**
- So batch failure is inherently **partial-success**: rows 1..k-1 are posted, row k failed, rows k+1.. are unaffected. A batch UI must **report per-row outcomes**, never imply rollback.

## 6. Double-post protections

- `_row_context` raises `MatchPostError("This row is already posted")` when `status == "posted"` (also blocks skipped/parse_error/unparsed).
- This makes posting **idempotent at the row level**: re-running a batch over already-posted rows yields a clean "already posted" per-row result, **not** a double-post.
- The Post button is row-scoped (`_bsi_widget_key(..., row.id)`, P1.3); under fragment rerun this plus the status guard prevents double-submit.

## 7. MatchPostError handling

- Raised by all posters for validation/business failures; surfaced today via `_bsi_render_statement_post_error`. Messages are operator-friendly (P1.1). In batch, each `MatchPostError` becomes a per-row "failed: <reason>" entry.

## 8. ValueError handling

- Raised by the GL kernel guard for closed period/year (entry_date = row.date). Posters' UI call sites already catch `(MatchPostError, ValueError)` together. In batch, a closed-period row fails individually and is reported; the rest continue.

## 9. Which match kinds are safe for batch?

- **`bank_fee` — Yes (the only general case).** Fully determined from the row (amount + inferred subtype); poster needs no human input. This is the high-confidence batch target.
- **`cc_bill` — conditionally**, only when the company has exactly one credit-card account (auto-selected); with multiple cards it requires a choice → not batch.
- All others — **No** (need per-row selection: vendor, worker, partner, sales-to-clear, credit GL).

> The design's "post all high-confidence (commissions / card deposits / payroll / CC-bill)" overstates the safe set: only **commissions/fees (`bank_fee`)** qualify generally; **card deposits** and **payroll** require human input and must stay manual.

## 10. Which kinds must always require review?

- **`card_clearing`** (which sales? fee/settlement confirm), **`vendor`** (which vendor/payable; ad-hoc expense creates records), **`worker_payroll`** (worker + gross/deductions/recovery), **`equity_loan`** (partner/kind), **`other_income`** (credit GL is a judgment). Ad-hoc expense and equity/loan are also the kinds a company may *policy-gate* for review (design §5 C).

## 11. Transaction-boundary options

- **Option A — independent per-row commits (only option that preserves current behavior).** Batch = loop; each row commits itself; partial success possible. **Required by the no-service-change constraint.**
- **Option B — atomic batch (one transaction).** Would require suppressing per-row commits / wrapping in a single transaction → changes commit ownership (TD-PS-01) and posting behavior. **Out of scope for P2.2;** revisit only in PS-P7 hardening.
- **Recommendation:** Option A, presented honestly as "posts each row; some may succeed while others fail."

## 12. Partial-failure options

- **Stop-on-first-error** vs **continue-and-report.** Given independent commits, **continue-and-report** is correct — don't abandon 39 good rows for 1 closed-period row.
- Must **not** present as transactional; the result report is the contract.

## 13. Progress-reporting options

- **Pre-batch confirmation list** (row, amount, inferred subtype) so the operator sees exactly what will post.
- **During:** progress counter / bar (optional).
- **After:** per-row result table — ✓ posted (JE id) / ✗ failed (reason) / ↺ already posted — plus a summary ("37 posted · 2 failed · 1 already posted"). Wrap in `st.fragment` to avoid full-page reset.

## 14. FastAPI / React implications

- Batch endpoint = `POST /reconciliation/batch` taking a list of `{row_id, kind, params}` → returns a **per-row results array** (status + je_id or error). This maps **exactly** to the independent-commit reality (non-transactional bulk).
- Each array item = one existing poster call; no new posting path.
- **Atomic bulk** would need TD-PS-01 (boundary-owned transactions) first — defer.
- `bank_fee` batch is the cleanest first endpoint: input is just `[row_id, …]` (subtype inferred server-side).

## 15. Minimal safe batch design (lowest-risk P2.2)

- **Scope: `bank_fee` only** — rows the heuristic classifies as a bank charge, gated by `_bank_charges_on`. (Optional follow-on: single-card `cc_bill`.)
- **Flow:** Cockpit/Queue "Post N bank charges" → confirmation list (row · amount · inferred subtype) → loop `post_bank_charge_outflow` + `log_audit` per row → per-row result report.
- **Semantics:** continue-on-error (independent commits); idempotent (already-posted reported, not re-posted); one audit per posted row.
- **Explicitly excluded:** card_clearing, vendor, worker, partner/equity, other_income — they stay in the manual P1.3 queue (need per-row input).
- **No change** to `match_post`, `services.posting`, commit counts, or accounting — batch is a UI loop over the existing `bank_fee` poster.

## 16. Tests required before implementation (test-first)

1. **Batch == singles** — batching N `bank_fee` rows produces JEs/BankTransactions/audits **identical** to N individual posts.
2. **Continue-on-error** — a closed-period row fails (`ValueError`) while the others post; result report accurate; **no rollback** of successes.
3. **Idempotency** — re-running a batch over already-posted rows returns per-row "already posted" (`MatchPostError`), zero double-posts.
4. **Audit parity** — exactly one `log_audit("Post","BankStatementRow", row.id, …)` per successfully posted row; none for failures.
5. **Commit parity** — batch of N = N × (poster commit + audit commit); no merged/atomic transaction introduced.
6. **Gating** — batch offered only when `_bank_charges_on`; only `bank_fee`-classified rows included; no other kind ever enters the batch set.
7. **Subtype-inference parity** — `infer_bank_charge_subtype` result in batch equals the single-post path.
8. **No-service-change guard** — `reconciliation/match_post.py` and `services/posting.py` byte-unchanged by the batch feature.

---

*Characterization only. No code, no implementation. Batch posting must be a UI loop over the existing `bank_fee` poster with independent per-row commits, continue-on-error, idempotency via the existing status guard, and one audit per posted row — preserving accounting and posting behavior exactly. The safe batch set is narrower than the design assumed: `bank_fee` only (plus single-card `cc_bill`).*
