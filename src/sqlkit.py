"""
sqlkit.py — tiny helper so the .sql files stay the single source of truth.

Each .sql file is split into named blocks:

    -- name: my_block
    SELECT ...;

Blocks can reference each other with {other_block}, which is substituted inline as a
subquery (with the trailing ';' stripped). That lets `05_drivers.sql` define the
first-order feature table once and reuse it in five queries — the same thing you'd do
with a CTE library or a dbt model in production.
"""

import os
import re
import sqlite3
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(HERE, "data", "zomato.db")
SQL_DIR = os.path.join(HERE, "sql")


def load_blocks(*files) -> dict:
    """Parse one or more .sql files into {block_name: sql_text}."""
    blocks = {}
    for f in files:
        path = os.path.join(SQL_DIR, f)
        text = open(path).read()
        parts = re.split(r"^--\s*name:\s*(\w+)\s*$", text, flags=re.M)
        # parts = [preamble, name1, body1, name2, body2, ...]
        for name, body in zip(parts[1::2], parts[2::2]):
            blocks[name] = body.strip()
    return blocks


def resolve(blocks: dict, name: str) -> str:
    """Expand {other_block} references into inline subqueries."""
    sql = blocks[name]
    for _ in range(5):                                  # a few passes handle nesting
        refs = set(re.findall(r"\{(\w+)\}", sql))
        if not refs:
            break
        for r in refs:
            inner = blocks[r]
            # a block ends at its final ';' (anything after it is a trailing comment)
            if ";" in inner:
                inner = inner[: inner.rindex(";")]
            inner = "\n" + inner.strip() + "\n"
            sql = sql.replace("{" + r + "}", inner)
    return sql


class Analytics:
    """Thin wrapper: `a.q('cohort_matrix')` runs that named block and returns a DataFrame."""

    def __init__(self, *files):
        self.con = sqlite3.connect(DB)
        self.blocks = load_blocks(*files)

    def q(self, name: str) -> pd.DataFrame:
        return pd.read_sql_query(resolve(self.blocks, name), self.con)

    def raw(self, sql: str) -> pd.DataFrame:
        return pd.read_sql_query(sql, self.con)

    def close(self):
        self.con.close()


ALL_SQL = ("01_metrics.sql", "02_cohort_retention.sql", "03_funnel.sql",
           "04_segmentation.sql", "05_drivers.sql", "06_ab_test.sql")


def connect() -> Analytics:
    return Analytics(*ALL_SQL)
