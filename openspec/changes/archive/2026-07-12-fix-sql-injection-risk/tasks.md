## 1. Core Fix: Validate column name before SQL construction

- [x] 1.1 Extract the column-name whitelist from the for-loop into a module-level constant (`_MIGRATION_COLUMNS`) in `core/database.py`
- [x] 1.2 Add a whitelist check before `c.execute(f"SELECT {col} ...")` — raise `ValueError` if column is not in the whitelist

## 2. Verification

- [x] 2.1 Run `bandit -r core/database.py` and confirm the B608 issue no longer appears
- [x] 2.2 Run `python -c "from core.database import init_db; init_db()"` to confirm no regression
- [x] 2.3 Inspect `data/scan_results.db` to verify schema migration still works (table columns exist)
