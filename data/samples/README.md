# Sample rows

200 rows from each table, committed so you can see the **schema and grain** without
downloading anything. The full dataset (60k users, ~72k orders, ~1M events, ~128 MB
SQLite) is not in git because it is deterministic and rebuilt in about ten seconds:

```bash
python3 src/generate_data.py
```
