# FASTAPI-P0.5d — Commit Ownership & Unit-of-Work Execution Plan (TD-PS-01)

**Mode:** Characterization + execution plan. No code, no implementation, no DB, no API, no React. Preserve accounting behavior exactly.
**Inputs:** P0.5 CHAR, P0 hardening plan, migration audit, `services/posting.py`, `services/audit.py`, `services/context.py`, `reconciliation/match_post.py`, `app.py`.
**State:** P0.1–0.4 + P0.5a (DTOs) / P0.5b (company unification) / P0.5c (recon stamp) complete; tag `v0.9-fastapi-hardening` exists. This plan covers the **deepest, riskiest** remaining item — converting internal commits to a single boundary-owned commit.

**Guiding principle:** this change alters the **commit mechanism**, never the **persisted result**. Every flow must persist byte-identical rows/balances/JE lines after conversion. Roll out **family-by-family behind a flag**, validated by a **dual-run parity harness** (same flow in internal vs boundary mode → identical persisted state).

---

## 1. Current commit-ownership inventory

| Layer | Commits | Flush | Rollback |
|-------|---------|-------|----------|
| `services/posting.py` kernel `create_journal_entry` | `:668` (per JE) | `:640` | `:628` (guard), `:661` (imbalance) |
| `services/posting.py` posts/voids/close/allocation | ~25 `session.commit()` points (e.g. `:866,1364,1395,1474,1501,1569,1588,1618,1660,1680,1702,1822,1871,2034,2083,2223,2266,2467,2684`) | several `:962,1777,1795,1991,2019,2201` | via kernel |
| `services/audit.py` `record_audit` | `:70` (per audit row) | — | — |
| `reconciliation/match_post.py` posters | per-row `session.commit()` (`:304,361,477,631,…`) | per-row `:88,443,604` | — |
| `app.py` shims | call the service (which commits) then `record_audit` (commits) | — | — |

**Net today:** every action produces **N internal commits** (kernel JE + extra balance/flag commits + audit), pinned by prior CHARs (2/post, 2/recon-row, 3/close, 2/YEC, 3–4/void). Audit is the **trailing** commit and is **non-atomic** with the entity (separate commit).

## 2. Boundary design (unit of work)

- **UoW helper** (conceptual): a context manager owning one transaction — `with unit_of_work(session): <flush-only service calls>` → **commit once on success, rollback on exception**. Services no longer call `commit`/`rollback`; they `flush` and may `raise`.
- **Streamlit boundary (now):** each shim/handler wraps its service call(s) in the UoW; the **shim** commits once at the end and rolls back on exception. Replaces N internal commits with **1** boundary commit.
- **FastAPI boundary (later):** the request dependency provides the session + UoW; the **route handler** success commits, exception rolls back. **Identical UoW shape** — one boundary, two callers.
- **Commit location:** the boundary (shim/route). **Rollback location:** the boundary on exception. The kernel's current internal `rollback()` on guard/imbalance moves to the boundary — **this resolves TD-PS-04** (kernel rollback no longer discards the caller's other pending work).
- **Guard behavior preserved:** the kernel still detects period/YEC/imbalance and **raises the same `ValueError`**; the boundary catches → rolls back the whole UoW. Persisted-on-failure state = nothing (same as today for a single action; cleaner for compound flows).

## 3. Audit conversion

- `record_audit` **commits today** (`audit.py:70`), preserving legacy ownership; it is called by the shim **after** the service returns success.
- **Conversion:** under boundary mode, `record_audit` becomes **flush-only**; the boundary commits the audit row **atomically with the entity**. The shim still calls it on the success path (one audit per successful action) — only the *commit* moves.
- **Preserve:** exactly **one audit row per successful action**; row content byte-identical (`action, entity_type, entity_id, description, performed_by, company_id, timestamp` semantics).
- **Behavior improvement (characterize):** today a post-entity audit failure would leave the entity committed but audit lost; under boundary mode both roll back together — more correct, but a change on the rare failure path. Pin it.
- **Sequencing:** audit conversion happens **per family, in lockstep** with that family's flip — when a family goes boundary-mode, its audit call goes flush-only too.

## 4. Posting family sequencing (safest → riskiest)

1. **Simple sales / expenses** — single JE + audit; smallest blast radius; fully characterized. **First.**
2. **Purchases / payables** — similar single-JE; (purchase→payable creation is inline in app, not the kernel).
3. **Receivable payments** — extra sale-balance commit (2 internal) → boundary.
4. **Bank transactions** — `post_bank_transaction`/`transfer` (simple; transfer no-op path).
5. **Partner / worker / equity movements** — BankTransaction + balance + multi-branch JE + record.
6. **Profit allocation** — period-scoped JE + allocation record.
7. **Period close / year-end close** — 3-commit / 2-commit multi-step.
8. **Reconciliation `match_post`** — per-row commit + batch; recon stamp already fixed (P0.5c).
9. **Void cascades** — **last**: multi-JE reversal commits + cascade (linked payable) + flag + audit; highest count variance (e.g. `void_purchase` paid = 4).

Ascending complexity + commit-count variance + blast radius. Voids last because cascades and variable counts are hardest to re-pin.

## 5. Feature-flag strategy

- **Mode flag per family:** `commit_mode ∈ {internal, boundary}`, defaulting **internal** (today's behavior). A family flips to `boundary` only after its parity tests pass and bake.
- **internal mode:** services commit at their current points (unchanged).
- **boundary mode:** those points become flushes; the UoW boundary commits once; `record_audit` flush-only.
- **Rollback plan:** flip the family's flag back to `internal` — **instant, no deploy** — if any parity diff appears. Structural failure → `git checkout v0.9-fastapi-hardening`.
- The flag is a **runtime setting/env**, not a code branch left dangling — once all families bake in `boundary` and the internal path is retired, the flag is removed in a final cleanup.

## 6. Test requirements (per family)

| Test | Assertion |
|------|-----------|
| **Persisted-state parity** | golden snapshot of all rows/balances after the UoW — **identical** internal vs boundary |
| **GL line parity** | JE line tuples, debit/credit, ref types, dates, float order unchanged |
| **Audit parity** | exactly one audit row, content byte-identical, atomic with entity |
| **Rollback parity** | guard/imbalance failure → **nothing persisted**; same `ValueError` string |
| **Failure behavior** | closed period/YEC, `MatchPostError`, partial inputs → same outcome |
| **Company isolation** | no cross-tenant rows; recon JE + records share `company_id` |
| **No partial commit** | a mid-flow failure leaves **no orphaned** BankTransaction/record/JE (the TD-PS-04 fix) |

**Dual-run harness (the key detector):** run each representative flow **twice** — once `internal`, once `boundary` — against fresh in-memory DBs and assert the two persisted states are identical. This catches subtle divergence the count tests can't.

## 7. Commit-count strategy (replacing the old pins)

- **Old:** `mock_commit.call_count == N` (internal commits). These **break** under boundary mode (count → 1) — they are not wrong, they assert the *mechanism*, which is what's changing.
- **New:** parametrize each commit test **by mode**:
  - `internal`: keep the old `call_count == N` (until the family is retired from internal).
  - `boundary`: assert **exactly one** boundary commit + **persisted-state parity** + audit row present.
- **Invariant across both:** identical persisted state. The count tests become **mode-specific**; the **state parity** test is mode-agnostic and is the real contract. After a family bakes in boundary, drop its internal-count test.

## 8. What must not change

Accounting lines (tuples/orientation), reference types, entry dates, float accumulation order; error strings (`ValueError`, `MatchPostError`); YEC/period guard semantics; void/reversal behavior (reversal JE content, cascade to linked payable, `is_void`/`voided_at`/`void_reason`); audit row content + one-per-action cardinality; **single-company behavior** (the change is invisible to single-tenant use); **net persisted state** of every flow.

## 9. Stop / go criteria

- **Go** to the next family only when: dual-run parity green, GL/audit/rollback parity green, no partial-commit, no error-string drift.
- **Stop immediately** on: any persisted-state diff, GL line diff, audit content/cardinality diff, new orphaned row, or changed error string.
- **Revert:** flip the family flag to `internal` (instant); if structural, `git checkout v0.9-fastapi-hardening`.
- **Detecting subtle failures:** the dual-run harness over a broad flow corpus is primary; secondary — a balance-integrity sweep (GL == derived == stored) and an audit-row count reconciliation after each family bakes in a staging dataset.

## 10. Recommended first implementation slice (tiny, reversible)

- **Slice 0 — scaffolding, zero behavior change:** introduce the `unit_of_work` boundary helper + the per-family `commit_mode` flag with **every family defaulting to `internal`**. Nothing flips; behavior byte-identical. Ship + bake.
- **Slice 1 — flip `post_cash_sale` only to `boundary`:** the single simplest flow (one JE + audit). Add the dual-run parity test for cash sale; the shim opens a UoW, the kernel + `record_audit` go flush-only **for this family only**, the shim commits once. Instantly revertible via the flag.

Slice 0 carries no risk (pure scaffolding); Slice 1 is one family, one flag, one parity test — the smallest reversible proof of the whole pattern before any other family follows.

---

*Characterization + plan only. No code, no implementation, no DB/API/React. The conversion replaces N internal commits (kernel + balance/flag + audit) with **one boundary-owned commit**, family-by-family behind a `commit_mode` flag, validated by a dual-run persisted-state parity harness, voids last. Commit-count tests become mode-specific; persisted-state parity is the mode-agnostic contract. Accounting behavior — lines, references, error strings, YEC guards, void behavior, audit rows, single-company semantics — preserved exactly; TD-PS-04 (rollback discarding caller work) is fixed by moving rollback to the boundary.*
