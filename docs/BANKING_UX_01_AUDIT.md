# BANKING-UX-01 — Banking Workflow Audit

**Mode:** Audit only — no code changes, no implementation.
**Basis:** code-derived (read of `render_banking`, `render_bank_statement_import`, the match-row renderers, `reconciliation/match_post.py`, `ui/banking.py`). Observations reflect the rendered Streamlit flow, not a live click-through.
**Surface reviewed:** Banking page (accounts / POS settlement / import / settings) and the statement Import → Review → Match → History loop.

---

## 1. Workflow map

```
Banking page (render_banking)
 ├─ section select: Accounts | [POS Settlement] | Import | [Settings]
 ├─ Accounts: add-account form (name/bank/number/currency/[kind]/balance) → table → per-account manage
 ├─ POS Settlement (if enabled): settlement entry/section
 └─ Import (render_bank_statement_import) → sub-section select:
      ├─ Upload:  pick bank acct → header row (auto-detect + Apply btn) → file upload →
      │           column mapping (2-col selectboxes, auto-suggested) → preview → commit to staging
      ├─ Review:  pick import (dropdown) → read-only row table →
      │           skip rows (multiselect of Row IDs + btn) → unpost CC bill (separate selectbox+reason+btn)
      ├─ Match:   get_postable_rows → SINGLE-ROW selectbox → line summary →
      │           radio "What is this?" (7 kinds) → kind-specific sub-form → Post → rerun → repeat
      └─ History: list of prior imports
```

**Core operator loop = Match.** One staging row at a time: select from dropdown → confirm/adjust the auto-suggested kind → complete a kind-specific sub-form → post → page reruns → repeat for the next row. The seven kinds: `card_clearing`, `other_income`, `equity_loan`, `vendor`, `worker_payroll`, `cc_bill`, `bank_fee`.

---

## 2. Click-count analysis (typical statement row, Match tab)

| Step | Interaction | Clicks/inputs |
|------|-------------|---------------|
| Land on Match | section select → "Match" | 1 |
| Pick the row | single-row dropdown | 1 (+ scroll/scan) |
| Confirm/adjust kind | radio (auto-suggested, often correct) | 0–1 |
| Kind sub-form | e.g. vendor: pick vendor → pick payable / ad-hoc toggle → (confirm fee) | 2–4 |
| Post | submit button | 1 |
| **Per row total** | | **~5–8 interactions**, then full-page rerun |

For a 40-line month-end statement that is **~200–320 interactions** plus 40 full-page reruns. There is **no bulk post, no "post all high-confidence matches," and no multi-select on the Match tab** — the dropdown forces strictly one row per cycle. Upload adds ~5–7 interactions (account, header-row Apply, file, per-field mapping, commit).

---

## 3. Operator pain points

1. **One-row-at-a-time dropdown (highest friction).** The Match tab posts a single row chosen from a `selectbox`; there is no list view with inline "post" actions and no batch. The dominant cost of month-end is repetition here.
2. **No auto-post / no confidence batching.** The system already computes a suggested match kind (`suggest_deposit_match_kind` / `suggest_withdrawal_match_kind`) and recognises commissions, card deposits, payroll, CC bills — but the operator must still hand-confirm and post each one. High-confidence rows could be queued for one-click bulk posting.
3. **Full-page rerun after every post** resets scroll/context; the operator re-orients on each cycle.
4. **Review and Match are separate tabs.** Seeing a row's context (Review) and acting on it (Match) requires tab switching; selection state doesn't carry across.
5. **Skip exposes raw DB Row IDs.** Review uses a `multiselect` labelled literally "Row IDs to skip" over internal `id`s — operators shouldn't see or pick database ids.
6. **Header-row auto-detect needs a second click.** Detection surfaces an info banner + a separate "Apply" button rather than defaulting to the detected value.
7. **Fragmented unpost.** CC-bill unpost lives in Review; `bsr:`-tagged bank transactions are explicitly blocked from the Banking void path; there is no single "unpost this statement row" affordance.
8. **Per-row session-state juggling** (`bsi_match_kind_row`, `bsi_match_kind`) is invisible plumbing that occasionally forces the kind back to a default when switching rows.

---

## 4. Visibility issues

- **No at-a-glance reconciliation status in the posting flow.** Operator cannot see "X postable, Y unmatched, Z errors, last import on …" while matching. (`render_reconciliation_health` exists but is a separate page focused on GL-vs-subledger.)
- **No statement tie-out.** The Match flow never shows "reconciled balance vs. bank closing balance" so the operator can't tell when a statement is fully reconciled.
- **Raw IDs leak** (Review "Row IDs to skip"; row labels include `#import_row_index`).
- **Suggested match kind isn't surfaced as a confidence signal** — it silently sets the radio default; the operator gets no "auto-detected: POS commission" cue with a one-click accept.
- **Posted vs. remaining isn't a progress bar** — only a flat history list.

---

## 5. Month-end audit

- The Import → Review → Match → History structure is sound for *occasional* reconciliation but scales poorly to a **full month posted row-by-row** (see §2). There is no "work the queue to zero" mode.
- **No high-confidence bulk path:** commissions, card-settlement deposits, payroll, and CC-bill lines are individually detectable yet must be posted one at a time.
- **No reconciliation completion signal** (statement fully matched / residual unmatched amount).
- **Closed-period interaction:** posting a row dated in a closed period/year is blocked only by the GL kernel guard (raises a `ValueError`, not a `MatchPostError`) — at month/year boundaries the operator may hit an unfriendly error if the match UI doesn't catch `ValueError` (see §8).
- **Recon health** (`render_reconciliation_health`, CC GL-vs-subledger) is the closest thing to a close checklist but is disconnected from the posting loop.

---

## 6. Mobile audit

- **Match radio `horizontal=True` with up to 7 kinds** will wrap awkwardly on a narrow viewport.
- **Upload + 2-column column-mapping** is cramped on mobile; file upload + per-field selectboxes are a poor small-screen experience (arguably a desktop-only task).
- The **single-row dropdown** is, ironically, more mobile-friendly than a wide table — but the per-row reruns and sub-forms still make month-end impractical on a phone.
- Recommend treating **statement import/match as desktop-first** and exposing only *light* mobile affordances (e.g. review status, approve a queued high-confidence batch) per the existing mobile UI system.

---

## 7. Dashboard recommendations

A **Reconciliation Cockpit** (could be a live Cowork artifact pulling from the same queries) showing:

- Postable rows by type (deposit/withdrawal), unmatched count, parse errors, duplicates.
- Auto-postable (high-confidence) count with a single "review & post all" entry.
- Per-statement progress: posted / remaining / residual unmatched amount; reconciled-vs-closing-balance tie-out.
- CC GL-vs-subledger health (reuse `compute_cc_payable_recon_health`) and last-import recency.
- Drill-through from a cockpit row straight into the relevant match action (collapsing Review+Match).

---

## 8. Error-message audit

- **Service-layer messages are strong and actionable** (`MatchPostError`): e.g. "Enable **Bank charges** in Company Setup to book the processor fee.", "Processor fee of … will post to Bank Charges. Confirm the fee before posting.", settlement gross/net/fee balance checks. Keep these.
- **Untranslated English literals** in the UI: "Row IDs to skip" (Review) and "Row has no clear deposit/withdrawal amount." (Match) — i18n gap; everything else routes through `_t(...)`.
- **`ValueError` vs `MatchPostError` gap:** closed-period/YEC blocks raise a kernel `ValueError`; if a match-post call site only catches `MatchPostError`, a boundary-dated row would surface as an unhandled Streamlit exception rather than a friendly inline error. Worth confirming each post call site catches both.
- **Raw-ID-bearing labels** in error/selection contexts reduce clarity for non-technical operators.

---

## 9. FastAPI-readiness observations

- **Service shape is already good:** the 7 `match_post` posters take an explicit `company_id`, return JSON-friendly `dict`s, and raise `MatchPostError` for failure — a clean API contract. The heuristic helpers (`suggest_*`, `looks_like_*`, `card_deposit_style`) are pure and directly reusable.
- **Stateful coupling lives in the UI**, not the service (the `bsi_match_kind*` session-state juggling) — an API would expose a stateless "suggest kind for row" + "post row with kind+params" pair, which the services already support.
- **Latent multi-tenant risk:** statement JEs are stamped with the *ambient* company (via the app `create_journal_entry` shim) while records carry the *explicit* `company_id` (documented in the PS-P6-5 CHAR). For an API serving multiple tenants this must be unified to the explicit `company_id`.
- **No audit at the reconciliation layer:** `match_post` posts without `log_audit`; an API path would need explicit `user_id` + an audit write for traceability.

---

## 10. Prioritized improvement list

### P1 — Immediate UX wins
- **Match-tab list with inline post**, replacing the single-row dropdown: show postable rows as a list (already grouped/labelled) with the auto-suggested kind pre-selected and a per-row Post action. Removes the dominant month-end friction.
- **Surface the auto-detected match kind as a labeled suggestion** ("Detected: POS commission") with one-click accept, instead of a silent radio default.
- **Replace "Row IDs to skip" with checkboxes/labels** (hide DB ids) and translate the two English literals.
- **Catch both `MatchPostError` and `ValueError`** at every post call site so closed-period posts show a friendly inline message.

### P2 — Valuable improvements
- **High-confidence bulk post:** a "review & post all auto-matched" action for commissions/card deposits/payroll/CC-bill lines, with a confirmation summary.
- **Reconciliation cockpit / dashboard** (§7), including per-statement progress and reconciled-vs-closing-balance tie-out.
- **Unify unpost** into a single "unpost statement row" affordance across CC-bill and other matched rows.
- **Default header-row to the detected value** (drop the extra Apply click).
- **Merge Review + Match context** so selecting a row shows its detail and its action together.

### P3 — Nice-to-have
- **Mobile-light reconciliation view** (status + approve queued batch only; keep import/mapping desktop-first); fix the 7-option horizontal radio wrap.
- **Persisted operator preferences** (last bank account, default kind per description pattern).
- **Audit trail for reconciliation posting** (ties into the FastAPI/user-context work).
- **Statement completion badge** ("fully reconciled") in History.

---

*Audit only. No code changed, no implementation. Observations are code-derived; a live operator walkthrough would refine the click-count estimates.*
