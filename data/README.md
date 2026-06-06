# Reference data (tracked in git)

Small files needed for tests, imports, and first-time setup. **Not** your live database or uploaded files.

| Path | Purpose |
|------|---------|
| `fixtures/bank_statement_sample.csv` | Bank statement import tests and manual import trials |
| `fixtures/settlement_statement_sample.csv` | Card settlement import tests and manual trials |
| `settings.example.json` | Example company defaults (currency, tax rate, fiscal year) |

## Local-only (gitignored)

| Path | Purpose |
|------|---------|
| `../erp_data.db` | SQLite database — created on first `streamlit run` |
| `../uploads/` | Imported statement files and attachments |
| `../backups/` | Manual and automatic DB backups |

Chart of accounts and transaction categories are seeded from Python (`registry/coa_seed.py`, `registry/categories_seed.py`) on startup — no separate data files required.
