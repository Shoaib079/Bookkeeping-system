# P3.8-B — Alembic Authority Cutover Design

**Mode:** Documentation + lightweight contract test only. **No runtime change in this slice.** `migrate_schema()` is **not removed, not disabled**; startup behavior is unchanged; no `alembic upgrade`, no stamping, no PostgreSQL switch, no model/accounting/API/UI change.
**Status:** **No runtime change yet.** `migrate_schema()` **remains the default and authoritative now.** Alembic becomes authoritative **only in a future, separately approved slice**, and **only when the feature flag is explicitly enabled**.
**Context:** P3.5 stamped `erp_data.db` to `0001`; P3.7 added read-only schema detection; P3.8-A added startup diagnostics after `migrate_schema()`; `migrate_schema()` remains authoritative. This document designs the **future** flag-gated transition where Alembic takes over.

## 1. Feature flag design

A single environment flag governs the transition. **Default preserves today's behavior.**

```
ERP_ALEMBIC_AUTHORITATIVE=0   # default
```

| Value | Meaning | Behavior |
|-------|---------|----------|
| `0` (default) | **Current behavior** — `migrate_schema()` is authoritative | startup runs `migrate_schema()`; P3.7/P3.8-A diagnostics observe-only; Alembic never drives schema |
| `1` | **Alembic-first behavior** (future) | startup uses the §2 decision matrix; Alembic drives schema; `migrate_schema()` retained as a legacy no-op safety net only |

Flag rules:
- **Default is `0`** — absent/unset/empty/invalid all resolve to `0` (**fail safe to current behavior**).
- The flag is **read once at startup**; flipping it requires an app restart (no live re-authority).
- `1` is **opt-in only** and is never set automatically; it is set deliberately by an operator after the §1–§4 gates pass.
- **This slice does not introduce the flag into runtime** — it specifies it. `migrate_schema()` remains the default now regardless of any value; the flag has no runtime effect until the future cutover slice wires it in.

## 2. Startup decision matrix (target — not implemented here)

When `ERP_ALEMBIC_AUTHORITATIVE=1` (future), startup inspects the DB and branches. **Inputs:** is the DB new/empty? does it have an `alembic_version`? is it at head? is it a legacy unstamped DB? is it ahead of code?

| # | DB state | Detection | Action | Operator action required |
|---|----------|-----------|--------|--------------------------|
| 1 | **New / empty DB** | no app tables, no `alembic_version` | **`alembic upgrade head`** → ends at `0001` | none (empty DB — nothing to back up) |
| 2 | **Existing stamped DB at head** | `alembic_version == head` (`0001`) | **verify only** — no migration runs; start normally | none |
| 3 | **Existing stamped, behind head** | `alembic_version` < head | **require operator action**: back up + confirm, then `alembic upgrade head` | backup + explicit confirmation before upgrade |
| 4 | **Legacy unstamped DB** | app tables present, **no `alembic_version`** | **do NOT auto-upgrade.** Verify schema == `0001` (equivalence); if equal, require backup + `alembic stamp 0001` (operator-confirmed). If schema ≠ `0001`, **stop startup** with a clear message | backup + stamp under confirmation; manual review if not equivalent |
| 5 | **Ahead-of-code DB** | `alembic_version` > known heads | **stop startup / fail closed** — "DB newer than app"; never downgrade | restore matching app version or restore backup |

- When the flag is `0`, **none of the above runs** — `migrate_schema()` is authoritative and the matrix is inert.
- **Fail closed on ambiguity:** any unrecognized/conflicting state (e.g. partial tables, multiple heads, unreadable `alembic_version`) **stops startup** with an explicit, actionable message — never a silent guess and never an automatic upgrade.
- **Failure messages** must name the DB, the current `alembic_version`, the expected head, and the exact required operator action (back up / stamp / upgrade / restore).

## 3. Migration flow

- **New DB:** `alembic upgrade head` builds the schema from `0001` (PG always; SQLite may keep `create_all` only if equivalence-guarded). No backup needed — the DB is empty.
- **Existing stamped DB (at head):** **verify head only** — confirm `alembic_version == 0001`; no DDL, no migration runs; start normally.
- **Existing stamped DB (behind head):** **backup → operator confirmation → `alembic upgrade head`** (additive only). Never auto-upgrade populated data without both.
- **Unstamped legacy DB:** **require backup + stamp process** — verify schema equivalence to `0001`, back up, then `alembic stamp 0001` under operator confirmation (records `alembic_version` only; **no DDL**, no data touch). If not equivalent, stop and require manual review; never auto-upgrade a legacy DB.

## 4. Safety rules

- **Never auto-upgrade a user DB without backup** — any `upgrade` touching an existing populated DB requires a verified **backup first** and **explicit operator confirmation**.
- **Never delete accounting rows** — consistent with the void-not-delete policy; migrations never delete `journal_entries`, `journal_entry_lines`, `sales`, `purchases`, `payables`, movements, allocations, etc.
- **No destructive migration** — schema changes are additive/non-destructive; no drops of accounting columns/tables.
- **Explicit operator confirmation** for any production schema change — no unattended/automatic production upgrades.
- **Fail closed on ambiguity** — unknown or conflicting DB state stops startup rather than guessing or auto-migrating.

## 5. Rollback

- **Restore the backup** if a cutover/upgrade fails (stop app, replace the SQLite file / `pg_restore`).
- **Disable the flag** — set `ERP_ALEMBIC_AUTHORITATIVE=0` to immediately revert to the default `migrate_schema()` path.
- **Revert to the `migrate_schema()` path** — because `migrate_schema()` is retained (not removed), turning the flag off restores the previous authoritative behavior with no schema change required.
- **Never manually edit accounting tables** — recovery is restore-from-backup + flag-off only; never hand-fix a live `alembic_version` or accounting data.

## 6. Test strategy (for the future cutover slice)

- **Flag off (default)** — `migrate_schema()` authoritative; Alembic drives nothing; suite green.
- **Flag on** — the §2 decision matrix governs startup.
- **Stamped DB** (`alembic_version == 0001`) — verify-only; no migration; app starts; suite green.
- **Unstamped legacy DB** — no auto-upgrade; equivalence verified; stamp instruction surfaced (or stamped under confirmation in a controlled test).
- **Ahead-of-code DB** (`alembic_version` > head) — startup fails closed with a clear message; no downgrade.
- **Migration failure** — a forced failure leaves the DB unchanged / restorable; clear error; no partial destructive state.

## 7. Retirement criteria — when `migrate_schema()` can finally be removed

All must hold before removal:
- **Bake-in period** — Alembic-authoritative (`flag=1`) has run stably across a defined window with no schema incidents.
- **No legacy unstamped DBs remain** — every known/target DB is stamped at a known revision (no DB depends on `migrate_schema()` to evolve).
- **PostgreSQL parity complete** — Alembic-built PG schema verified equivalent to the SQLite reference (and dual-run posting parity green) where PG is in scope.
- **Cutover proven stable** — flag default can be flipped to `1` confidently; rollback path exercised; no reliance on `migrate_schema()` for new schema.
- Removal is its **own final slice** (the P3.9-equivalent), separate from this design and from the first cutover.

## Future PostgreSQL path

- **New PostgreSQL DBs are created via Alembic** (`upgrade head` from `0001`) — never via `migrate_schema()`.
- **`migrate_schema()` never runs on PostgreSQL** (its SQLite DDL/PRAGMA is invalid there).
- **Optional dual-run parity before production** — compare the Alembic-built PG schema to the SQLite reference and run the posting parity harness before any production PG switch.

## No-change decisions (P3.8-B)

- **No runtime/startup change; `migrate_schema()` stays the default and authoritative now.**
- **The flag is specified, not wired** — `ERP_ALEMBIC_AUTHORITATIVE` has no runtime effect in this slice.
- **Alembic becomes authoritative only in a future approved slice**, and only when the flag is explicitly set to `1`.
- **No `alembic upgrade`, no stamping, no PostgreSQL switch, no model/accounting/API/UI change, no `Float → Decimal`.**

---

*Design only — no runtime change yet. `migrate_schema()` remains the default and authoritative now. Future flag-gated transition: `ERP_ALEMBIC_AUTHORITATIVE=0` (default = current behavior) / `=1` (Alembic-first, opt-in). When on, startup branches by DB state (new → upgrade head; stamped-at-head → verify only; stamped-behind → backup+confirm+upgrade; unstamped legacy → verify+backup+stamp under confirmation, never auto-upgrade; ahead-of-code → fail closed). Safety: never auto-upgrade without backup, never delete accounting rows, no destructive migration, explicit operator confirmation, fail closed on ambiguity. Rollback = restore the backup + disable the flag + revert to the retained migrate_schema() path. Retirement of migrate_schema() only after bake-in + no legacy DBs + PG parity + proven-stable cutover.*
