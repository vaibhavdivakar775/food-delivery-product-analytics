"""
quiz.py — drill yourself on your own project until you can answer cold.

    python3 src/quiz.py                    # everything, shuffled
    python3 src/quiz.py --topic metrics    # metrics | sql | experiment | project
    python3 src/quiz.py --mock             # 15 questions in real interview order
    python3 src/quiz.py --list             # just read the questions and answers

How it works: you get a question, you answer OUT LOUD (that matters -- writing is easier
than speaking, and the interview is speaking), then press Enter to see a model answer and
score yourself honestly. Questions marked [LIVE] pull the real number from your database,
so the answer can never be stale.
"""

import argparse
import json
import os
import random
import textwrap

from sqlkit import connect, HERE

W = 84
RESULTS = os.path.join(HERE, "reports", "results.json")


def wrap(t, indent=""):
    """Re-flow a triple-quoted answer: collapse the source line breaks, then wrap."""
    paras = [" ".join(line.strip() for line in para.split("\n"))
             for para in t.strip().split("\n\n")]
    return "\n\n".join(textwrap.fill(p, W, initial_indent=indent,
                                     subsequent_indent=indent) for p in paras if p)


def build(R, a):
    """Return a list of (topic, question, answer). Answers interpolate live numbers."""
    H, NS, AB, IMP = R["headline"], R["north_star"], R["ab_stats"], R["impact"]
    ST, LEAK = R["stratified"], R["payment_leak"]
    late = {r["first_delivery"]: r["repeat_30d_pct"] for r in R["repeat_by_late"]}

    Q = []
    add = lambda topic, q, ans: Q.append((topic, q, wrap(ans, "   ")))

    # ---------------------------------------------------------------- project story
    add("project",
        "Walk me through your project in 30 seconds.",
        f"""A food-delivery marketplace where {H['activation_rate_pct']}% of signups place a first order but
        only {NS['repeat_30d_rate_pct']:.0f}% place a second one within 30 days. I found the biggest driver is a late
        first delivery -- worth about {R['raw_gap_pp']:.0f} percentage points of 30-day repeat rate, and it
        survives stratification and shows a dose-response. I also found a broken
        checkout-to-payment step on Android worth ~{int(LEAK['recoverable_orders_6mo']/1000)}k orders in six months. Then I ran an
        experiment on a post-first-order coupon: {AB['abs_lift_pp']:+.1f}pp with a real AOV guardrail cost,
        so I recommended shipping it targeted. Total sizing ~Rs {IMP['total_gmv_lakh_yr']:.0f} lakh a year.""")

    add("project",
        "Why did you pick THIS question instead of something else?",
        """Because acquisition wasn't the constraint -- two-thirds of signups do order. The
        constraint was that they don't come back, and in this business first orders carry
        ~28% discount while repeat orders carry ~9%. So the first order loses money and
        the repeat orders make it back. A user who never returns is a user you paid to
        acquire and never recovered. That makes the second order the business problem,
        not a nice-to-have.""")

    add("project",
        "Did you write all of this yourself?",
        """The honest answer, always: I designed the analysis and the argument, I used AI
        assistance for parts of the implementation, and I understand every line -- happy
        to walk through any query you pick. Never bluff this. A candidate who explains
        their tooling honestly and then explains a CTE correctly is fine. A candidate
        caught bluffing is done.""")

    add("project",
        "What's the weakest part of your project?",
        f"""The lateness impact estimate. It multiplies an assumed 6pp reduction in the late
        rate by an observational {ST['adjusted_gap_pp']:.1f}pp effect by {IMP['orders_per_retained_user_measured']} measured orders per retained
        user -- three numbers, only the last measured. Direction solid, magnitude is a
        planning estimate. Second weakest: Members repeat at 48% but that's mostly
        selection, which is why I kept it out of the recommendations.""")

    # ---------------------------------------------------------------- metrics
    add("metrics",
        "What's your north-star metric, and why not GMV?",
        f"""30-day repeat rate of new users, currently {NS['repeat_30d_rate_pct']:.1f}%. GMV and DAU both rise when you
        spend more on ads -- they measure the marketing budget as much as the product.
        Repeat rate can't be bought that way. It's also the earliest strong LTV signal in
        food delivery, because most churn happens between order 1 and order 2, and it
        reads back in weeks rather than quarters.""")

    add("metrics",
        "Why measure it only on 'matured cohorts'?",
        """Right-censoring. Someone who first ordered five days ago hasn't HAD 30 days to
        come back, so counting them as churned makes the metric fake and drifting. I only
        include users whose first order was at least 30 days before the data cut-off.""")

    add("metrics",
        "Name your guardrail metrics and why they exist.",
        f"""Cancellation rate, average delivery time, average rating, discount as % of GMV,
        and net revenue per order. They exist because almost any single metric can be
        gamed -- give everyone a 50% coupon and repeat rate soars while you lose money on
        every order. In my experiment a guardrail did move: second-order AOV fell Rs {IMP['nudge_aov_delta_rupees']:.0f}.""")

    add("metrics",
        "Reading your cohort heatmap: what does a row tell you vs a column?",
        f"""Across a row: how fast one cohort decays -- mine goes 100% to ~27% to ~18%, so
        almost all the loss is in month 1. Down the M1 column: whether newer cohorts are
        better or worse than older ones -- mine goes 27, 27, 24, 23, 19, so newer cohorts
        are worse. Caveat I'd state: the last cohorts are partly right-censored.""")

    add("metrics",
        "[LIVE] What's your AOV, and is GMV the same as revenue?",
        f"""AOV is Rs {H['aov']:.0f} -- GMV divided by orders. GMV is NOT revenue: the platform keeps a
        take rate, roughly 18-22% in Indian food delivery, and out of that pays the rider,
        the discount and the payment fee. What's left is contribution margin, and it's
        thin. Total GMV here is Rs {H['gmv']/1e7:.2f} Cr.""")

    add("metrics",
        "What's the difference between 12 percentage points and 12 percent?",
        f"""Percentage points is the arithmetic difference between two percentages; percent is
        relative. Late vs on-time repeat is {late['Late']:.1f}% vs {late['On time']:.1f}% -- that's {R['raw_gap_pp']:.1f} percentage
        points, but about a {100*(late['On time']-late['Late'])/late['Late']:.0f}% relative difference. Mixing them up is a tell.""")

    add("metrics",
        "Why is your 'late' threshold 10 minutes and not 0?",
        """Because a two-minute overrun isn't a bad experience, and the data agrees: the
        dose-response curve is flat for the first ten minutes and then falls off a cliff.
        The threshold matches where user behaviour actually changes. If I'd used zero I'd
        have labelled half my on-time users late and diluted the effect.""")

    add("metrics",
        "Your funnel drops 34% at the last step. So what?",
        f"""On its own, not much -- carts get abandoned everywhere. It becomes an insight when
        you segment it: Android converts at {LEAK['android_pay_conv_pct']:.0f}% on that step, iOS at {LEAK['ios_pay_conv_pct']:.0f}%, while every
        earlier step matches within 0.2pp. If Android users were just lower-intent they'd
        abandon earlier too. A gap isolated to one step is a defect signature -- an
        engineering ticket, not a growth experiment. Worth ~{int(LEAK['recoverable_orders_6mo']):,} orders in six months.""")

    add("metrics",
        "What is RFM and what did it tell you?",
        """Recency, frequency, monetary -- score every user 1 to 5 on each with NTILE(5),
        then map combinations to segments a PM can act on. Mine: Champions are ~19% of
        users but ~36% of GMV, so retention spend should be weighted toward them. And
        paid-social users repeat at 21.6% vs 35.5% for referral on the heaviest
        discounts -- we're buying discount-chasers.""")

    # ---------------------------------------------------------------- experimentation
    add("experiment",
        "Explain your A/B test design.",
        f"""Hypothesis: a Rs 75 coupon valid 7 days, sent right after the first delivered
        order, raises the share who order again within 14 days. Randomised at the USER
        level, 50/50. One primary metric: repeat within 14 days. Powered for a 2.0pp MDE
        at 80% power, alpha 0.05, which needed {AB['required_n_per_arm']:,} per arm -- I had {AB['actual_min_n_per_arm']:,}.
        Guardrails: second-order AOV, cancellation rate, coupon cost.""")

    add("experiment",
        "Why randomise at the user level rather than per order?",
        """Because the treatment belongs to a person. If I randomised per order the same user
        could land in both arms, the arms would contaminate each other, and the effect
        would be diluted toward zero. The unit of randomisation has to match how the
        treatment is experienced.""")

    add("experiment",
        "What's a p-value? And what is it NOT?",
        f"""If the treatment truly had no effect, the p-value is the probability of seeing a
        difference at least as large as mine by chance alone. Mine was {AB['p_value_str']}, so chance
        is a poor explanation. It is NOT the probability that the treatment works, and it
        says nothing about whether the effect is big enough to matter -- that's the job of
        the confidence interval, mine being [{AB['ci_low_pp']:.2f}pp, {AB['ci_high_pp']:.2f}pp].""")

    add("experiment",
        "What is SRM and why do you check it before anything else?",
        f"""Sample ratio mismatch -- I designed a 50/50 split, did I actually get one? If not,
        assignment or logging is broken and nothing else in the readout can be trusted,
        however good the lift looks. Mine passed, chi-square p = {R['ab_srm_pvalue']:.2f}. I also check the
        arms are balanced on things decided before assignment, like first-order AOV.""")

    add("experiment",
        f"Your test showed {AB['abs_lift_pp']:+.1f}pp. Would you ship it?",
        f"""Yes -- targeted, with a permanent 10% holdout. Statistics are clean: powered,
        SRM passed, arms balanced, CI excludes zero. But a guardrail moved -- second-order
        AOV fell Rs {IMP['nudge_aov_delta_rupees']:.0f} -- so net value is ~Rs {IMP['nudge_net_gmv_lakh_yr']:.0f}L, not the ~Rs {IMP['nudge_gross_gmv_lakh_yr']:.0f}L the gross lift
        implies. And the effect is WEAKER for users whose first delivery went badly
        (+2.04pp vs +3.61pp), so it buys an order, it doesn't repair the experience. Ship
        it, don't spray it, and don't let it become the strategy.""")

    add("experiment",
        "Your lateness finding is correlational. Convince me.",
        f"""Three things, and I'll say up front it isn't proof. One, stratification: within 69
        like-for-like cells -- same city, channel, membership status, platform -- the gap only
        moves from {R['raw_gap_pp']:.1f}pp to {ST['adjusted_gap_pp']:.1f}pp, so composition explains almost none of it. Two,
        dose-response: flat for ten minutes then a cliff, and confounders rarely produce a
        threshold shape that lines up with the promise the user was given. Three, a
        mechanism. What would settle it is a geo experiment on rider capacity.""")

    add("experiment",
        "What if the coupon just pulls forward an order that would have happened anyway?",
        """Then the 14-day win is an accounting illusion and the 90-day effect is zero. It's
        the main threat to the result and I'd raise it myself. The permanent holdout
        answers it: compare 90-day orders per user rather than the 14-day flag. If the
        curves converge, it's a subsidy, not growth, and I'd turn it off.""")

    add("experiment",
        "How would you design an experiment for the delivery finding?",
        """A geo experiment -- you can't give one user in a city a faster rider fleet, so
        randomising individuals doesn't work. Match cities on volume, late rate and AOV,
        add rider capacity at peak in the treatment cities, hold the others as control,
        and compare new-user 30-day repeat rate over the following month.""")

    add("experiment",
        "The result is significant but the lift is 0.1pp. Ship?",
        """No. Significance says the effect is real, not that it's worth having -- with a big
        enough sample, trivially small effects become significant. I'd weigh it against
        cost and guardrails, and a 0.1pp lift that costs Rs 75 a head is a loss.""")

    # ---------------------------------------------------------------- SQL
    add("sql",
        "What's the difference between WHERE and HAVING?",
        """WHERE filters rows before grouping; HAVING filters groups after aggregation. So
        'orders over Rs 500' is WHERE, but 'cities with more than 10,000 orders' is
        HAVING, because you can't know the count until you've grouped.""")

    add("sql",
        "What's the difference between JOIN and LEFT JOIN, and where does it matter here?",
        f"""Inner JOIN keeps only rows that match in both tables; LEFT JOIN keeps every row
        from the left table with NULLs where there's no match. It matters for my
        activation rate: I need users with NO orders to still appear, so it has to be a
        LEFT JOIN from users. With an inner join I'd get {H['activation_rate_pct']}% replaced by 100% and
        never notice.""")

    add("sql",
        "How do you find each user's FIRST order in SQL?",
        """A CTE with MIN(order_ts) grouped by user_id. If I need properties of that order --
        was it late, how big -- I join back to orders on user_id AND order_ts = first_ts,
        which pins it to that exact row. That 'first event per user, then join back'
        pattern is the backbone of every cohort and retention query I wrote.""")

    add("sql",
        "How would you compute a '% of rows where X' in one pass?",
        """AVG(CASE WHEN condition THEN 1 ELSE 0 END), times 100 for a percentage. The ELSE 0
        is essential -- without it, non-matching rows become NULL, AVG ignores NULLs, and
        you get 100% every time. I hit exactly that bug while building the guardrail
        query.""")

    add("sql",
        "What does NTILE(5) do and where did you use it?",
        """It sorts rows and splits them into 5 equal-sized buckets, numbered 1 to 5. I used
        it for RFM scoring -- NTILE(5) OVER (ORDER BY frequency) gives every user a
        frequency score where 5 is the top 20%. Same for recency and monetary value.""")

    add("sql",
        "What does PARTITION BY do?",
        """It restarts a window function for each group. LAG(sessions) OVER (PARTITION BY
        platform ORDER BY step_no) gives the previous funnel step's count WITHIN that
        platform -- which is exactly how I got the Android-versus-iOS step conversions.""")

    add("sql",
        "You join two tables and the row count goes up. What happened?",
        """The join key isn't unique on one side, so rows fan out and I'm double-counting.
        It's the most common bug in analytics SQL. I check row counts after every join,
        and I state the grain -- 'one row per user per month' -- before writing anything.""")

    add("sql",
        "[LIVE] Write a query for orders and late rate by city.",
        """SELECT city, COUNT(*) AS orders, ROUND(100.0*AVG(is_late),1) AS late_pct
        FROM orders WHERE status='delivered' GROUP BY city ORDER BY late_pct DESC;
        Note the 100.0 rather than 100 -- integer division would silently give zero.""")

    add("sql",
        "How do you compute days between two timestamps here, and month buckets?",
        """JULIANDAY(a) - JULIANDAY(b) gives the number of days, which is how I test 'did
        they order again within 30 days'. STRFTIME('%Y-%m', ts) buckets a timestamp into a
        month for cohorts, and CAST(STRFTIME('%H', ts) AS INT) gives the hour as a number
        so I can compare it with BETWEEN.""")

    return Q


MOCK_ORDER = [
    ("project", "Walk me through your project in 30 seconds."),
    ("project", "Why did you pick THIS question instead of something else?"),
    ("metrics", "What's your north-star metric, and why not GMV?"),
    ("metrics", "Name your guardrail metrics and why they exist."),
    ("metrics", "Why measure it only on 'matured cohorts'?"),
    ("metrics", "Reading your cohort heatmap: what does a row tell you vs a column?"),
    ("metrics", "Your funnel drops 34% at the last step. So what?"),
    ("experiment", "Your lateness finding is correlational. Convince me."),
    ("experiment", "Explain your A/B test design."),
    ("experiment", "What's a p-value? And what is it NOT?"),
    ("experiment", "What is SRM and why do you check it before anything else?"),
    ("sql", "How do you find each user's FIRST order in SQL?"),
    ("sql", "What's the difference between JOIN and LEFT JOIN, and where does it matter here?"),
    ("project", "What's the weakest part of your project?"),
    ("project", "Did you write all of this yourself?"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", choices=["metrics", "sql", "experiment", "project"])
    ap.add_argument("--mock", action="store_true", help="15 questions, interview order")
    ap.add_argument("--list", action="store_true", help="print everything, no prompting")
    args = ap.parse_args()

    R = json.load(open(RESULTS))
    a = connect()
    Q = build(R, a)
    a.close()

    if args.mock:
        by_q = {q: (t, ans) for t, q, ans in Q}
        picked = [(by_q[q][0], q, by_q[q][1]) for _, q in MOCK_ORDER if q in by_q]
        header = "MOCK INTERVIEW — 15 questions, no hints. Answer out loud."
    else:
        picked = [x for x in Q if not args.topic or x[0] == args.topic]
        random.shuffle(picked)
        header = f"DRILL — {len(picked)} questions" + (f" on {args.topic}" if args.topic else "")

    if args.list:
        for t, q, ans in picked:
            print(f"\n[{t}] {q}\n{ans}")
        return

    print("=" * W)
    print(header)
    print("Answer OUT LOUD, then press Enter for the model answer. Ctrl-C to stop.")
    print("=" * W)

    score = {"good": 0, "shaky": 0, "no": 0}
    try:
        for i, (t, q, ans) in enumerate(picked, 1):
            print(f"\n{'-' * W}\nQ{i}/{len(picked)}  [{t}]\n")
            print(wrap(q, "  "))
            input("\n  (answer out loud, then press Enter) ")
            print("\n  MODEL ANSWER:")
            print(ans)
            v = input("\n  How did you do?  [g]ood / [s]haky / [n]o idea > ").strip().lower()
            score["good" if v.startswith("g") else "shaky" if v.startswith("s") else "no"] += 1
    except KeyboardInterrupt:
        print("\n\nstopped early.")

    done = sum(score.values())
    if done:
        print(f"\n{'=' * W}")
        print(f"  answered {done}   good {score['good']}   shaky {score['shaky']}   "
              f"no idea {score['no']}")
        pct = 100 * score["good"] / done
        verdict = ("ready to talk about this project." if pct >= 80 else
                   "nearly there -- re-read the LEARN file for whatever felt shaky."
                   if pct >= 55 else
                   "not yet. Go back to LEARN/00-START-HERE.md and work the day plan.")
        print(f"  {pct:.0f}% solid -> {verdict}")
        print("=" * W)


if __name__ == "__main__":
    main()
