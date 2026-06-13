# BANKING-UX-03 P2.1 — Banking Landing / Cockpit Characterization

**Mode:** Characterization only — no code, no implementation, no redesign.
**Context:** P1.1–P1.3 complete (Match Queue implemented). Inputs read: BANKING_UX_01_AUDIT, BANKING_UX_02_DESIGN, BANKING_UX_03_ROADMAP.
**Purpose:** Map the current Banking landing experience and inventory the read-only surface before building a Reconciliation Cockpit (design §6, roadmap P2.1).

---

## 1. Current Banking navigation map

```
render_banking (app.py:20351)
 ├─ POS settlement entry banner (if enabled)
 ├─ section select (_banking_section_select):
 │    accounts | [pos_settlement] | import | [settings]
 ├─ accounts  → add-account form → accounts table → per-account manage  (DEFAULT landing)
 ├─ pos_settlement (if _banking_pos_settlement_enabled) → settlement entry/section
 ├─ import     → render_bank_statement_import → sub-sections: upload | review | match | history
 │                 (match = the new P1.3 Queue)
 └─ settings (if manage_banking) → _render_banking_page_settings
```

**Other banking surfaces (separate pages, not under `render_banking`):**
- **Reconciliation Health** — `render_reconciliation_health` (`:8662`): GL-integrity page (AR/AP/CC/Banking/CoA-cache). Its own nav entry.
- **Statement import** also reachable embedded vs standalone (`render_bank_statement_import(embedded=…)`).
- **Settlement import** (`reconciliation/settlement_import.py`) feeding the clearing match.

**Whole-feature gate:** `_banking_reconciliation_on(session)` → setting `banking.reconciliation_enabled` (company-level **C**). Import/Review/Match only render when enabled.

**Today there is no "landing dashboard."** The default Banking section is the **Accounts** add/list form — orientation-free; the operator must know to go Import → Match.

---

## 2. Existing visibility widgets

| Widget | Where | Shows |
|--------|-------|-------|
| **Reconciliation Health** | `render_reconciliation_health` | AR GL-vs-sub, AP GL-vs-sub, CC Payable GL-vs-sub, per-bank stored-vs-derived balance, CoA cache drift |
| **Import status** | `render_bank_statement_import` Review/History | per-import `valid_count` / `error_count` / `flagged_count`, file name, date range, created_at |
| **Settlement status** | inside `_render_bsi_deposit_clearing` + POS settlement section | Card Sales Clearing balance, unsettled card sales, matching settlement batches, fee preview |
| **Bank balances** | Accounts table + Health page | stored `BankAccount.balance`; Health adds txn-derived + diff |
| **Match progress** | P1.3 Queue header (new) | "N left" counter over `get_postable_rows` |
| **Dashboard overlap** | main dashboard | no dedicated reconciliation/cockpit widget found; bank balances surface only via Accounts/Health |

These are **scattered across three places** (Health page, Import sub-tabs, POS/match flow) — none is a single landing.

---

## 3. Existing queries / helpers that could power a cockpit (all read-only)

| Helper / query | Yields |
|----------------|--------|
| `get_postable_rows(session, cid)` | company-wide postable rows (status ∈ {staging, duplicate_flagged}, parsed) |
| `BankStatementImport` rows | `valid_count`, `error_count`, `flagged_count`, file_name, start/end_date, created_at, bank_account_id, currency |
| `BankStatementRow.status` | staging · duplicate_flagged · posted · voided · skipped · parse_error (+ `match_type`, `posted_at`, `amount`, `date`, `duplicate_reason`, `balance_after`) |
| `compute_cc_payable_recon_health(session, cid)` | **serializable dict**: company_card_enabled, gl_account_exists, gl_balance, subledger_total, difference, status (ok/warning), tolerance, cards[] |
| `calculate_account_balance` / `_for_period` | GL balances (Card Sales Clearing, Bank, AR, AP, RE…) — read-only |
| `get_unsettled_card_sales` / `fetch_unsettled_card_sales_for_visibility` | unsettled card sales (count/total/list) |
| `get_matching_settlement_rows` | pending settlement batches for a date/deposit |
| `SettlementStatementRow.status` | staging · posted (gross/fee/net per row) |
| per-account `BankTransaction` sums (Health page) | deposit/withdrawal/transfer totals → txn-derived balance |
| gate helpers | `_banking_reconciliation_on`, `_card_settlement_on`, `_company_card_on`, `_bank_charges_on` |

---

## 4. Existing metrics already available (reuse, don't re-derive)

- Per-import **valid / error / flagged** counts + recency (created_at).
- **Postable rows** count (company-wide) via `get_postable_rows`.
- **Bank balances**: stored vs txn-derived vs diff per account (Health page logic).
- **AR / AP / CC** reconciliation differences (GL vs subledger).
- **Card Sales Clearing** GL balance; **unsettled card sales** count/total; **pending settlement batches**.
- **CoA cache drift** count.

## 5. Missing metrics (no current query — would be new, read-only)

- **Statement-level outstanding amount** (sum of unmatched row amounts) — only the *count* exists today, not the summed amount.
- **Oldest unmatched row age** — no query computes the age of the oldest postable row.
- **Per-import posted/remaining progress** — `valid_count` exists, but posted-count *per import* is not aggregated (postable is company-wide).
- **Skipped count per import** — `status="skipped"` exists but isn't tiled.
- **Statement tie-out** — reconciled balance vs bank closing balance (no captured statement closing-balance; `balance_after` on rows could seed a derivation but is not used this way).
- **Month-end readiness checklist** — not computed anywhere (advisory aggregate).
- **Single bank-vs-book tie-out number** at company level.

---

## 6. Reconciliation health inventory (`render_reconciliation_health`)

Sections: **A** AR (GL vs subledger sum of open credit sales), **B** AP (GL vs sum of open payables), **CC** Payable (2110 vs subledger via `compute_cc_payable_recon_health`, only if `_company_card_on`), **C** Banking (per-account stored vs txn-derived deposit−withdrawal±transfer, with status label), **D** CoA cache drift (cached vs `calculate_account_balance` per GL account).

**Character:** this is a **GL-integrity / drift page**, not a workflow page. It computes per-account `calculate_account_balance` across **all** GL accounts and per-account `BankTransaction` sums — **potentially expensive**. It has **no** import/postable/throughput metrics and is **disconnected from the posting loop**. Compute and render are interleaved (Streamlit-coupled).

## 7. Settlement health inventory

Scattered, not consolidated:
- **Card Sales Clearing balance** — `calculate_account_balance(Card Sales Clearing)` (in `_render_bsi_deposit_clearing`).
- **Unsettled card sales** — `get_unsettled_card_sales` / `fetch_unsettled_card_sales_for_visibility` (count/total/list).
- **Pending settlement batches** — `get_matching_settlement_rows`; `SettlementStatementRow.status == "staging"`.
- **CC payable drift** — `compute_cc_payable_recon_health` (on the Health page).
- All gated by `_card_settlement_on` / `_company_card_on` — **industry-neutral**: hidden for trading/service/bookkeeping tenants with no card sales.

## 8. Month-end visibility gaps

- No **consolidated readiness** view (the design §6 checklist does not exist).
- No **per-statement** posted / remaining / residual-unmatched.
- No **oldest unmatched** age or **outstanding amount** sum.
- No **tie-out** / "statement reconciled" completion signal.
- Health page is the closest thing but is **GL-drift**, not **work-remaining**, and lives off the posting path.

---

## 9. Multi-company considerations

- **Everything is single-company-scoped** via `cq()` (→ `current_company_required()`); `compute_cc_payable_recon_health` takes an explicit `company_id`. A cockpit must run **inside an active company context**.
- **No cross-company aggregation exists** and none should be added now (one company at a time). A **cross-client cockpit** (bookkeeping firm overseeing many tenants) is a future multi-tenant feature, out of P2.1 scope.
- Settings that gate tiles (`banking.reconciliation_enabled`, card/charges toggles) are **company-level (C)** — the cockpit's visible tiles vary per company.

---

## 10. FastAPI / React readiness

- **Metrics are pure reads** → clean `GET /reconciliation/summary` aggregate. `compute_cc_payable_recon_health` already returns a **serializable dict** (DTO-shaped) — a model to copy.
- **`render_reconciliation_health` mixes compute + Streamlit render** — the compute halves (AR/AP/CC/bank-balance/drift) would extract cleanly into a read service for an API; the rendering is Streamlit-coupled.
- **`get_postable_rows` returns ORM rows** — an API cockpit wants a **count/summary** endpoint, not row payloads.
- A React **Recon Cockpit** would consume one aggregate read endpoint + drill-through links to the Queue (already API-shaped from P1.3 work).

---

## 11. Risks of introducing a cockpit

1. **Query cost on every Banking load.** The Health page already does per-GL-account `calculate_account_balance` + per-account txn sums; a cockpit reusing that wholesale would be slow on large data. Cockpit must use **cheap counts/sums**, not per-row Python loops, and avoid re-running the full Health computation.
2. **Definition drift.** A cockpit re-deriving "bank balance" or "CC difference" risks diverging from the Health page's definitions. **Reuse the same helpers** (`compute_cc_payable_recon_health`, the Health bank-balance logic) rather than re-implementing.
3. **Read-only discipline.** Cockpit must create **zero JEs** (all listed helpers are read-only; keep it that way).
4. **Default-landing change.** Making the cockpit the default Banking section changes first-load behavior — should be a **default-view setting** (design §5: **A** = cockpit default; **B**/**C** overrides), not a hard switch.
5. **Per-statement metrics need new grouping.** "Postable" is company-wide; per-import posted/remaining tiles require a new aggregation that doesn't exist (keep MVP to company-wide to avoid behavior surprises; per-statement is a follow-on).
6. **Tile gating.** Settlement/CC tiles must gate on `_card_settlement_on`/`_company_card_on` to stay industry-neutral; reconciliation gate on `_banking_reconciliation_on`.
7. **Missing metrics ≠ free.** Oldest-unmatched, outstanding-amount, tie-out, readiness checklist are **new queries** — scope them explicitly (some belong in P2.4, not the MVP cockpit).

---

## 12. Minimal viable cockpit (lowest-risk P2.1)

**Read-only landing that reuses existing helpers and drills into the P1.3 Queue. No new posting, no new heavy computation.**

- **Import health tile:** per recent import `valid_count` / `error_count` / `flagged_count` + company-wide **postable count** (`get_postable_rows`). (Cheap.)
- **Bank balances tile:** reuse the Health page's stored-vs-derived per-account logic (or just stored balances for the MVP to stay cheap).
- **Settlement/CC tile (gated):** `compute_cc_payable_recon_health` (already a dict) + Card Sales Clearing balance + unsettled-card-sales count. Hidden when card settings off.
- **Drill-through:** each tile links into the Match Queue (and Review/History) scoped appropriately.
- **Defer to P2.4/later (new metrics):** outstanding-amount sum, oldest-unmatched age, per-statement posted/remaining, tie-out, readiness checklist.
- **Default-view setting:** cockpit as Banking landing is **A** default, overridable **B**/**C** (don't hard-replace Accounts).
- **No change** to `match_post`, `services.posting`, or any posting behavior; zero JEs created.

---

## 13. Tests needed before implementation (test-first)

1. **Aggregate correctness** — cockpit counts/sums (postable, valid/error/flagged, balances) match seeded data and match the existing Health/Import definitions.
2. **Definition parity** — cockpit bank balance / CC difference equal `render_reconciliation_health` / `compute_cc_payable_recon_health` outputs (no drift).
3. **Read-only** — rendering the cockpit creates **zero** JournalEntries / BankTransactions.
4. **Tile gating** — settlement/CC tiles hidden when `_card_settlement_on` / `_company_card_on` off; whole cockpit gated by `_banking_reconciliation_on`.
5. **Company isolation** — metrics reflect only the active company (cq scope); no cross-company leakage.
6. **Drill-through scope** — tile links land on the correctly-scoped Queue/Review.
7. **Default-view setting** — A default = cockpit; B/C overrides honored; Accounts still reachable.
8. **Performance guard** — cockpit avoids per-row Python loops / full-Health recomputation on load (assert query count / shape stays bounded).

---

*Characterization only. No code, no implementation. A cockpit must be read-only over the existing reconciliation/CC/balance helpers, single-company-scoped, tile-gated for industry-neutrality, and create no journal entries.*
