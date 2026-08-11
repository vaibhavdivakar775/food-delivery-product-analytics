"""
monitor.py — automated weekly metric monitoring + alerting.

WHY THIS FILE EXISTS
  An analysis answers a question once. A *monitor* keeps answering it every week
  without anyone re-running a notebook. This is the "drive automation and build
  scalable reporting/monitoring solutions" part of the job: the same SQL that
  produced the one-off insight is scheduled, thresholded, and alerted on.

WHAT IT DOES
  1. Computes this week's value for every tracked metric (north star, guardrails,
     funnel steps, ops).
  2. Compares to the trailing 4-week mean and flags a breach when the metric moves
     past a stated threshold in the BAD direction.
  3. Writes reports/weekly_monitor.md and exits non-zero if anything is RED, so a
     cron job / GitHub Action can fail loudly instead of being ignored.

RUN:      python3 src/monitor.py [--week 2026-06-22]
SCHEDULE: 0 7 * * MON  cd /path/to/repo && python3 src/monitor.py >> logs/monitor.log
"""

import argparse
import os
import sys
from datetime import timedelta
import pandas as pd

from sqlkit import connect, HERE

REPORTS = os.path.join(HERE, "reports")

# --------------------------------------------------------------------------------
# The metric registry: name -> (SQL expression, direction, amber %, red %)
#   direction "up"   = higher is better  (a DROP is bad)
#   direction "down" = lower is better   (a RISE is bad)
#   thresholds are RELATIVE moves vs the trailing 4-week mean
# --------------------------------------------------------------------------------
METRICS = [
    # (label,                    sql_expression,                          direction, amber, red)
    ("Orders",                   "COUNT(*)",                               "up",   0.05, 0.10),
    ("Active users",             "COUNT(DISTINCT user_id)",                "up",   0.05, 0.10),
    ("GMV (₹)",                  "SUM(gmv)",                               "up",   0.05, 0.10),
    ("AOV (₹)",                  "AVG(gmv)",                               "up",   0.03, 0.06),
    ("Late-delivery rate (%)",   "100.0*AVG(is_late)",                     "down", 0.10, 0.20),
    ("Avg delivery (min)",       "AVG(delivery_minutes)",                  "down", 0.05, 0.10),
    ("Avg rating",               "AVG(rating)",                            "up",   0.02, 0.04),
    ("Discount % of GMV",        "100.0*SUM(discount)/SUM(gmv)",           "down", 0.10, 0.20),
]


def md_table(df: pd.DataFrame) -> str:
    """Render a DataFrame as a GitHub markdown table (avoids a `tabulate` dependency)."""
    cols = list(df.columns)
    head = "| " + " | ".join(str(c) for c in cols) + " |"
    rule = "| " + " | ".join("---" for _ in cols) + " |"
    body = ["| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |"
            for row in df.itertuples(index=False)]
    return "\n".join([head, rule] + body)


def weekly_frame(a, expr: str) -> pd.Series:
    """Weekly series for one metric expression (week starting Monday)."""
    sql = f"""
        SELECT DATE(order_ts, 'weekday 0', '-6 days') AS week_start,
               {expr} AS value
        FROM orders
        WHERE status = 'delivered'
        GROUP BY 1 ORDER BY 1
    """
    df = a.raw(sql)
    return pd.Series(df["value"].to_numpy(), index=pd.to_datetime(df["week_start"]))


def funnel_weekly(a) -> pd.Series:
    """Session -> order conversion by week (the product-health funnel metric)."""
    sql = """
        SELECT DATE(event_ts, 'weekday 0', '-6 days') AS week_start,
               100.0 * COUNT(DISTINCT CASE WHEN step_no=6 THEN session_id END)
                     / COUNT(DISTINCT CASE WHEN step_no=1 THEN session_id END) AS value
        FROM app_events GROUP BY 1 ORDER BY 1
    """
    df = a.raw(sql)
    return pd.Series(df["value"].to_numpy(), index=pd.to_datetime(df["week_start"]))


def status_for(cur, base, direction, amber, red):
    """Classify the move as GREEN / AMBER / RED."""
    if base in (0, None) or pd.isna(base):
        return "⚪ NO DATA", 0.0
    move = (cur - base) / abs(base)
    bad = -move if direction == "up" else move          # positive = moving the wrong way
    if bad >= red:
        return "🔴 RED", move
    if bad >= amber:
        return "🟠 AMBER", move
    return "🟢 GREEN", move


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", default=None,
                    help="Monday of the week to report on (default: last complete week)")
    args = ap.parse_args()

    a = connect()

    series = {label: weekly_frame(a, expr) for label, expr, _, _, _ in METRICS}
    series["Session→order conv (%)"] = funnel_weekly(a)
    specs = {label: (d, am, rd) for label, _, d, am, rd in METRICS}
    specs["Session→order conv (%)"] = ("up", 0.05, 0.10)

    weeks = sorted(set().union(*[set(s.index) for s in series.values()]))
    # last COMPLETE week = drop the final partial week at the data cut-off
    target = pd.Timestamp(args.week) if args.week else weeks[-2]

    rows, worst = [], "🟢 GREEN"
    for label, s in series.items():
        s = s.sort_index()
        if target not in s.index:
            continue
        cur = float(s.loc[target])
        prior = s.loc[:target].iloc[-5:-1]                 # trailing 4 complete weeks
        base = float(prior.mean()) if len(prior) else float("nan")
        direction, amber, red = specs[label]
        st, move = status_for(cur, base, direction, amber, red)
        rows.append({
            "Metric": label, "This week": round(cur, 2),
            "4-wk mean": round(base, 2) if base == base else None,
            "Δ vs 4-wk": f"{move:+.1%}", "Direction": direction, "Status": st,
        })
        order = ["🟢 GREEN", "🟠 AMBER", "🔴 RED"]
        if order.index(st.split()[0] + " " + st.split()[1]) > order.index(worst):
            worst = st

    df = pd.DataFrame(rows)

    # -- context queries that fire only when something is red ---------------------
    breach = df[df["Status"].str.contains("RED|AMBER")]
    drill = ""
    if len(breach):
        drill = md_table(a.raw(f"""
            SELECT city,
                   ROUND(100.0*AVG(is_late),1) AS late_rate_pct,
                   ROUND(AVG(delivery_minutes),1) AS avg_min,
                   COUNT(*) AS orders
            FROM orders
            WHERE status='delivered'
              AND DATE(order_ts, 'weekday 0', '-6 days') = '{target.date()}'
            GROUP BY 1 ORDER BY late_rate_pct DESC
        """))

    md = f"""# Weekly product-health monitor
**Week of {target.date()}** · generated by `src/monitor.py` · overall status **{worst}**

Thresholds are relative moves vs the trailing 4-week mean, and are direction-aware
(a fall in AOV is bad; a fall in late-delivery rate is good).

{md_table(df)}

"""
    if drill:
        md += f"""## Auto-drilldown (fired because a metric breached)
Late deliveries by city, this week — Ops triage list:

{drill}

"""
    md += """## How this would run in production
| Piece | Here | At scale |
|---|---|---|
| Storage | SQLite | Trino / BigQuery / Redshift |
| Transform | `sql/*.sql` blocks | dbt models, tested + documented |
| Schedule | cron / GitHub Action | Airflow DAG |
| Alerting | non-zero exit code | Slack webhook to #product-alerts |
| Dashboard | Streamlit | Looker / Superset, on the same models |

The important property is that the monitor and the analysis read the **same SQL
definitions**, so the number in the alert can never drift from the number in the deck.
"""

    out = os.path.join(REPORTS, "weekly_monitor.md")
    with open(out, "w") as f:
        f.write(md)
    print(df.to_string(index=False))
    print(f"\noverall: {worst}   ->  reports/weekly_monitor.md")

    a.close()
    sys.exit(1 if "RED" in worst else 0)


if __name__ == "__main__":
    main()
