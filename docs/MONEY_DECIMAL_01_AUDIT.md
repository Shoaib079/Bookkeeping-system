# MONEY-DECIMAL-01 — Float / Money Audit

**Mode:** Audit only (2026-06-16). No schema, model, migration, posting, report, or Decimal conversion changes.

**Goal:** Inventory every monetary `Float` column and float arithmetic path before PostgreSQL **production** runtime cutover. SQLite remains production runtime; PostgreSQL is test-only today.

**Baseline:** Full suite **4045 passed** (post P2-HARDEN-01 H-01/H-02, AUTH-SESSION-02-IMPL-3).

**Cross-refs:** [P3.1 PostgreSQL Compatibility](./P3_1_POSTGRES_COMPATIBILITY_AUDIT.md) (R4 — Float identical on engine swap; NUMERIC is separate) · [P4.0 Postgres Enablement](./P4_0_POSTGRES_ENABLEMENT_PLAN.md) (Float unchanged for swap) · [TD-MIG-04](./TECH_DEBT_AND_MIGRATION_CLEANUP.md#global-migration-td-mig) · [ROADMAP § MONEY-DECIMAL-01](../ROADMAP.md#money-decimal-01)

---

## Executive summary

| Theme | Finding |
|-------|---------|
| **ORM money columns** | **99** `Column(Float, …)` across **38** model classes — **zero** `Decimal` / `Numeric` today |
| **Application arithmetic** | Universal `float` + `round(x, 2)`; JE balance guard `abs(deb − cred) > 0.01` |
| **Decimal usage in repo** | **None** in production code (`from decimal import Decimal` not used) |
| **PG engine swap (Float)** | **Safe today** — IEEE-754 double on both SQLite and PG ([P3.1 R4](./P3_1_POSTGRES_COMPATIBILITY_AUDIT.md)) |
| **PG production cutover blocker** | **MONEY-DECIMAL-01** — deliberate `NUMERIC`/`Decimal` changes rounding semantics; must be characterized before production PG |
| **Alembic baseline `0001`** | Reflects current `Float` schema; **Float→Decimal excluded** from baseline per [P3.3](./P3_3_ALEMBIC_BASELINE_PLAN.md) — requires **new revision** when implemented |

---

## 1. Float inventory (models.py)

**Total:** 99 `Float` columns on 38 tables.

### Tier A — Core GL / transactional money (must become Numeric)

| Table | Fields | Role |
|-------|--------|------|
| `JournalEntryLine` | `debit`, `credit`, `amount_native` | Source of truth for GL; `amount_native` already rounded to 4 dp in kernel |
| `ChartOfAccounts` | `balance` | **Cache** derived from JE lines (`sync_account_balances`); not authoritative |
| `Sale` | `amount`, `paid_amount`, `balance`, `fx_rate`, `native_amount` | AR / revenue posting |
| `ExpenseRecord` | `amount`, `fx_rate`, `native_amount` (+ legacy mirrors) | Expense posting |
| `Purchase` | `amount`, `fx_rate`, `native_amount` | Purchase posting |
| `Payable` | `amount`, `paid_amount`, `balance` | AP subledger |
| `BankAccount` | `balance` | **Cache** updated by `apply_account_balance_delta` / void reversal |
| `BankTransaction` | `amount` | Banking GL + cache delta |
| `BankStatementRow` | `debit_amount`, `credit_amount`, `amount`, `balance_after`, `original_amount` | Reconciliation |
| `BankStatementImport` | `starting_balance`, `ending_balance` | Statement tie-out |
| `SettlementStatementRow` | `gross_amount`, `fee_amount`, `net_amount` | Card settlement |
| `PartnerMovement` | `amount` | Partner GL |
| `WorkerMovement` | `amount`, `gross_salary`, `deductions`, `advance_recovery`, `net_paid` | Payroll GL |
| `PartnerProfitAllocation` | `total_net_income` | Close/allocation |
| `PartnerProfitAllocationLine` | `amount` | Allocation split |
| `YearEndClose` | `net_income_snapshot`, `re_balance_at_close` | YEC snapshot |
| `CustomerLedgerEntry` | `amount` | Customer subledger |
| `ExpenseDraft` | `amount` | Receipt capture spine |
| `Budget` | `amount` | Planning (non-posting but money) |
| `RecurringExpenseTemplate` | `amount` | Template amount |
| `RecurringExpenseDraft` | `amount` | Draft amount |
| Legacy (`CashSale`, `CreditSale`, `Salary`, `Expense`) | `amount` | Read-only migration sources |

### Tier B — Operational / POS / EOD aggregates (money — convert with Tier A)

| Table | Fields | Notes |
|-------|--------|-------|
| `EndOfDayClose` | 13 floats (sales/expense/purchase/payment/bank totals, `daily_profit_estimate`, `recon_variance`) | Snapshot aggregates; must match sum of underlying txs |
| `ExternalSalesVerification` | 14 variance/total fields | POS vs ERP reconciliation |
| `DailyCashReconciliation` | `opening_cash`, `expected_cash`, `actual_cash`, `difference` | Cash count |
| `MenuPriceHistory` | `price_gross` | Menu pricing |

### Tier C — Inventory / recipe quantities (defer or separate scale)

| Table | Fields | Notes |
|-------|--------|-------|
| `Product` | `cost_price`, `unit_price`, `quantity`, `min_stock` | `quantity` is not currency — consider `Numeric(19,4)` not `(19,2)` |
| `InventoryTransaction` | `change` | Quantity delta |
| `Ingredient` | `cost_per_base_unit` | Unit cost |
| `Recipe` | `yield_quantity` | Quantity |
| `RecipeLine` | `quantity`, `waste_percent` | `waste_percent` is ratio, not money |

### Tier D — Non-money Float (may remain Float)

| Table | Fields | Rationale |
|-------|--------|-----------|
| `Partner` | `profit_share_pct` | Percentage 0–100 |
| `PartnerProfitAllocationLine` | `share_pct` | Percentage |
| `Worker` | `base_salary` | **Borderline** — payroll money; convert with Tier A for consistency |
| `ReceiptDraftSuggestion` | `suggested_payment_confidence`, `extraction_confidence` | ML score 0–100 |
| `ReceiptLearningMap` | `confidence_cached` | ML score |

### Tier E — Multi-currency helpers

| Field | Tables | Current | Recommendation |
|-------|--------|---------|----------------|
| `fx_rate` | Sale, ExpenseRecord, Purchase | Float, default 1.0 | `Numeric(19, 8)` or keep Float until Tier A stable |
| `native_amount` | Sale, ExpenseRecord, Purchase | Float | `Numeric(19, 4)` — matches kernel `round(net * fx_rate, 4)` |
| `currency` | String columns | OK as-is | No change |

---

## 2. Money field classification

| Class | Count (approx) | Action |
|-------|----------------|--------|
| **P0 — Posted money** | ~45 columns | **Must** become `Numeric` before PG production |
| **P1 — Cached balances** | `ChartOfAccounts.balance`, `BankAccount.balance` | Convert with P0; re-sync from JE after migration |
| **P2 — Aggregates / snapshots** | EOD, external verification, daily cash | Convert with P0; characterize sum parity |
| **P3 — Quantities / unit costs** | Product, recipe, inventory | Separate slice; scale `(19,4)` |
| **P4 — Percentages / confidence** | profit share, waste %, AI confidence | **May remain Float** indefinitely |

---

## 3. Calculation & service map

### Posting kernel (`services/posting.py`) — highest risk

| Pattern | Locations | Decimal impact |
|---------|-----------|----------------|
| JE balance guard | `abs(total_debit - total_credit) > 0.01` | Tolerance must use `Decimal('0.01')` |
| Line accumulation | `total_debit += debit` (float order preserved verbatim per PS-P1) | **Golden vectors required** — order may change with Decimal |
| `round(x, 2)` | Sale balance, receivable payment, partner allocation last-share, worker payroll | Replace with quantize to 2 dp |
| `round(x, 4)` | `amount_native` on JE lines | Keep 4 dp policy |
| Profit allocation | Last partner absorbs remainder (`100.01` → `[50.0, 50.01]`) | Explicit penny absorption algorithm must be re-pinned |
| YEC / period close | `func.sum` on debit/credit + 0.01 thresholds | SQL aggregate type changes on PG Numeric |

### Banking cache (`services/banking_balance.py`)

- `round(float(amount), 2)` on every delta — must match posting amounts bit-for-bit after conversion.

### Write services (`write_sales`, `write_expenses`, `write_purchases`, …)

- `native = round(amount * fx_rate, 2)` — entry point from API `float` body fields.

### Read / report services

| Module | Float usage |
|--------|-------------|
| `read_balances.py` | `_net_balance_for_lines` sums floats; `round(..., 2)` on liquid position |
| `read_reports.py` | Trial balance, P&L, balance sheet — all `round(bal, 2)` |
| `read_ar_ap.py` | Open balance `round(amount - paid, 2)` |
| `read_reconciliation.py` | `TIE_OUT_TOLERANCE = 0.01`; signed amount helpers |
| `read_ledger.py` | Line amounts from ORM Float |

### Streamlit UI (`app.py`)

- `_parse_amount_str` → **`float(cleaned)`** — all manual entry
- `amount_input` returns `float | None`
- Report render paths duplicate many `round` / `0.01` checks (TB, RE, OBE, bank derived vs cached)
- `sync_account_balances` / legacy `calculate_account_balance` shims delegate to `read_balances`

### Receipt AI

- `ExpenseDraft.amount` (Float)
- `ReceiptDraftSuggestion` confidence fields (Float — Tier D)
- `services/receipt_learning.py` score `round(score, 2)` (0–100, not currency)

---

## 4. Tests relying on float behavior

| Test area | Pattern | Pre-Decimal action |
|-----------|---------|-------------------|
| `tests/helpers/commit_parity.py` | `journal_line_tuples` → `(account_id, debit: float, credit: float)` | Extend for Decimal equality |
| P2 / P0 write tests | `abs(deb - cred) < 0.02` journal balanced helpers | Centralize tolerance helper |
| `test_fastapi_p2_closing_write.py` | `100.01` allocation → `[50.0, 50.01]` odd-cent absorption | **Golden vector — do not break** |
| `test_banking_service01_char_balance_delta_matrix.py` | `pytest.approx(110.01)` | Re-pin after Decimal |
| `test_cc_recon_health.py` | `abs(difference) < 0.01` | Same |
| `tests/test_posting_service01_*.py` | ~40+ characterization files pin kernel outputs | Run full matrix before/after |
| Dual-run / PG parity (`tests/p3_dual_run_utils.py`) | Persists float state across engines | Add Numeric parity lane post-MD |

**No test uses `Decimal` today.**

---

## 5. SQLite vs PostgreSQL implications

| Topic | SQLite (runtime) | PostgreSQL (test-only) | After Numeric migration |
|-------|------------------|------------------------|-------------------------|
| Storage type | `REAL` (8-byte float) | `DOUBLE PRECISION` | `NUMERIC(p,s)` exact |
| Engine swap with Float | Identical arithmetic ([P3.1](./P3_1_POSTGRES_COMPATIBILITY_AUDIT.md)) | Same | N/A |
| ORM `Numeric(asdecimal=True)` | Stored as string; works | Native exact | Preferred |
| Existing data | ~all values representable as 2 dp money | PG test DB seeded fresh | One-time `CAST`/Python migration for legacy SQLite files |
| Aggregates | `SUM(debit)` on float | Same on double | `SUM` on numeric — different rounding on large ledgers |
| JE imbalance guard | 1-cent float tolerance | Same | Must use decimal tolerance |

**Key insight:** PostgreSQL **test** cutover with Float is already supported. **Production** PG cutover is blocked until MONEY-DECIMAL-01 completes — not because Float breaks on PG, but because production requires exact decimal semantics long-term.

---

## 6. Alembic migration risk

| Risk | Severity | Mitigation |
|------|----------|------------|
| **`0001_baseline` encodes Float** | Medium | Do **not** edit `0001`; add `0002_money_numeric_*` revision |
| **Autogenerate proposes Float→Numeric** | High | Strip from autogenerate until MD slice; manual revision only ([P3.4-B](./P3_4_B_BASELINE_AUTHORING_PLAN.md)) |
| **SQLite `ALTER COLUMN` limited** | High | Table rebuild or batch copy pattern (same as Phase 14A rebuild discipline) |
| **Cached balances drift** | Medium | Post-migration `sync_account_balances()` from JE lines |
| **Dual-write period** | Medium | Avoid — big-bang per column group with backup |
| **Rollback** | Medium | Restore DB backup; do not hand-edit accounting rows |

---

## 7. Risk list

| ID | Risk | Severity | Status |
|----|------|----------|--------|
| **MD-01** | 99 Float money columns — no exact decimal in DB | **High** | Open |
| **MD-02** | Posting kernel float accumulation order pinned by PS-P1 tests — Decimal may change pennies | **High** | Open |
| **MD-03** | Universal `0.01` tolerance masks float noise — unsafe with Decimal unless redefined | **Medium** | Open |
| **MD-04** | `BankAccount.balance` / `ChartOfAccounts.balance` cache can diverge from JE | **Medium** | Pre-existing; re-sync after migration |
| **MD-05** | `_parse_amount_str` → float — binary float from user input (e.g. 0.1+0.2) | **Medium** | Open |
| **MD-06** | FX `amount_native` at 4 dp vs reporting at 2 dp — policy must stay explicit | **Medium** | Open |
| **MD-07** | Profit allocation last-partner penny absorption | **Medium** | Golden test exists — must re-pin |
| **MD-08** | API/FastAPI JSON numbers are JSON floats today | **Medium** | Accept str/Decimal parse at boundary later |
| **MD-09** | Inventory quantities mixed with money in same migration wave | **Low** | Defer to MD-P3 slice |
| **MD-10** | Bundling Numeric change with PG engine swap | **High** | **Forbidden** — separate projects ([P3.1](./P3_1_POSTGRES_COMPATIBILITY_AUDIT.md)) |

---

## 8. Decimal policy recommendation

### Column types (SQLAlchemy → PostgreSQL)

| Use | SQLAlchemy | PG | Python |
|-----|------------|-----|--------|
| Reporting currency amounts | `Numeric(19, 2)` | `NUMERIC(19,2)` | `Decimal` quantize `0.01` |
| FX native amounts | `Numeric(19, 4)` | `NUMERIC(19,4)` | `Decimal` quantize `0.0001` |
| FX rates | `Numeric(19, 8)` | `NUMERIC(19,8)` | `Decimal` |
| Quantities | `Numeric(19, 4)` | `NUMERIC(19,4)` | `Decimal` |
| Percentages / ML confidence | `Float` | `DOUBLE PRECISION` | `float` OK |

Use `Numeric(..., asdecimal=True)` everywhere money touches ORM.

### Arithmetic rules (proposed — not implemented)

1. Parse user/API money at boundary → `Decimal` (never `float(cleaned)` for storage).
2. Quantize to 2 dp **once** at posting boundary (HALF_UP — document explicitly).
3. JE balance: `abs(debit_sum - credit_sum) <= Decimal('0.01')` (keep 1-cent tolerance).
4. Do **not** change allocation penny-absorption algorithm without golden test update.
5. Keep `amount_native` at 4 dp; reporting displays 2 dp.

### Central helper (future slice)

- `services/money.py`: `parse_money`, `quantize_reporting`, `quantize_native`, `je_balanced()` — **not created in this audit**.

---

## 9. Migration strategy (safest order)

1. **Characterization first** — golden posting vectors on current Float (baseline snapshot).
2. **Boundary helpers** — parse/quantize module; no schema change.
3. **Posting kernel** — switch internal math to Decimal; all `test_posting_service01_*` green on SQLite Float columns (ORM coerces).
4. **ORM + Alembic `0002+`** — column type migration on PG test DB; dual-run parity.
5. **SQLite production data migration** — offline script: backup → migrate types → `sync_account_balances` → verify TB.
6. **Read/report services** — Decimal-native sums.
7. **UI `amount_input`** — Decimal parse path.
8. **PG production cutover** — only after steps 1–7 green.

**Do not** migrate SQLite production schema until characterization suite exists.

---

## 10. Tests to add before implementation

| Priority | Test | Rationale |
|----------|------|-----------|
| **P0** | `test_money_decimal_01_golden_posting_vectors.py` | Pin JE lines for cash sale, expense, purchase, receivable payment, allocation `100.01`, worker salary |
| **P0** | `test_money_decimal_01_je_balance_tolerance.py` | Document 1-cent guard with edge cases |
| **P1** | Extend dual-run harness for Numeric PG vs Float SQLite (pre/post) | Engine + type parity |
| **P1** | Bank balance delta matrix under Decimal | BS-05 parity |
| **P1** | `read_reports` golden totals for seeded ledger | Report regression |
| **P2** | `_parse_amount_str` → Decimal equivalents | EU/US format preservation |
| **P2** | FX payment gain/loss paths | `abs(fx_diff) >= 0.01` threshold |

---

## 11. Safe implementation slices

| Slice | Scope | Risk |
|-------|-------|------|
| **MD-AUDIT-01** | This document + contract test | None |
| **MD-02** | Golden posting vectors (tests only, Float baseline) | Low |
| **MD-03** | `services/money.py` helpers + unit tests; no schema | Low |
| **MD-04** | Posting kernel Decimal internal math (SQLite Float columns) | **High** — full posting suite |
| **MD-05** | Alembic `0002` Numeric columns + PG test DB only | Medium |
| **MD-06** | Write/read services + banking_balance | Medium |
| **MD-07** | SQLite production migration script + balance re-sync | **High** |
| **MD-08** | UI parse + amount_input | Medium |
| **MD-P3** | Inventory/recipe quantities (separate scale) | Low–Med |

**Do not combine** MD-04 with PG production switch or Alembic authority flip in one PR.

---

## 12. Do-not-touch list (during early slices)

- GL posting formulas (account pairs, ref_types, void cascade order)
- `0.01` JE imbalance threshold **semantics** (may reimplement with Decimal, not widen)
- Profit allocation last-partner remainder absorption logic
- `apply_account_balance_delta` / `reverse_account_balance_delta` sign rules ([BS-05](./BANKING_SERVICE_01_BS05.md))
- Card settlement / CC bill payment posting paths
- Alembic `0001_baseline` revision content
- `migrate_schema()` authority until MD-07 + Alembic bake-in complete
- Feature flags / API auth / company stamp wrappers

---

## 13. Answers to audit questions

1. **Which fields must become Decimal/Numeric?** — Tier A + B (+ `Worker.base_salary`); see §1–2.
2. **Which can remain Float temporarily?** — Tier D (percentages, ML confidence); optionally `fx_rate` until FX slice.
3. **Precision/scale?** — Money `(19,2)`, native FX `(19,4)`, rates `(19,8)`, quantities `(19,4)`.
4. **Safest migration strategy?** — Golden tests → money helpers → posting kernel → Alembic new revision → SQLite data migration → reports/UI; never bundle with PG swap ([§9](#9-migration-strategy-safest-order)).
5. **Tests before schema?** — Golden vectors + JE tolerance + dual-run ([§10](#10-tests-to-add-before-implementation)).
6. **Avoid breaking SQLite data?** — Backup; ORM reads Float during transition; typed migration script; `sync_account_balances` verify TB to 0.01.
7. **Defer until PG runtime?** — PG **production** cutover and pooling hardening; PG **test** with Float may continue per [P4.0](./P4_0_POSTGRES_ENABLEMENT_PLAN.md) until MD-05 lands.

---

## 14. ROADMAP update recommendation

Update `ROADMAP.md` § MONEY-DECIMAL-01:

- **Status:** Audit complete (2026-06-16) — 99 Float columns inventoried; blocker for PG **production** clarified (Numeric semantics, not Float engine parity)
- **Next:** MD-02 golden vectors → MD-03 money helpers → MD-04 posting kernel
- **TD-MIG-04:** Raise priority **Low → High**; link this doc
- Keep PG runtime **test-only** until MD-05+ green

---

*Audit only. No code changed except this doc and `tests/test_money_decimal_01_audit.py` contract test.*
