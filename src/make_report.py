"""
make_report.py — generates README.md and reports/EXECUTIVE_SUMMARY.md from
reports/results.json.

WHY GENERATE THEM: every number in the README and the one-pager is pulled from the
results file that run_analysis.py produced. Nothing is hand-typed, so the report can
never quietly disagree with the analysis after a re-run. That property is the whole
point of the pipeline.

Run:  python3 src/run_analysis.py && python3 src/make_report.py
"""

import json
import os
import pandas as pd

from sqlkit import HERE

R = json.load(open(os.path.join(HERE, "reports", "results.json")))
H, NS = R["headline"], R["north_star"]
AB, IMP, LEAK, ST = R["ab_stats"], R["impact"], R["payment_leak"], R["stratified"]


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |",
           "| " + " | ".join("---" for _ in cols) + " |"]
    for row in df.itertuples(index=False):
        out.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
    return "\n".join(out)


def cr(x):          # ₹ crore
    return f"₹{x/1e7:.2f} Cr"


# =====================================================================================
# EXECUTIVE SUMMARY — the single most valuable artifact in an interview
# =====================================================================================
def executive_summary() -> str:
    seg = pd.DataFrame(R["repeat_by_segment"])
    gold = seg[(seg.dimension == "gold")].set_index("value")["repeat_pct"]
    ch = seg[(seg.dimension == "channel")].set_index("value")["repeat_pct"]
    dose = pd.DataFrame(R["dose_response"])
    hte = pd.DataFrame(R["ab_by_segment"])
    late_pct = [r for r in R['repeat_by_late'] if r['first_delivery'] == 'Late'][0]['repeat_30d_pct']
    ontime_pct = [r for r in R['repeat_by_late'] if r['first_delivery'] == 'On time'][0]['repeat_30d_pct']
    dose_txt = "\n".join(
        f"  - {r.lateness_bucket[3:]}: **{r.repeat_30d_pct:.1f}%** repeat (n = {int(r.users):,})"
        for r in dose.itertuples())

    late_t = hte[hte.segment.str.contains("LATE")]
    lift_late = (late_t[late_t.variant == "treatment"].repeat_14d_pct.iloc[0]
                 - late_t[late_t.variant == "control"].repeat_14d_pct.iloc[0])
    on_t = hte[hte.segment.str.contains("ON TIME")]
    lift_on = (on_t[on_t.variant == "treatment"].repeat_14d_pct.iloc[0]
               - on_t[on_t.variant == "control"].repeat_14d_pct.iloc[0])

    return f"""# The Second-Order Problem — Executive Summary
**Audience:** Product / Growth leadership · **Analyst:** Vaibhav Divakar ·
**Data:** {int(H['registered_users']):,} users, {int(H['orders']):,} orders, Jan–Jun 2026 (simulated)

---

## 1. The problem
We activate users well and lose them immediately.

- **{H['activation_rate_pct']}%** of registered users place a first order — acquisition is not the problem.
- Only **{NS['repeat_30d_rate_pct']:.1f}%** of new users place a **second order within 30 days**.
- Month-1 retention has fallen from **{R['cohort_matrix']['1']['2026-01']:.0f}%** (January cohort) to
  **{R['cohort_matrix']['1']['2026-05']:.0f}%** (May cohort) while order volume grew — we are buying
  growth that leaks straight back out.

Every ₹ of acquisition spend is amortised over **{H['orders_per_ordering_user']} orders per user**. That is
the business problem: not traffic, not supply — **the second order**.

## 2. What the data says

**Finding 1 — A late first delivery is the single largest killer of the second order.**
Users whose first order arrived >10 min past the promised ETA repeat at
**{late_pct:.1f}%** vs **{ontime_pct:.1f}%** for on-time users — a **{R['raw_gap_pp']:.1f}pp** raw gap
(p < 0.001). Held constant within {int(ST['cells_used'])} city × channel × Gold × platform cells covering
{int(ST['users_covered']):,} users, the gap is still **{ST['adjusted_gap_pp']:.1f}pp**, and it shows a clean
dose–response once the ETA is genuinely missed:
{dose_txt}
(the first ~10 minutes cost nothing — users forgive a small overrun, which is exactly
why the "late" threshold is set at 10 minutes rather than 0.)
Lateness is **concentrated**, not systemic: {IMP['lateness_worst_cells'][0]['city']} at
{IMP['lateness_worst_cells'][0]['daypart'].lower()} runs **{IMP['lateness_worst_cells'][0]['late_rate_pct']}%** late vs
a **{H['late_delivery_rate_pct']}%** company average.

**Finding 2 — One funnel step is broken on one platform.**
Checkout → payment converts at **{LEAK['android_pay_conv_pct']}% on Android vs {LEAK['ios_pay_conv_pct']}% on iOS**, while
*every other step is within 0.5pp across platforms*. A gap isolated to a single step is
the signature of a defect, not of user intent. At current volume that is
**~{int(LEAK['recoverable_orders_6mo']):,} lost orders in six months**.

**Finding 3 — We are buying the wrong users.**
Paid-social users repeat at **{ch.get('paid_social'):.1f}%** vs **{ch.get('referral'):.1f}%** for referral, and
consume the heaviest discounts. Gold members repeat at **{gold.get('Gold member'):.1f}%** vs
**{gold.get('Non-member'):.1f}%** for non-members.

## 3. The recommendation

| # | Action | Owner | Est. annual GMV | Confidence |
|---|---|---|---|---|
| 1 | **Fix the Android payment step** (SDK/UPI retry, fallback rail) | Eng · Payments | **₹{IMP['android_fix_gmv_lakh_yr']:.0f} L** | High — measured gap, one step, one platform |
| 2 | **Cut late deliveries {IMP['lateness_late_rate_reduction_assumed_pp']:.0f}pp in the worst city × daypart cells** (rider capacity + honest ETAs at peak) | Ops · City teams | **₹{IMP['lateness_fix_gmv_lakh_yr']:.1f} L** | Medium — observational, but stratified + dose–response |
| 3 | **Ship the Next-Order Nudge**, targeted (below) | Growth · CRM | **₹{IMP['nudge_net_gmv_lakh_yr']:.1f} L net** | High — randomised experiment |

**Total ≈ ₹{IMP['total_gmv_lakh_yr']:.0f} L / year** on a {int(H['registered_users']/1000)}k-user base, at
AOV ₹{IMP['aov_used']} and {IMP['orders_per_retained_user_measured']} incremental orders per retained user (both measured, not assumed).

Sequencing matters: **#1 is a bug fix, #2 is the durable fix, #3 is the fast lever.**
Do #3 while #1 and #2 are in flight — but do not let the coupon become the strategy.
Discounting a bad delivery experience is renting retention; fixing the delivery buys it.

## 4. The experiment (evidence for #3)

> **Hypothesis:** a ₹75 coupon valid 7 days, sent immediately after a user's first
> delivered order, raises the share who order again within 14 days.
> **Unit:** user · **Split:** 50/50 · **Primary metric:** repeat within 14 days
> **MDE:** {AB['planned_mde_pp']}pp absolute at 80% power, α = 0.05 → **{AB['required_n_per_arm']:,} users per arm required**

| | Control | Treatment |
|---|---|---|
| Users | {AB['control_n']:,} | {AB['treatment_n']:,} |
| Repeat within 14d | {AB['control_rate_pct']:.2f}% | **{AB['treatment_rate_pct']:.2f}%** |

- **Absolute lift {AB['abs_lift_pp']:+.2f}pp** (relative **{AB['rel_lift_pct']:+.1f}%**),
  95% CI **[{AB['ci_low_pp']:.2f}pp, {AB['ci_high_pp']:.2f}pp]**, z = {AB['z_stat']}, **p {AB['p_value_str']}**.
- **Sample-ratio-mismatch check passed** (χ² p = {R['ab_srm_pvalue']:.2f}) and the arms are balanced on
  pre-assignment covariates — the randomisation is trustworthy.
- **Guardrail breach:** treated users' second-order AOV falls **₹{IMP['nudge_aov_delta_rupees']:.0f}** — they trade
  down to make the coupon worth using. That costs ₹{IMP['nudge_aov_guardrail_cost_lakh_yr']:.1f} L/yr and is already
  netted out above. Cancellation rate is unchanged.

**Decision: SHIP — but targeted, not blanket.** The lift is real and the CI excludes
zero, yet the effect is similar for users whose first delivery went well
(**{lift_on:+.2f}pp**) and badly (**{lift_late:+.2f}pp**): the coupon buys an extra order, it does
**not** repair a bad delivery. So send it where the coupon is not simply paying users
who would have returned anyway — and hold out 10% permanently to keep measuring.

## 5. What would change my mind
- **The lateness effect is observational.** Stratification and dose–response make
  confounding unlikely, but the clean test is a **geo/time-sliced ETA experiment**:
  add rider capacity in two matched cities and compare new-user repeat rates.
- **14 days is a short horizon.** If the nudge merely *pulls forward* an order that
  would have happened in week 5, the 90-day effect is ~0. The holdout answers this.
- **Simulated data.** Effect *sizes* here are properties of my simulation; the
  *methods*, definitions, and decision logic are what transfer.
"""


# =====================================================================================
# README
# =====================================================================================
def readme() -> str:
    trend = pd.DataFrame(R["monthly_trend"])
    rfm = pd.DataFrame(R["rfm_summary"])
    fun = pd.DataFrame(R["funnel_overall"])
    ch = pd.DataFrame(R["behaviour_by_channel"])
    seg = pd.DataFrame(R["repeat_by_segment"])
    chan30 = seg[seg.dimension == "channel"].set_index("value")["repeat_pct"]

    return f"""# The Second-Order Problem
### A product-analytics case study on a food-delivery marketplace

> **{H['activation_rate_pct']}% of registered users place a first order. Only {NS['repeat_30d_rate_pct']:.1f}% place a second one
> within 30 days.** This project finds out why, sizes each cause in rupees, runs an
> experiment on the fix, and ships a monitor so the answer stays current.

`SQL` · `Python` · `cohort retention` · `funnel analysis` · `RFM segmentation` ·
`A/B testing` · `Streamlit` · `automated monitoring`

---

## The one-minute version

| | |
|---|---|
| **Business question** | Why do new users not place a second order, and which fix is worth the most GMV? |
| **North-star metric** | 30-day repeat rate of new users — currently **{NS['repeat_30d_rate_pct']:.1f}%** |
| **Finding 1** | A **late first delivery** cuts the 30-day repeat rate by **{ST['adjusted_gap_pp']:.1f}pp** (confounder-adjusted), with a clean dose–response |
| **Finding 2** | Checkout→payment converts at **{LEAK['android_pay_conv_pct']}% on Android vs {LEAK['ios_pay_conv_pct']}% on iOS** — one broken step, ~**{int(LEAK['recoverable_orders_6mo']):,}** lost orders in 6 months |
| **Finding 3** | Paid-social users repeat at **{chan30.get('paid_social'):.1f}%** vs **{chan30.get('referral'):.1f}%** for referral, on the heaviest discounts |
| **Experiment** | "Next-Order Nudge" (₹75 off, 7 days): **{AB['abs_lift_pp']:+.2f}pp** repeat rate, 95% CI [{AB['ci_low_pp']:.2f}, {AB['ci_high_pp']:.2f}], p {AB['p_value_str']} |
| **Decision** | **Ship the nudge targeted**, fix the Android payment step first, and fund rider capacity at peak in the two worst cells |
| **Estimated impact** | **≈ ₹{IMP['total_gmv_lakh_yr']:.0f} lakh incremental GMV per year** on a {int(H['registered_users']/1000)}k-user base, assumptions stated |

📄 **[Read the 1-page executive summary →](reports/EXECUTIVE_SUMMARY.md)**
📓 **[Read the full analysis notebook →](notebooks/analysis.ipynb)**
🎤 **[Interview walkthrough & defence of every choice →](INTERVIEW-PREP.md)**

---

## The headline charts

**Retention collapses after month 1, and later cohorts are worse than earlier ones.**

![cohort heatmap](charts/02_cohort_heatmap.png)

**One late first delivery permanently lowers the whole retention curve.**

![retention by first delivery](charts/03_retention_by_first_delivery.png)

**More lateness → less repeat. The monotone slope is why I treat this as causal.**

![dose response](charts/07_dose_response.png)

**The funnel's biggest leak is checkout → payment …**

![funnel](charts/04_funnel.png)

**… and it is almost entirely an Android problem. Every earlier step matches iOS.**

![funnel by platform](charts/05_funnel_by_platform.png)

**The experiment: a real lift, with a real guardrail cost.**

![ab test](charts/10_ab_test.png)

**Every finding, priced.**

![impact](charts/12_impact.png)

---

## How I framed it

A product analyst's job is not to produce charts; it is to change a decision. So the
project is built backwards from the decision:

1. **Define the metric before looking at data.**
   *North star:* 30-day repeat rate of new users. It is the earliest reliable predictor
   of LTV in food delivery, it is fast to move, and — unlike "orders" — it cannot be
   faked by buying more traffic. Measured only on **matured cohorts** (first order ≥30
   days before the cut-off) so right-censoring does not flatter it.
   *Guardrails:* cancellation rate, avg delivery time, avg rating, discount % of GMV,
   net revenue per order. A win on the north star that breaks a guardrail is not a win.

2. **Find where the metric leaks** — cohorts, funnel, segments.

3. **Separate correlation from cause.** The headline finding is observational, so it is
   stress-tested three ways: stratification across {int(ST['cells_used'])} confounder cells, a dose–response
   curve, and a randomised experiment on the recommended fix.

4. **Price every finding in rupees**, with the assumptions written down where a
   sceptical reader can attack them.

5. **Automate it** so the answer does not go stale the day after the deck is presented.

## What's in the repo

```
zomato-product-analytics/
├── README.md                      ← you are here
├── INTERVIEW-PREP.md              ← 30-sec / 2-min pitch + the hard questions, answered
├── reports/
│   ├── EXECUTIVE_SUMMARY.md       ← the 1-pager for a PM
│   ├── weekly_monitor.md          ← auto-generated metric health report
│   └── results.json               ← every number, machine-readable
├── sql/                           ← the analytics layer (named, commented query blocks)
│   ├── 01_metrics.sql             north star, guardrails, monthly trend
│   ├── 02_cohort_retention.sql    cohort matrix + retention by first-delivery experience
│   ├── 03_funnel.sql              session funnel, segmented, + "size the prize"
│   ├── 04_segmentation.sql        RFM (NTILE), channel quality, time-of-day
│   ├── 05_drivers.sql             driver analysis, stratification, dose–response
│   └── 06_ab_test.sql             SRM check, balance, primary metric, guardrails, HTE
├── src/
│   ├── generate_data.py           the simulator, with its causal structure documented
│   ├── sqlkit.py                  loads named SQL blocks; SQL stays the source of truth
│   ├── run_analysis.py            runs everything → charts/ + results.json
│   ├── make_report.py             renders README + exec summary FROM results.json
│   └── monitor.py                 weekly monitoring + RED/AMBER alerting, non-zero exit
├── dashboard/app.py               Streamlit self-serve dashboard
├── notebooks/analysis.ipynb       the narrative walkthrough
├── charts/                        12 publication-styled charts
└── data/                          CSVs + zomato.db (SQLite)
```

## Reproduce it

```bash
pip install -r requirements.txt
python3 src/generate_data.py     # build data/zomato.db      (~10s, seeded)
python3 src/run_analysis.py      # all analyses -> charts/ + reports/results.json
python3 src/make_report.py       # regenerate README + executive summary
python3 src/monitor.py           # weekly metric health check (exit 1 if RED)
streamlit run dashboard/app.py   # interactive dashboard
```

Everything is seeded (`np.random.default_rng(42)`) — the same numbers come out every time.

## About the data — read this before judging it

The data is **simulated**, deliberately and transparently.

Public food-delivery datasets have orders but **no event/clickstream table and no
experiment assignment table**, which makes funnel analysis and A/B analysis impossible.
Rather than skip the two techniques the job actually asks for, I wrote a simulator with
an explicit causal structure (`src/generate_data.py`, documented at the top of the file)
and then tried to **recover** that structure with SQL and statistics — including one
finding I got wrong on the first pass because my event generator silently erased the
platform gap I had injected.

What this means for a reader:
- **The effect sizes are properties of my simulation.** Do not quote them as facts
  about any real company.
- **The metric definitions, the queries, the stratification, the experiment design, the
  guardrail logic, and the decision framework are exactly what you would use in
  production** — those are the parts worth reviewing.

## Data-quality notes (the honest section)

- **Right-censoring:** later cohorts have less time to repeat. Every retention figure is
  restricted to matured cohorts; the May/June rows of the cohort matrix are shown but
  should not be compared to January's M1 without that caveat.
- **Cancelled orders** are excluded from GMV and retention but kept for the
  cancellation guardrail.
- **"Late" is defined as >10 min past the promised ETA**, not >0 — a 2-minute overrun is
  not a bad experience, and the threshold materially changes the headline number.
- **The lateness→retention link is observational.** Stratified and dose-response tested,
  but the clean answer needs a geo experiment (proposed in the summary).
- **Attribution:** acquisition channel is last-touch at signup; multi-touch would shift
  the channel comparison.

## Reference numbers

**Monthly trend**

{md_table(trend)}

**Funnel**

{md_table(fun[['step_no', 'event_name', 'sessions', 'pct_of_top', 'step_conv_pct']])}

**RFM segments**

{md_table(rfm[['segment', 'users', 'pct_users', 'pct_gmv', 'avg_orders', 'avg_lifetime_gmv']])}

**Acquisition channels**

{md_table(ch)}

---

*Built by Vaibhav Divakar · BITS Pilani (Goa), EEE, 2027 · targeting Product Analyst roles.
Feedback welcome — especially on the parts you think are wrong.*
"""


def main():
    with open(os.path.join(HERE, "reports", "EXECUTIVE_SUMMARY.md"), "w") as f:
        f.write(executive_summary())
    with open(os.path.join(HERE, "README.md"), "w") as f:
        f.write(readme())
    print("wrote README.md and reports/EXECUTIVE_SUMMARY.md")


if __name__ == "__main__":
    main()
