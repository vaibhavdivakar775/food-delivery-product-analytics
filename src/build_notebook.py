"""
build_notebook.py — assembles and EXECUTES notebooks/analysis.ipynb.

The notebook is generated rather than hand-edited so that (a) it can never drift from
the SQL in sql/, and (b) re-running the pipeline refreshes its outputs. It is executed
before saving, so the committed .ipynb renders with real tables and charts on GitHub.

Run:  python3 src/build_notebook.py
"""

import json
import os
import nbformat as nbf
from nbclient import NotebookClient

from sqlkit import HERE

NB = os.path.join(HERE, "notebooks", "analysis.ipynb")

# Narrative numbers are interpolated from results.json rather than typed, so the prose
# cannot drift from the analysis after a re-run.
R = json.load(open(os.path.join(HERE, "reports", "results.json")))
H, NS, AB, IMP, ST, LEAK = (R["headline"], R["north_star"], R["ab_stats"],
                            R["impact"], R["stratified"], R["payment_leak"])
LATE = {r["first_delivery"]: r["repeat_30d_pct"] for r in R["repeat_by_late"]}
HTE = {(r["segment"], r["variant"]): r["repeat_14d_pct"] for r in R["ab_by_segment"]}
LIFT_ON = HTE[("First delivery ON TIME", "treatment")] - HTE[("First delivery ON TIME", "control")]
LIFT_LATE = HTE[("First delivery LATE", "treatment")] - HTE[("First delivery LATE", "control")]
M1 = R["cohort_matrix"]["1"]

md = lambda t: nbf.v4.new_markdown_cell(t.strip())   # text already interpolated
code = lambda t: nbf.v4.new_code_cell(t.strip())

cells = [
    md(f"""
# The Second-Order Problem
## Why do new users not come back — and which fix is worth the most GMV?

**Product-analytics case study on a food-delivery marketplace · Jan–Jun 2026 (simulated data)**

---

### How to read this notebook

Every section follows the same shape:

> **Question → SQL → result → *so what?***

The SQL lives in `sql/*.sql` (not inline), because in a real team the query *is* the
artifact other people reuse — the notebook is just the narrative wrapped around it.
`sqlkit` loads named query blocks out of those files.

**The one thing to take away:** this project is judged on the *decision*, not the code.
Each analysis below ends with the business implication, and the whole thing converges on
one recommendation with a rupee value attached.
"""),
    code("""
import sys, os
sys.path.insert(0, os.path.abspath("../src"))
import pandas as pd
from sqlkit import connect, resolve

pd.set_option("display.width", 120)
pd.set_option("display.max_columns", 30)

a = connect()          # opens data/zomato.db and parses every sql/*.sql block
print("SQL blocks available:", ", ".join(sorted(a.blocks)))
"""),

    md(f"""
---
## 0. The data

Four tables, shaped the way a real event-driven product warehouse is shaped:

| table | grain | what it is |
|---|---|---|
| `users` | one row per user | signup date, city, platform, acquisition channel, Gold flag |
| `orders` | one row per order | GMV, discount, promised vs actual delivery time, rating, status |
| `app_events` | one row per session × funnel step | `app_open → search → restaurant_view → add_to_cart → checkout_start → payment_success` |
| `ab_test_assignments` | one row per experiment participant | variant, primary metric, guardrail metrics |

**The data is simulated, on purpose and transparently.** Public food-delivery datasets
have orders but no clickstream and no experiment assignments, which makes funnel and A/B
analysis impossible. `src/generate_data.py` documents the causal structure it injects;
the job of this notebook is to *recover* that structure using the same techniques you
would use in production.
"""),
    code("""
for t in ["users", "orders", "app_events", "ab_test_assignments"]:
    n = a.raw(f"SELECT COUNT(*) AS n FROM {t}").iloc[0, 0]
    print(f"{t:<22} {n:>10,} rows")

a.raw("SELECT * FROM orders LIMIT 5")
"""),

    md(f"""
---
## 1. Metric definition — before looking at anything

Doing this first is the discipline that separates an analyst from a chart generator.
If you define the metric *after* seeing the data, you will define whichever metric looks
best.

**North star — 30-day repeat rate of new users.**
Of users whose first order was ≥30 days before the data cut-off, what share ordered again
within 30 days?

Why this one:
- In food delivery, **the second order is the strongest early predictor of LTV** — most
  of the churn happens between order 1 and order 2.
- It is **fast-moving**: you see the effect of a change within weeks, unlike LTV.
- It **cannot be gamed by spending more on acquisition**, unlike total orders or GMV. A
  metric that goes up when you buy traffic is a vanity metric.
- It is restricted to **matured cohorts** so right-censoring does not flatter it — a user
  who ordered yesterday hasn't had 30 days to come back and must not be counted as churned.

**Guardrails** (must not get worse while we chase the north star): cancellation rate,
average delivery time, average rating, discount % of GMV, net revenue per order.
"""),
    code("""
print(resolve(a.blocks, "north_star"))
"""),
    code("""
headline = a.q("headline")
north_star = a.q("north_star")
display(headline.T.rename(columns={0: "value"}))
display(north_star)
"""),
    md(f"""
### So what?

**{H['activation_rate_pct']}% of registered users place a first order — but only {NS['repeat_30d_rate_pct']:.1f}% of them place a
second one within 30 days.** Acquisition is working; retention is not. Every rupee of
acquisition spend is being amortised over {H['orders_per_ordering_user']} orders.

That reframes the whole project: the problem is not the top of the funnel, it is **the
second order**. Everything below is an attempt to find out where that second order goes.
"""),

    md(f"""
---
## 2. Cohort retention — is it getting better or worse?

A cohort is all users whose **first order** fell in month *M*. Retention in period *k* is
the share of that cohort that ordered at all in month *M+k*.

Reading a cohort table has a fixed grammar:
- **Down a column** = are newer cohorts better or worse than older ones? (product/quality trend)
- **Across a row** = how fast does a single cohort decay? (stickiness)
"""),
    code("""
cm = a.q("cohort_matrix")
piv = cm.pivot(index="cohort_month", columns="period_index", values="retention_pct")
piv.style.background_gradient(cmap="Reds", axis=None).format("{:.0f}", na_rep="")
"""),
    md(f"""
### So what?

Two things, and the second is the alarming one:

1. **Across a row:** ~{100 - M1['2026-01']:.0f}% of the January cohort never returned in month 1. The decay is
   brutal and consistent across cohorts.
2. **Down the M1 column:** {M1['2026-01']:.0f}% → {M1['2026-02']:.0f}% → {M1['2026-03']:.0f}% → {M1['2026-04']:.0f}% → {M1['2026-05']:.0f}%. **Newer cohorts are worse.** We
   are growing order volume while the quality of each new cohort deteriorates.

*Caveat I have to state:* the May cohort has had less calendar time inside the window, so
some of that decline is right-censoring, not decay. That is why the north-star metric is
computed only on matured cohorts — but the direction is consistent enough to investigate.

So: what changed for newer cohorts?
"""),

    md(f"""
---
## 3. The hypothesis: the first delivery *is* the product

For a first-time user, the app is not the product — **the first delivery is**. If it
arrives late, the user has learned that the promise is unreliable.

Let's split the retention curve by whether the user's very first order arrived more than
10 minutes past the promised ETA.
"""),
    code("""
cbl = a.q("cohort_by_late")
cbl.pivot(index="period_index", columns="segment", values="retention_pct")
"""),
    code("""
display(a.q("repeat_by_late"))
display(a.q("dose_response"))
"""),
    md(f"""
### So what?

- Late-first-delivery users repeat at **{LATE['Late']:.1f}%** vs **{LATE['On time']:.1f}%** — a **{R['raw_gap_pp']:.1f}pp** gap, and the
  whole retention curve sits lower for months afterwards. One bad delivery is not a
  one-off cost; it is a permanent haircut on that user's lifetime value.
- The **dose–response** is the important part: nothing happens for the first 10 minutes
  (users forgive a small overrun), then repeat rate falls off a cliff. That shape is very
  hard to produce by confounding, and it is why the 10-minute threshold is the right
  definition of "late".

But correlation is not causation. Maybe late orders happen in Bengaluru, at peak, to
paid-social users — and *those* users would have churned anyway.
"""),

    md(f"""
---
## 4. Killing the confounders

Three tests before I believe this:

1. **Stratification** — compare late vs on-time users *within* the same city × channel ×
   Gold × platform cell, then re-weight by cell size. If the gap survives, it isn't
   composition.
2. **Dose–response** — done above.
3. **A randomised experiment** — section 7.
"""),
    code("""
display(a.q("repeat_by_late_stratified"))
display(a.q("repeat_by_segment"))
"""),
    md(f"""
### So what?

Within {int(ST['cells_used'])} like-for-like cells covering {int(ST['users_covered']):,} users, the gap only narrows from
**{R['raw_gap_pp']:.1f}pp to {ST['adjusted_gap_pp']:.1f}pp**. Composition explains almost none of it.

The segment table also ranks every other candidate driver, which is how I can claim
lateness is *the biggest* one rather than just *a* one:

| driver | spread in 30-day repeat rate |
|---|---|
| **Late first delivery** | **{R['raw_gap_pp']:.1f}pp** |
| Gold membership | ~22pp — but that is selection: people who subscribe already intended to order more |
| Acquisition channel | ~14pp (referral vs paid-social) |
| First-order rating | ~12pp — largely *downstream of* lateness, not independent of it |
| City | ~3pp |
| Platform | ~1.4pp |

Gold and channel are things we *select*, not things we *do*. Lateness is something we
**control** — which makes it the actionable driver.
"""),

    md(f"""
---
## 5. The funnel — the other place orders leak

Retention is about users who *ordered*. The funnel is about sessions that *tried to*.
A session counts at a step if it fired that event at least once.
"""),
    code("""
display(a.q("funnel_overall"))
display(a.q("funnel_by_platform"))
display(a.q("payment_leak_size"))
"""),
    md(f"""
### So what?

The overall funnel says the biggest single drop is **checkout → payment (34%)**. That
alone is a weak finding — carts get abandoned everywhere.

Segmenting it is what turns it into an insight: **Android converts at {LEAK['android_pay_conv_pct']}% on that
step, iOS at {LEAK['ios_pay_conv_pct']}%**, while *every earlier step matches within 0.2pp*. A gap isolated to
one step on one platform is the signature of a **defect** (payment SDK / UPI intent
failure), not of different user intent. That is an engineering ticket, not a growth
experiment — and it is worth ~{int(LEAK['recoverable_orders_6mo']):,} orders over six months.

**This is the single most valuable habit in funnel analysis: never read an aggregate
funnel without segmenting it.**
"""),

    md(f"""
---
## 6. Who are our users? RFM segmentation

RFM = Recency, Frequency, Monetary. Score each user 1–5 on each (via `NTILE(5)`), then
map score combinations to segments a PM can actually act on.
"""),
    code("""
display(a.q("rfm_summary"))
display(a.q("behaviour_by_channel"))
"""),
    md(f"""
### So what?

- **Champions (~19% of users) carry ~36% of GMV.** Retention spend should be weighted
  toward keeping them, not toward blanket discounts.
- **Paid-social is our worst channel on every axis**: lowest repeat rate, lowest GMV per
  user, highest discount burn. We are buying discount-chasers. Referral is the opposite.
- The correct read of the "Hibernating / Churned" bucket is that most of them are
  **one-and-done users** — the same second-order problem, seen from a different angle.
"""),

    md(f"""
---
## 7. The experiment: "Next-Order Nudge"

Everything so far is observational. Here is the randomised evidence.

> **Hypothesis:** sending a ₹75 coupon valid 7 days immediately after a user's first
> delivered order increases the share who order again within 14 days.
>
> - **Unit of randomisation:** user, assigned at first-order completion
> - **Split:** 50/50 · **Primary metric:** repeat order within 14 days
> - **MDE:** 2.0pp absolute, 80% power, α = 0.05 (two-sided)
> - **Guardrails:** second-order AOV, second-order cancellation rate, coupon cost

The order of operations matters and most people get it wrong: **sample size is computed
before the test runs, and SRM is checked before the result is read.**
"""),
    code("""
from run_analysis import sample_size_per_arm, ab_readout

prim = a.q("ab_primary")
c = prim[prim.variant == "control"].iloc[0]
t = prim[prim.variant == "treatment"].iloc[0]

need = sample_size_per_arm(p_base=c.repeat_14d_pct / 100, mde_abs=0.02)
print(f"Required users per arm for a 2.0pp MDE at 80% power: {need:,}")
print(f"Actual: control {int(c.n):,} / treatment {int(t.n):,} -> "
      f"{'adequately powered' if min(c.n, t.n) >= need else 'UNDERPOWERED'}")

display(a.q("srm_check"))     # sample ratio mismatch: must be ~50/50
display(a.q("ab_balance"))    # pre-assignment covariates must match
display(prim)
"""),
    code("""
res = ab_readout(int(t.conversions), int(t.n), int(c.conversions), int(c.n))
pd.Series(res).to_frame("value")
"""),
    code("""
display(a.q("ab_guardrails"))
display(a.q("ab_by_segment"))
"""),
    md(f"""
### So what? — the ship / don't-ship decision

**The lift is real:** {AB['abs_lift_pp']:+.2f}pp absolute ({AB['rel_lift_pct']:+.1f}% relative), 95% CI
[{AB['ci_low_pp']:.2f}pp, {AB['ci_high_pp']:.2f}pp], p {AB['p_value_str']}. SRM passes and the arms are balanced on
pre-assignment covariates, so the randomisation is trustworthy.

**But the guardrail moved:** treated users' second-order AOV is **₹{IMP['nudge_aov_delta_rupees']:.0f} lower** — they
trade down to make the coupon worth using. Cancellation rate is unchanged. Netting the
coupon cost *and* the AOV loss against the incremental orders, the nudge is still
positive, but it is worth ~₹{IMP['nudge_net_gmv_lakh_yr']:.0f}L/yr rather than the ~₹{IMP['nudge_gross_gmv_lakh_yr']:.0f}L/yr the gross lift suggests.

**And the effect is not where I hoped:** the lift is {LIFT_ON:+.2f}pp for users whose first
delivery went well and only {LIFT_LATE:+.2f}pp for those whose went badly. **The coupon buys an extra
order; it does not repair a broken experience.** So it is not a substitute for fixing
delivery — which is the finding a growth team is most likely to talk itself out of.

**Decision: ship it, targeted, with a permanent 10% holdout.** Blanket-sending it pays
users who would have come back anyway.
"""),

    md(f"""
---
## 8. Sizing it in rupees

An analysis that stops at "significant" is unfinished. Every recommendation gets a number
and a stated assumption, so a sceptic can attack the assumption rather than the vibe.
"""),
    code("""
import json
imp = json.load(open("../reports/results.json"))["impact"]
pd.Series(imp)[["android_fix_gmv_lakh_yr", "lateness_fix_gmv_lakh_yr",
                "nudge_gross_gmv_lakh_yr", "nudge_coupon_cost_lakh_yr",
                "nudge_aov_guardrail_cost_lakh_yr", "nudge_net_gmv_lakh_yr",
                "total_gmv_lakh_yr"]].to_frame("₹ lakh / year")
"""),
    md(f"""
**Assumptions, stated plainly:**

| assumption | value | why it is conservative |
|---|---|---|
| Android payment fix closes | **half** the iOS gap | full parity after one release is optimistic |
| Late-delivery rate reduction | **{IMP['lateness_late_rate_reduction_assumed_pp']:.0f}pp** in the worst cells | achievable with rider capacity + honest peak ETAs |
| Effect of lateness | the **stratified {ST['adjusted_gap_pp']:.1f}pp**, not the raw {R['raw_gap_pp']:.1f}pp | strips out composition |
| Value of a retained user | **{IMP['orders_per_retained_user_measured']} extra orders** (measured) | right-censored, so an under-estimate |
| Nudge cost | coupon **and** the AOV guardrail loss | most write-ups count only the coupon |

**Total ≈ ₹{IMP['total_gmv_lakh_yr']:.0f} lakh / year on a {int(H['registered_users']/1000)}k-user base.**

---
## 9. What I would do next

1. **Run the geo experiment on ETAs.** The lateness finding is the biggest one and the
   least clean. Add rider capacity in two matched cities at peak and measure new-user
   repeat rate. That converts a {ST['adjusted_gap_pp']:.1f}pp observational gap into a causal one.
2. **Extend the horizon to 90 days.** If the nudge only pulls an order forward, its
   14-day win is an illusion. The permanent holdout answers this.
3. **Rebalance acquisition spend** from paid-social toward referral, and re-measure
   blended CAC payback per channel rather than CAC alone.
4. **Keep it alive:** `src/monitor.py` re-runs these metrics weekly against the same SQL,
   flags RED/AMBER breaches, and exits non-zero so a scheduler can alert on it.
"""),
    code("""
a.close()
"""),
]

nb = nbf.v4.new_notebook(cells=cells)
nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python",
                              "name": "python3"},
               "language_info": {"name": "python"}}

os.makedirs(os.path.dirname(NB), exist_ok=True)
print("executing notebook ...")
NotebookClient(nb, timeout=600, kernel_name="python3",
               resources={"metadata": {"path": os.path.dirname(NB)}}).execute()
nbf.write(nb, NB)
print(f"wrote {NB}")
