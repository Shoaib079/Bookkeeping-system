# BACKUP-01 — Pre-Operations Safety Backup

**Checkpoint:** POST-LAUNCH-OBSERVATIONS entry gate  
**Created:** 2026-06-19 00:42:53 local  
**Operator:** automated BACKUP-01 run

## Purpose

Fresh safety checkpoint before entering POST-LAUNCH-OBSERVATIONS mode. No code, schema, migration, Docker, or live-database modifications were made — only a read-only SQLite copy and this report.

## Git checkpoint

| Check | Result |
|---|---|
| Working tree | Clean |
| Branch | `main` |
| Sync with `origin/main` | Up to date (`d2258b5`) |
| Tag `post-launch-observations-start` | `d2258b5` (OPERATOR-ROLLOUT-OR06–OR11 complete) |

### Recent commits (at checkpoint)

```
d2258b5 OPERATOR-ROLLOUT-OR06–OR11: complete COMMIT_MODE staging tiers 3–8.
58c67b5 OPERATOR-ROLLOUT-OR05: staging COMMIT_MODE_POST_EXPENSE boundary.
fcfad75 OPERATOR-ROLLOUT-OR04: staging COMMIT_MODE_POST_CASH_SALE boundary.
faae155 OPERATOR-ROLLOUT-OR03: enable API write sales on staging.
9aab0a0 OPERATOR-ROLLOUT-OR02: green PG boundary matrix on staging.
```

## Database backup

| Field | Value |
|---|---|
| Source | `erp_data.db` (repo root — live SQLite) |
| Backup path | `backups/erp_data_pre_observations_20260619_004253.db` |
| Source size | 1,773,568 bytes (1.69 MiB) |
| Backup size | 1,773,568 bytes |
| Size match | Yes (byte-identical copy) |
| Git tracked | No (`backups/*` gitignored) |

## Environment snapshot

| Item | Value |
|---|---|
| Python | 3.13.7 |
| Live DB size | 1,773,568 bytes |
| Latest commit (pre-report) | `d2258b515d5c032cf98f1ce37c104684d05c4ae7` |
| Checkpoint tag | `post-launch-observations-start` → `d2258b5` |
| Branch | `main` |

## Test verification

Command: `pytest tests/ -q` (no `COMMIT_MODE_*` or `ERP_TEST_POSTGRES_URL` exported)

| Metric | Count |
|---|---|
| Collected | 7105 |
| Passed | 7069 |
| Skipped | 34 |
| Xfailed | 2 |
| Failed | 0 |
| Duration | ~165 s |

Result: **GREEN** — matches expected baseline.

## Tags created (this checkpoint)

1. `post-launch-observations-start` — marks OR-01–OR11 complete HEAD before observations work
2. `backup-01-pre-observations` — marks this backup report commit

## Scope compliance

- No application code changes
- No ROADMAP changes
- No feature work
- No migrations
- No Docker changes
- No live database modifications (copy-only backup)

## Restore notes

To restore from this checkpoint:

```bash
cp backups/erp_data_pre_observations_20260619_004253.db erp_data.db
```

Verify file size matches source before use. Prefer stopping the app before overwrite.
