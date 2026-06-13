# BANKING-UX-03 — Implementation Roadmap

**Source design:** `docs/BANKING_UX_02_DESIGN.md` (Cockpit-fronting-Queue, batch at the seam, classic table optional).
**This document:** a phased, test-first implementation plan. **Planning only — no code in this file.**

## Guiding constraints (apply to every phase)
- **Small, safe, independently-shippable releases** — each sub-release is behind nothing larger than a section toggle and can be reverted alone.
- **Tests first** — land characterization/contract tests *before* the UI change in the same or prior release.
- **No accounting changes, no posting changes** — every batch/queue action calls the **existing** `reconciliation/match_post` posters and `services.posting` kernel unchanged. Bulk = loop over the same contract.
- **No database changes in Phase 1** — P1 is UI-only (existing queries, existing pure helpers, Streamlit fragments, `_t` locales).
- **Preserve `services.posting` contracts** and **reconciliation orchestration ownership** — UI never reimplements posting; `match_post.py` stays the orchestrator. P1 does **not** modify `match_post.py` (it only *calls* its existing pure helpers).

## Streamlit reality check (affects sequencing)
Streamlit reruns on every interaction. "No full-page rerun per post" is achieved with **`st.fragment`-scoped reruns**, not by removing reruns. This is a dependency/risk, not an accounting concern; it is called out per phase.

---

## Recommended exact implementation order

1. **P1.1** — Error UX hardening (wording, catch `ValueError`, fix 2 untranslated literals, hide raw Row IDs). *Smallest, highest safety, unblocks confidence in later changes.*
2. **P1.2** — Confidence/suggested-kind chip surfaced in the existing Match flow (read-only, one-click accept).
3. **P1.3** — Match **queue list** (fragment-scoped) replacing the single-row dropdown; inline accept + detail slide-over (merges Review+Match context).
4. **P2.1** — Read-only **Reconciliation Cockpit** landing (import/statement/settlement/readiness) with drill-through into the P1.3 queue.
5. **P2.2** — **Batch post** of High-confidence rows (loop over existing posters) with confirm + per-row result report.
6. **P2.3** — **Configuration surface** (A/B/C settings) via the existing registry; default-view, thresholds, review requirements, unpost rules.
7. **P2.4** — Statement **tie-out / completion signal** + **unified unpost** + default detected header row.
8. **P3.x** — Mobile oversight view; learned match memory; reconciliation audit trail; React-readiness prep (post-FastAPI).

Order rationale: de-risk errors first; surface confidence before building the queue around it; ship the queue (the dominant win) before the cockpit that launches it is strictly necessary; batch after the queue exists to host it; config after the behaviors it governs exist; tie-out/unpost as polish; P3 is strategic/after-FastAPI.

---

## Phase 1 — Immediate UX wins (UI-only, no DB, no posting/accounting change)

### P1.1 — Error UX hardening
**Scope:** Reword banking/reconciliation errors for operators; ensure every statement-post call site catches **both** `MatchPostError` and `ValueError` (closed-period/YEC) and renders a friendly inline message; route the two untranslated literals through `_t`; replace "Row IDs to skip" with labelled checkboxes (no DB ids shown). No message *semantics* change — wording only.
**Files touched:** `app.py` (the `_render_bsi_*` post call sites in `render_bank_statement_import`; the Review skip control); `registry/locales/transactional.py` (+ TR locale) for the new/reworded keys. **Not touched:** `reconciliation/match_post.py`, `services/posting.py`.
**Tests required (first):** unit tests asserting (a) a closed-period statement post surfaces a friendly inline error, not an exception; (b) each `MatchPostError` path maps to its reworded `_t` key; (c) skip control no longer renders raw ids; (d) locale keys resolve in EN+TR.
**Risks:** Low. Main risk = missing a post call site (mitigate by enumerating all `_render_bsi_*` posters). i18n drift if TR not updated.
**Expected user benefit:** No dead-end exception pages at month/year boundaries; clearer recovery; no leaked database ids.

### P1.2 — Confidence / suggested-kind chip
**Scope:** In the existing Match flow, surface the already-computed suggestion (`suggest_deposit_match_kind` / `suggest_withdrawal_match_kind` / `looks_like_*`) as a visible **"Detected: …" chip with a confidence band** and a one-click **Accept**. Presentation only — the heuristics are unchanged.
**Files touched:** `app.py` (`_bsi_default_match_kind` call site and the radio block); `ui/banking.py` (a small render helper for the chip). **Not touched:** the heuristic functions themselves.
**Tests required (first):** characterization test pinning current `suggest_*` / `looks_like_*` outputs for representative descriptions (so "confidence band" is a pure relabeling); UI contract test that Accept posts via the same poster as today.
**Risks:** Low. Confidence banding must be presentation-only; do not let it gate posting.
**Expected user benefit:** Faster decisions; the system's existing intelligence becomes visible and one-click.

### P1.3 — Match queue list (fragment-scoped)
**Scope:** Replace the single-row `selectbox` in the Match section with a **scannable, filterable queue list** (filter by deposit/withdrawal/confidence, sort, search) rendered inside an `st.fragment` so accept/post reruns the fragment, not the page. Each row shows the P1.2 chip + inline **Accept**; **Review** opens a detail slide-over that merges Review+Match context with prev/next. Single-row posting still uses existing posters; no batch yet.
**Files touched:** `app.py` (`render_bank_statement_import` Match section); `ui/banking.py` (queue-list + detail render helpers). **Read-only use of** `get_postable_rows` (unchanged).
**Tests required (first):** contract test that posting one row from the queue produces an identical JE/BankTransaction to today's dropdown path; filter/sort/search produce expected subsets of `get_postable_rows`; fragment rerun does not double-post (idempotency on the existing "already posted" guard).
**Risks:** Medium — `st.fragment` behavior/version dependency; double-submit on rapid clicks (mitigate with the existing `status=="posted"` guard + disabling the button mid-post). Larger UI diff than P1.1/1.2.
**Expected user benefit:** The dominant month-end friction (one-row dropdown + full rerun) is removed; context no longer resets each post.

---

## Phase 2 — Major UX improvements

### P2.1 — Reconciliation Cockpit (read-only landing)
**Scope:** New landing surface with Import/Statement/Settlement/Readiness tiles (per design §6), each drilling into the P1.3 queue scoped to the click. **Pure reads** — reuse `get_postable_rows`, `calculate_account_balance(_for_period)`, `compute_cc_payable_recon_health`. Settlement tile only renders when card/POS settlement is enabled (industry-neutral). Readiness is advisory, never a posting gate.
**Files touched:** `app.py` (`render_banking` section list + dispatch to a cockpit renderer); `ui/banking.py` (cockpit render + a **read-only** aggregation helper). **Not** `services/posting.py`.
**Tests required (first):** aggregation helper unit tests (counts/sums match seeded data); settlement tile hidden when setting off; drill-through lands on the correctly-scoped queue; readiness checklist derives from data and posts nothing.
**Risks:** Low–Med — aggregate query cost on large imports (mitigate with simple counts, no per-row Python loops); keep it strictly read-only.
**Expected user benefit:** Orientation + month-end readiness at a glance; one place to start the work.

### P2.2 — Batch post of High-confidence rows
**Scope:** From the cockpit/queue, **"Post N High-confidence"** → confirmation summary → loop the **existing** posters per row → per-row **result report** (succeeded/failed with reason). Default: High only batch-selectable (company setting can widen — see P2.3). This is the §1 invariant in action: batch = N single posts.
**Files touched:** `app.py` / `ui/banking.py` (batch action UI + result report). **Posters unchanged.**
**Tests required (first):** contract test that batch-posting N rows yields **identical** GL/bank-txn results to N individual posts; partial-failure test (1 of 5 hits closed-period → other 4 still post, failure reported, no rollback of the 4); confirmation summary accuracy.
**Risks:** Med — partial-failure clarity is essential (one bad row must not obscure successes, and must not imply a transactional batch). Must reuse per-row commit semantics exactly (no new transaction wrapper that could change commit counts).
**Expected user benefit:** Scales from 20 to 500 rows; effort grows with ambiguity, not row count.

### P2.3 — Configuration surface (A/B/C)
**Scope:** Expose the §5 settings via the **existing registry** (`get_setting`/`set_setting`, already company-scoped — no schema change for company-level **C** settings): auto-match on/off, bulk-confidence policy, confidence thresholds, default landing view, header-detection behavior, unpost permission/reason, review-required kinds. User-level (**B**) prefs that have no store yet stay in session-state with a noted follow-up; do **not** add tables in this sub-release.
**Files touched:** `app.py` / `ui/banking.py` (settings UI in the Banking → Settings section); `registry/` setting keys/metadata. **No DB schema change** (registry is generic key/value).
**Tests required (first):** each setting changes the corresponding default/behavior; defaults match design §5 (A); company isolation of settings; thresholds are presentation-only (never gate accounting).
**Risks:** Low–Med — scope creep; keep to the §5 list. Ensure thresholds never alter posting eligibility, only presentation/selectability.
**Expected user benefit:** The configurable-ERP philosophy realized; firms/bookkeepers get control, non-accountants keep working defaults.

### P2.4 — Tie-out, unified unpost, header-row default
**Scope:** Statement **tie-out / "reconciled" completion signal** (read-only, from existing balances); a **single unpost affordance** consolidating the CC-bill path (reuse `void_credit_card_bill_payment`) and surfacing the existing "must unpost from reconciliation" rule consistently — **no change to void/accounting**; default the **detected header row** (drop the extra Apply click).
**Files touched:** `app.py` (Review/History + upload header-row), `ui/banking.py`. Unpost reuses existing reconciliation functions; **no posting change.**
**Tests required (first):** tie-out matches computed balances; unified unpost calls the existing void path and preserves its result; header-row default equals detected value and is overridable.
**Risks:** Low. Unpost consolidation must not broaden what's voidable (preserve current guards, e.g. `bsr:` blocking).
**Expected user benefit:** Operators know when a statement is done; one consistent unpost; one fewer click on every upload.

---

## Phase 3 — Future enhancements (mostly post-FastAPI / may need DB)

### P3.1 — Mobile / tablet oversight view
**Scope:** Cockpit read + month-end readiness + "approve High-confidence batch" on tablet/phone; fix the 7-option horizontal radio → vertical/segmented on narrow viewports. Mobile posting beyond batch-approve is opt-in (B), off by default; company can disable (C). Import/mapping stays desktop-first.
**Files touched:** `ui/banking.py`, mobile render paths; locale.
**Tests required (first):** narrow-viewport rendering contract; mobile-posting gate respects B/C settings.
**Risks:** Low–Med (responsive layout regressions).
**Expected user benefit:** Owner oversight on the go without exposing fragile data-entry on small screens.

### P3.2 — Learned match memory
**Scope:** Remember the chosen kind per description pattern, per tenant, to improve **suggestions only** (never auto-post Low). **Needs persistence → DB/registry change → not before Phase 3.**
**Files touched:** new read/write of a pattern store (registry or a new table — DB change); `ui/banking.py`; suggestion surfacing.
**Tests required (first):** memory influences suggestion only, never eligibility; tenant isolation; cold-start defaults to existing heuristics.
**Risks:** Med — must remain suggestion-only; privacy/tenant isolation; schema addition.
**Expected user benefit:** Fewer manual decisions over time.

### P3.3 — Reconciliation audit trail
**Scope:** Add audit on reconciliation posting (ties to PS-P7 `log_audit` + explicit `user_id`). **Coordinate with PS-P7 hardening** (ambient-vs-explicit company stamping, audit policy). Likely DB/contract touch → Phase 3.
**Files touched:** `reconciliation/` + `app.py` shim layer **under PS-P7**, not as a UX-only change.
**Tests required (first):** audit row written on success with correct actor/entity; no change to GL.
**Risks:** Med — overlaps accounting-adjacent hardening; must be done in PS-P7, not bootlegged into UX work.
**Expected user benefit:** Traceability/compliance for reconciliation actions.

### P3.4 — React-readiness prep
**Scope:** When FastAPI lands: Cockpit = `GET summary`; Queue = `GET postable (+suggested kind/confidence)`; post/batch = `POST decision(s)` over existing poster signatures; Upload wizard = client-side state in React. No work before FastAPI; this phase only *documents the mapping* the P1/P2 UI already honors.
**Files touched:** none now (design alignment).
**Tests required:** n/a until FastAPI.
**Risks:** Carries the PS-P7 risks (company stamping, audit) — fix there.
**Expected user benefit:** Smooth path to the React target without re-deriving the UX.

---

## Cross-phase test strategy (test-first ledger)
- **Contract-preservation tests** (every phase that posts): "UI path X posts identically to the current path" and "batch of N == N singles" — the guardrail that proves no accounting/posting change.
- **Characterization pins** before relabeling heuristics (P1.2) and before any reconciliation-adjacent touch (P3.3).
- **Locale resolution** tests (EN+TR) for every new `_t` key.
- **Read-only assertions** for cockpit/tie-out (assert zero JEs created).
- **Permission/setting** tests for P2.3 (defaults = design §5 A; C overrides scoped per company).

---

*Roadmap only — no code, no patches. Phase 1 is UI-only with no DB or accounting/posting change; all posting flows through the unchanged `reconciliation/match_post` + `services.posting` contracts in every phase.*
