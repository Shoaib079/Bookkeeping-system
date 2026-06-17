# BANKING-UX-04 — Configurable Banking Workflow: Architecture Audit

**Mode:** Architecture audit only. **No implementation, no code changes, no schema change** (none needed — see §"where the setting lives"), **no changes to `services/posting.py`, `reconciliation/match_post.py`, or GL line tuples.** Recommends how a company-scoped `banking.workflow_mode` should reshape **UI visibility/routing only**.

## Recommendation — **PROCEED** (low risk, UI-only)

This is a **UI-only routing/visibility change behind a company-scoped setting**, and the codebase **already has the exact precedent**: `render_banking` builds its section list conditionally from company-scoped toggles (`_banking_reconciliation_on`, `_banking_pos_settlement_enabled`, `_company_card_on`). `banking.workflow_mode` is one more setting of the same shape. No posting/recon/GL change, no schema change. Proceed with the S1–S4 slices; the only real watch-item is **never bypassing the existing duplicate-post safeguard** (which lives in match_post and stays untouched).

## 1. Current architecture assessment

| Surface | Location | Notes |
|---|---|---|
| **Banking page** | `render_banking` `app.py:21080` | Builds `_bank_opts` then `_banking_section_select("banking_section", _bank_opts)` (`:21101`); fall-through renders the **manual bank-account add form** + accounts list (`:21117+`). |
| **Section options (conditional)** | `app.py:21089-21100` | `cockpit` (if recon on + `view_bank_statement_import`), `accounts`, `pos_settlement` (if enabled), `import` (always), `settings` (if `manage_banking`). |
| **Statement import** | `_render_banking_statement_import` `app.py:20985` | "import" section. |
| **Match & Post** | `reconciliation/match_post.py` | **LOCKED — do not touch.** Holds the duplicate-post safeguard + GL posting. |
| **Reconciliation cockpit** | `_render_banking_recon_cockpit` (called `:21104`) | "cockpit" section; gated by recon-on + permission. |
| **Bank accounts** | accounts section / fall-through form `:21117+` | Add `BankAccount`; opening-balance posting via existing helper. |
| **Manual bank transaction entry** | Add Transaction bank paths (`presets={"banking_section":"import"}` `app.py:3565`; bank reroute `:26222-26225`) + BSI manual flows | Must remain available in **all** modes. |
| **POS settlement** | `_render_banking_pos_settlement_section` / `_entry` (`:21087`,`:21107`) | "pos_settlement" section; gated by `_banking_pos_settlement_enabled`. Card **clearing**, not a POS product (VENDOR-NEUTRAL-01). |
| **Company card flow** | `_company_card_on` → account kind `credit_card` (`:21116-21138`) | Distinct from POS settlement. |
| **Existing company-scoped banking settings (the precedent)** | `_banking_reconciliation_on`, `_banking_pos_settlement_enabled`, `_company_card_on` | Read per-company; **exactly the pattern `banking.workflow_mode` should follow.** |

**Key observation:** the page already *assembles* its sections from company settings. `workflow_mode` only needs to influence **order, default landing, and which sections sit under an "Advanced" expander** — it does **not** add or remove any section.

## 2. Where the workflow-mode setting should live

- **Define** `banking.workflow_mode` in **`registry/settings_catalog.py`** as a **company-scoped** enum: `statement_first` | `hybrid` | `manual_first`, **default `statement_first`** (statement-first preferred). Stored as a key/value company setting — **no schema change** (same store as `banking.reconciliation`/`pos_settlement`; those are settings, not columns).
- **Read** via the existing company-setting getter (`get_setting`/`get_effective_config`), wrapped in a thin `_banking_workflow_mode(session)` helper mirroring `_banking_reconciliation_on`.
- **Consume only in UI:** `ui/banking.py` / `render_banking` (section **order**, **default landing**, **Advanced** grouping) and the **Add Transaction bank-path visibility**. 
- **Must NOT live in / be read by** `services/posting.py`, `reconciliation/match_post.py`, `app.py` startup, or any service — it is **presentation routing**, not business logic (keeps the FastAPI/React boundary clean: the React banking page reads the same setting value).

**Mode → UI behavior (no workflow removed):**
- **statement_first:** default landing = import (or cockpit if recon-on); the manual bank-account form + manual bank-txn entry move under an **"Advanced"** expander; import prominent.
- **hybrid:** both visible at top level; default landing configurable (reuse the existing `_banking_apply_session_landing` mechanism).
- **manual_first:** default landing = manual entry; import remains in the picker (not hidden).
- **All modes:** every section stays in `_bank_opts`; mode changes only order/default/Advanced-grouping. **Manual always reachable.**

## 3. What must NOT change

- **`services/posting.py`** — posting kernel + GL line tuples: untouched.
- **`reconciliation/match_post.py`** — match/post + **duplicate-post safeguard**: untouched; mode must never bypass it.
- **Journal entries / GL tuples** — identical outputs regardless of mode.
- **Existing imports/matching** — unchanged; statement-first is preferred, not mandatory.
- **Duplicate-post safeguards** — remain the single source of truth for "don't post twice"; UI mode does not add a second dedup path.

## 4. Implementation slices

- **BANKING-UX-04-S1 — audit + setting contract:** ✅ **Complete** — `docs/BANKING_UX_04_AUDIT.md` + `tests/test_banking_ux_04_audit.py`. Tag: `banking-ux-04-s1-audit`.
- **BANKING-UX-04-S2 — UI routing/visibility:** ✅ **Complete** — `banking.workflow_mode` setting + `_banking_workflow_mode` getter + `ui/banking.py` section order/landing/Advanced panel. Tests: `tests/test_banking_ux_04_s2_workflow_mode_routing.py`. Tag: `banking-ux-04-s2-workflow-mode-routing`.
- **BANKING-UX-04-S3 — Add Transaction bank/manual placement:** ✅ **Complete** — workflow mode on Add Transaction type order, statement callout, Advanced manual bank type. Tests: `tests/test_banking_ux_04_s3_add_transaction_bank_paths.py`. Tag: `banking-ux-04-s3-add-transaction-bank-paths`.
- **BANKING-UX-04-S4 — tests/docs/React-readiness:** 📋 Planned — extended test matrix + freeze setting for React banking page.

## 5. Risk matrix

| Risk | Severity | Mitigation |
|---|---|---|
| **Duplicate manual + imported postings** | High (accounting) | Mode is **UI-only**; the match_post duplicate-post safeguard is unchanged and remains the only dedup authority. A test asserts mode change does not alter posting outputs. |
| **Hidden manual entry becomes inaccessible** | Medium | "Advanced" must always be reachable; a test asserts manual entry is present (under Advanced) in **every** mode. |
| **POS Settlement vs company credit card confusion** | Medium | Keep them distinct (already are); plain wording (§7); POS settlement = card clearing (VENDOR-NEUTRAL-01), credit card = an account kind. |
| **Role/permission visibility** | Medium | Mode must not widen gates: `import`/`settings`/`cockpit` keep their existing `manage_banking`/`view_bank_statement_import` checks; mode only reorders what the user is already allowed to see. |
| **Multi-company setting leakage** | High (tenant) | `banking.workflow_mode` is company-scoped + read with explicit `company_id`; a test asserts company A's mode does not affect company B. |
| **React migration impact** | Low | The setting is a plain company-scoped value; the React banking page reads it the same way — no logic duplication. |

## 6. Test plan (recommended)

- **statement_first** → manual entry present **under Advanced**; import prominent / default landing.
- **hybrid** → both manual and import visible at top level.
- **manual_first** → manual entry prominent; import still available in the picker.
- **Posting invariance (the critical one)** → the same bank activity produces **identical** journal entries / posting outputs in all three modes (golden compare; mode is UI-only).
- **Company isolation** → company A's `workflow_mode` does not affect company B.
- **Existing reconciliation tests unchanged** → match_post / recon suites pass without modification.
- **Permission invariance** → mode does not surface a section the role cannot access.

## 7. UI wording (plain language; EN/TR)

Owner-facing label (no accounting jargon): **"How do you record bank activity?"** / TR **"Banka hareketlerini nasıl giriyorsunuz?"**

| Mode | EN (plain) | TR |
|---|---|---|
| statement_first | "Start from a bank statement" | "Banka ekstresinden başla" |
| hybrid | "Both — statement and manual" | "Her ikisi — ekstre ve elle giriş" |
| manual_first | "Enter bank transactions manually" | "Banka işlemlerini elle gir" |

- Keep technical terms (reconcile / match / post / GL) **out** of the owner-facing chooser; they may stay inside the "Advanced" area. Avoid "POS" as a product word — use "card settlement" / "kart hesaplaşması".

## Implementation boundaries

- **Touch:** `registry/settings_catalog.py` (catalog entry), a thin `_banking_workflow_mode` getter, `ui/banking.py`/`render_banking` (ordering/visibility), Add Transaction bank-path visibility, tests, i18n strings.
- **Never touch:** `services/posting.py`, `reconciliation/match_post.py`, GL line tuples, journal-entry creation, the duplicate-post safeguard.
- **No schema change** — `banking.workflow_mode` is a company key/value setting (same store as the existing banking toggles).

## ROADMAP suggestions (separate from implementation)

- Record **BANKING-UX-04 = PROCEED**, UI-only, company-scoped `banking.workflow_mode` (default `statement_first`), slices S1–S4, building on the existing `banking.reconciliation`/`pos_settlement` setting pattern (no duplicate fixes).
- State the rule: **workflow mode is presentation routing only; posting/recon/GL are mode-invariant; manual entry is never removed.**

## No-change statement (BANKING-UX-04 audit)

- **No implementation, no code changes, no schema change, no posting/recon/GL change.** Architecture assessment + setting location + slice plan + risk matrix + test plan + boundaries + wording + recommendation only.

---

*Architecture audit only. `render_banking` (`app.py:21080`) already assembles its sections from company-scoped toggles (`_banking_reconciliation_on`/`_banking_pos_settlement_enabled`/`_company_card_on`) — so `banking.workflow_mode` is one more setting of the same shape: define it company-scoped in `registry/settings_catalog.py` (enum statement_first|hybrid|manual_first, default statement_first, **no schema change**), read via a thin `_banking_workflow_mode` getter, and **consume only in `ui/banking.py` + Add Transaction bank paths** (section order / default landing / Advanced grouping) — never in posting/match_post/GL. All three modes retain every section; manual is always reachable. Risks: duplicate manual+imported posting (UI-only mode never bypasses the match_post dedup), hidden-manual-inaccessible (Advanced always reachable), POS-vs-credit-card confusion (plain wording), permission widening (keep existing gates), multi-company leakage (company-scoped + explicit company_id), React (plain setting value). Tests: per-mode visibility + posting-invariance (identical JE in all modes) + company isolation + unchanged recon tests. Wording: "How do you record bank activity?" EN/TR, no jargon in the chooser. Recommendation: **PROCEED** (low risk, UI-only); slices S1 setting contract → S2 banking UI routing → S3 Add Transaction placement → S4 tests/React-readiness.*
