"""
sql.py — a tiny SQL scratchpad so practising is frictionless.

    python3 src/sql.py "SELECT city, COUNT(*) FROM orders GROUP BY city"
    python3 src/sql.py -f myquery.sql
    python3 src/sql.py --tables            # list tables and their columns
    python3 src/sql.py --block cohort_matrix   # run a named block from sql/*.sql
    python3 src/sql.py                     # interactive mode: type queries, see results

No setup, no server, no login — the database is a single file at data/zomato.db.
"""

import argparse
import os
import sys
import pandas as pd

from sqlkit import connect, DB, resolve


def show(df: pd.DataFrame, limit=50):
    with pd.option_context("display.max_rows", limit + 5, "display.width", 160,
                           "display.max_columns", 40):
        if len(df) > limit:
            print(df.head(limit).to_string(index=False))
            print(f"... {len(df) - limit:,} more rows ({len(df):,} total)")
        else:
            print(df.to_string(index=False))
            print(f"({len(df):,} rows)")


def list_tables(a):
    tabs = a.raw("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    for t in tabs["name"]:
        cols = a.raw(f"PRAGMA table_info({t})")
        n = a.raw(f"SELECT COUNT(*) AS n FROM {t}").iloc[0, 0]
        print(f"\n{t}  ({n:,} rows)")
        for c in cols.itertuples():
            print(f"    {c.name:<22} {c.type}")


def main():
    ap = argparse.ArgumentParser(description="Run SQL against data/zomato.db")
    ap.add_argument("query", nargs="?", help="SQL to run (quote it)")
    ap.add_argument("-f", "--file", help="run SQL from a file")
    ap.add_argument("--block", help="run a named block from sql/*.sql, e.g. cohort_matrix")
    ap.add_argument("--tables", action="store_true", help="list tables and columns")
    ap.add_argument("--limit", type=int, default=50, help="max rows to print")
    args = ap.parse_args()

    if not os.path.exists(DB):
        sys.exit("data/zomato.db not found — run:  python3 src/generate_data.py")

    a = connect()

    if args.tables:
        list_tables(a)
    elif args.block:
        sql = resolve(a.blocks, args.block)
        print(sql + "\n" + "-" * 70)
        show(a.raw(sql), args.limit)
    elif args.file:
        show(a.raw(open(args.file).read()), args.limit)
    elif args.query:
        show(a.raw(args.query), args.limit)
    else:
        # interactive: type a query, end it with ';' or a blank line, Ctrl-D to quit
        print(f"SQLite scratchpad on {os.path.relpath(DB)}")
        print("Type a query (finish with ';' or a blank line). Ctrl-D to quit.\n")
        buf = []
        while True:
            try:
                line = input("sql> " if not buf else "  ... ")
            except EOFError:
                print()
                break
            if line.strip().endswith(";") or (not line.strip() and buf):
                buf.append(line)
                q = "\n".join(buf).strip().rstrip(";")
                buf = []
                if not q:
                    continue
                try:
                    show(a.raw(q), args.limit)
                except Exception as e:            # a typo should not kill the session
                    print(f"!! {type(e).__name__}: {e}")
                print()
            else:
                buf.append(line)

    a.close()


if __name__ == "__main__":
    main()
