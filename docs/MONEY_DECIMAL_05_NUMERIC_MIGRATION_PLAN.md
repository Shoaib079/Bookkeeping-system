# MONEY-DECIMAL-05 — Alembic Numeric Migration Plan

**Mode:** Audit / planning only. **No production code change, no `models.py` change, no Alembic file change, no schema change, no Decimal migration, no PostgreSQL runtime switch.** Plans the `Float → Numeric` migration to run **after** MD-01..04b, before any PostgreSQL production cutover.

## Context

- **MD-01** inventoried **99 `Float` money columns / 38 tables** (zero `Numeric` today); Float is identical on the SQLite→PG engine swap, so `NUMERIC` is the deliberate, rounding-sensitive change.
- **MD-02** pinned golden posting vectors; **MD-03** added `services/money.py` Decimal helpers; **MD-04a/04b** added Decimal posting + profit-allocation helpers. All green; nothing is wired into models yet.
- The precision tiers are **already defined by the helpers**: `MONEY_PRECISION = 0.01` (2 dp), `FX_PRECISION = 0.0001` (4 dp), `RATE_PRECISION = 0.00000001` (8 dp).

## 1. Column classification

Map each money column family to a target type (driven by the MD-03 precision tiers):

| Target | Columns (families) | Rationale |
|---|---|---|
| **`Numeric(19, 2)`** | All currency **amounts / balances**: `JournalEntryLine.debit/credit`; `ChartOfAccounts.balance`; `Sale.amount/paid_amount/balance`; `ExpenseRecord.amount`; `Purchase.amount`; `Payable.amount/paid_amount/balance`; `BankAccount.balance`; `BankTransaction.amount`; `BankStatementRow.debit_amount/credit_amount/amount/balance_after/original_amount`; `BankStatementImport.starting/ending_balance`; `SettlementStatementRow.gross/fee/net_amount`; `PartnerMovement.amount`; worker/salary `amount/gross_salary/deductions/net_salary`; daily-close totals (`cash_sales`…`daily_profit_estimate`, `recon_variance`); EOD/external-verification totals (`external_*/erp_*/variance_*/z_report_*`); `opening/expected/actual_cash`, `difference`; `total_net_income`, allocation `amount`, `net_income_snapshot`, `re_balance_at_close`; `Budget.amount`, etc. | Reporting currency = 2 dp; matches `quantize_money`. The bulk of the 99. |
| **`Numeric(19, 4)`** | **Native/reporting-currency FX amounts**: `JournalEntryLine.amount_native`; `Sale.native_amount`; `ExpenseRecord.native_amount`; `Purchase.native_amount` (any `native_amount` / `amount_native`). | Already rounded to 4 dp in the kernel; matches `quantize_fx`. |
| **`Numeric(19, 8)`** | **FX rates**: `Sale.fx_rate`, `ExpenseRecord.fx_rate`, `Purchase.fx_rate` (all `fx_rate`). | Rate precision; matches `quantize_rate`. |
| **Remain `Float` (out of scope — not money)** | **Quantities**: `Product.quantity/min_stock`, `InventoryMovement.change`. **Percentages**: `Partner.profit_share_pct`, allocation `share_pct`. | Units and ratios, not currency. Percentage exactness is a **separate later decision** (could become `Numeric(9,6)`), explicitly out of this money migration. |

**SQLite caveat (critical):** SQLite has **no true decimal type** — `NUMERIC` is type *affinity*, and values are still stored as REAL (float) unless stored as TEXT. So on SQLite the change is mainly a **type declaration + Python-boundary `Decimal` (`asdecimal=True`)** change, **not** exact decimal storage. **Exact decimal storage lands only on PostgreSQL** (true `NUMERIC`). The migration's SQLite value is preparing the schema + routing Python arithmetic through Decimal; the precision payoff is on PG.

## 2. Migration plan

- **New revision `0002_money_numeric`** — never edit `0001_baseline` (frozen per P3.3/P3.4). `0002` `down_revision = "0001"`.
- **PostgreSQL (direct alter):** `ALTER TABLE … ALTER COLUMN … TYPE NUMERIC(19,2) USING (col)::numeric(19,2)` (and 19,4 / 19,8 per tier). The `USING` clause **quantizes** existing doubles (ROUND_HALF_UP semantics enforced at the data-migration step, not truncation).
- **SQLite (batch alter):** SQLite cannot `ALTER COLUMN TYPE`; use Alembic `with op.batch_alter_table(...)` (table rebuild). Because the change spans 38 tables, the rebuild must **preserve every index/unique/FK** — hand-reconcile against the `migrate_schema()`-created indexes (same discipline as the P3.4 baseline). On SQLite the type change is affinity-level and low-risk for values, but the rebuild's constraint preservation is the real work.
- **Model change is a separate slice** (not in `0002`): switching `models.py` to `Numeric(19,2, asdecimal=True)` **and** routing services through `services/money.py` so Python receives `Decimal`. The Alembic `0002` and the model/type switch should land together behind the cutover gate, with golden vectors as the guard.
- **`migrate_schema()` stays authoritative** until the Alembic cutover (P3.8 series); `0002` is applied via the same flag-gated, backup-first path.

## 3. Risk list

- **Quantization of existing Float values** — IEEE-754 doubles (e.g. `100.0100000001`) must quantize to `100.01` via ROUND_HALF_UP; a naive cast/truncate could shift a half-cent. **Golden vectors (MD-02) are the guard.**
- **SQLite gives no real exactness** — easy to over-claim; document that exactness is PG-only and SQLite remains lossy until PG cutover.
- **Cache columns** (`ChartOfAccounts.balance`, `BankAccount.balance`) are derived — re-sync via `sync_account_balances` / delta recompute after migration rather than trusting the converted cache; lower risk but must be re-derived.
- **Null/default handling** — nullable money columns stay nullable; `default=0.0` becomes `Decimal('0.00')`; no NOT-NULL tightening in this migration.
- **Batch rebuild on SQLite** — must preserve all indexes/uniques/FKs (the partial `WHERE is_void = 0` indexes, `uq_*` constraints); a dropped constraint is a silent integrity regression.
- **Mixed float/Decimal arithmetic** — until services route fully through `money.py`, mixing `Decimal` columns with `float` math raises `TypeError`; the model switch and service routing must land together.
- **Downgrade risk** — `0002` downgrade (NUMERIC→Float) on populated data is itself lossy; **prefer restore-from-backup** over downgrade for rollback.
- **Percentage/quantity scope creep** — keep them Float; do not bundle.

## 4. Test plan

- **SQLite migration smoke:** on a **copy** of `erp_data.db`, `alembic upgrade 0002`; app starts; representative read/write/post works; `alembic downgrade` is **not** the rollback (restore-from-backup is).
- **PostgreSQL optional migration test** (`ERP_TEST_POSTGRES_URL`): build to head incl. `0002`; assert columns are `NUMERIC(19,2/4/8)`; insert/round-trip values are **exact** (e.g. `0.1 + 0.2 == 0.30`).
- **Golden vectors still pass** (MD-02): posting math under the Decimal path reproduces the pinned vectors **exactly**.
- **Reports still match:** P&L, Balance Sheet, Cash Flow, Trial Balance unchanged **to the cent** before vs after; JE balance guard still within tolerance.
- **Quantization correctness:** a fixture of "ugly" doubles quantizes to the expected 2/4/8-dp Decimals (ROUND_HALF_UP).
- **Constraint preservation:** post-migration schema retains every index/unique/FK (diff vs pre-migration).

## 5. Safe implementation slices (for Cursor — DO NOT implement here)

- **MD-05-IMPL-1 — author `0002_money_numeric` (against empty DB):** create-only generation, hand-reconciled; no DB touched; equivalence test vs the intended schema.
- **MD-05-IMPL-2 — model type switch + service routing:** `models.py` → `Numeric(asdecimal=True)`; services consume `services/money.py`; golden vectors + reports guard. Lands with `0002` behind the cutover gate.
- **MD-05-IMPL-3 — data-migration quantization step:** the `USING`/batch-rebuild quantization (ROUND_HALF_UP); cache re-sync; backup-first.
- **MD-05-IMPL-4 — SQLite smoke + PG migration test + golden/report parity.**
- **MD-05-IMPL-5 — flag-gated cutover** (reuse the P3.8 startup-authority + backup + owner-confirmation machinery); SQLite first, PG parity before production.

## 6. Do-not-touch list

- **`0001_baseline`** — never edit; `0002` is additive.
- **Quantity columns** (`quantity`, `min_stock`, `change`) and **percentage columns** (`profit_share_pct`, `share_pct`) — remain Float; out of scope.
- **`migrate_schema()`** — stays authoritative until the separate Alembic cutover; not removed/disabled here.
- **Posting rounding semantics** — preserved exactly; the Decimal path must reproduce the golden vectors, not change them.
- **No PostgreSQL runtime switch**; SQLite remains production runtime in this plan.
- **No model/Alembic/schema edits in this audit.**

## 7. ROADMAP update recommendation

- Record **MONEY-DECIMAL-05 = planned** under the MONEY-DECIMAL track: classification fixed (2/4/8-dp tiers + Float-stays for quantity/percentage), migration = new `0002` (PG direct-alter / SQLite batch-rebuild), model switch + service routing as a paired slice, golden-vector + report parity as the gate.
- State the **cutover gates**: all MD tests green · golden vectors pass under Decimal · `0002` applied on a backed-up DB · schema equivalence + constraint preservation · PG dual-run parity · owner backup + confirmation. Reuse the **P3.8 flag-gated, backup-first** cutover machinery.
- Note the **SQLite-exactness caveat** prominently so the value proposition (PG-only exactness) is not over-claimed.

## Test run note

The task lists `pytest` for `test_money_decimal_01_audit`, `_02_golden_posting_vectors`, `_03_money_helpers`, `_04_char_posting_math`, `_04b_char_profit_allocation_rounding`, and the full suite. This audit **changes no code**, so they remain as they are (green per MD-01..04b). pytest cannot execute in this sandbox (no `sqlalchemy`); run them locally. This audit adds only a doc + a pure-stdlib doc-contract test.

## No-change statement (MONEY-DECIMAL-05 audit)

- **No production code, no `models.py`, no Alembic file, no schema change, no Decimal migration, no PostgreSQL runtime switch.** Column classification + migration plan + risk list + test plan + slices + do-not-touch + roadmap recommendation only.

---

*Audit/planning only. Classification (driven by MD-03 tiers): currency amounts/balances → `Numeric(19,2)`; native FX amounts (`native_amount`/`amount_native`) → `Numeric(19,4)`; `fx_rate` → `Numeric(19,8)`; quantities (`quantity/min_stock/change`) and percentages (`profit_share_pct/share_pct`) **remain Float** (out of scope). Migration = new `0002_money_numeric` (never edit 0001): PG direct `ALTER … TYPE NUMERIC USING ::numeric` (quantize ROUND_HALF_UP), SQLite `batch_alter_table` rebuild preserving all indexes/uniques/FKs; model switch to `Numeric(asdecimal=True)` + service routing through `services/money.py` is a paired slice behind the cutover gate. **Critical caveat: SQLite has no true decimal — exactness lands only on PostgreSQL; SQLite change is affinity + Python-boundary Decimal.** Risks: quantization of existing doubles (golden vectors guard), derived-cache re-sync, constraint preservation on SQLite rebuild, mixed float/Decimal during transition, lossy downgrade (rollback = restore backup). Tests: SQLite smoke, optional PG migration (exact NUMERIC), golden vectors pass, reports match to the cent, quantization correctness, constraint preservation. Cutover reuses P3.8 flag-gated, backup-first machinery; PG dual-run parity + owner confirmation required. Risk LOW (audit) — nothing changes; real risk is in the deferred conversion, fully gated.*
