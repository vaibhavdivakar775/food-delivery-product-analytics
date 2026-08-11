# Learn this project in 5 days

You have a project on your resume that you did not write from scratch. That is fine —
**every analyst inherits work.** What is not fine is being unable to defend it. This
folder exists to close that gap.

---

## The honest framing

There are **two different things** an interviewer can test, and they need different prep:

| | What it is | Can you get there in 5 days? |
|---|---|---|
| **1. Defending the project** | "Walk me through your analysis. Why that metric? Is it causal? Would you ship it?" | **Yes.** This is about reasoning, not syntax. Days 1–5 below. |
| **2. Writing SQL live** | "Here are two tables. Write a query for 30-day retention." | **Not fully.** You can get to *competent on the basics*. Start the SQL track today and keep it running for 3–4 weeks. |

Do not let anyone (including yourself) pretend #2 is a 5-day job. It is a
muscle. But #1 is where a resume screen and the first interview are decided, and #1 is
absolutely reachable in five days.

**If an interviewer asks "did you write all of this yourself?", the answer is the true
one:** you designed the analysis and the argument, you used AI assistance for parts of
the implementation, and you understand every line — which you then prove by explaining
one. That answer is respected. A bluff that collapses under one follow-up is not.

---

## The rule that makes this work

> **Never put a claim on your resume you cannot explain in three sentences to a
> non-technical person.**

Every bullet on your resume maps to one section of this folder. If you can teach the
section, you can defend the bullet. That's the whole system.

---

## The 5-day plan

Roughly 3 hours a day. Do them in order — each day depends on the one before.

### Day 1 — The story and the business (3 hrs)
The goal today is that you can tell the story *without any numbers* and it still makes
sense. Business logic first, data second.

1. Read [`02-product-metrics.md`](02-product-metrics.md) sections 1–3 (~45 min).
   This teaches: north-star metric, guardrail metric, activation, retention, churn, AOV,
   GMV, and how a food-delivery business actually makes money.
2. Read [`reports/EXECUTIVE_SUMMARY.md`](../reports/EXECUTIVE_SUMMARY.md) twice (~20 min).
3. Say the **30-second pitch** from [`INTERVIEW-PREP.md`](../INTERVIEW-PREP.md) out loud
   five times. Not read — *said*, from memory, to a wall. It will feel stupid. Do it.
4. **Self-test:** explain to a friend (or to your phone's voice recorder) why
   *"first orders lose money and repeat orders make money"* — in your own words, no notes.
   If you can't, re-read section 3 of `02-product-metrics.md`.

### Day 2 — Retention and cohorts (3 hrs)
1. Read [`02-product-metrics.md`](02-product-metrics.md) sections 4–5: cohorts, retention
   curves, right-censoring.
2. Open the cohort heatmap (`charts/02_cohort_heatmap.png`). Practise reading it out
   loud: *"down a column tells me X, across a row tells me Y."*
3. Read [`01-sql-from-zero.md`](01-sql-from-zero.md) **parts 1–4** and type out every
   query yourself. Do not copy-paste. Typing is how the syntax sticks.
4. **Self-test:** run `python3 src/quiz.py --topic metrics` and score yourself.

### Day 3 — Funnel, segments, and the SQL behind them (3 hrs)
1. Read [`02-product-metrics.md`](02-product-metrics.md) sections 6–7: funnels, RFM.
2. Read [`01-sql-from-zero.md`](01-sql-from-zero.md) **parts 5–7** (JOINs, CTEs, window
   functions). Type every query.
3. Open `sql/03_funnel.sql` and read it top to bottom. You have now seen every construct
   in it. Anything you can't read, look it up in part 8 (the cheat sheet).
4. **Self-test:** `python3 src/quiz.py --topic sql`.

### Day 4 — Causation and the experiment (3 hrs)
This is the day that separates you from other candidates. Most people can describe a
funnel. Very few can defend a causal claim or read an A/B test properly.

1. Read [`03-experimentation.md`](03-experimentation.md) in full. It covers: correlation
   vs causation, confounders, stratification, dose–response, hypothesis, randomisation,
   MDE and power, p-value, confidence interval, SRM, guardrails, heterogeneous effects.
2. Re-read `INTERVIEW-PREP.md` — specifically the four questions about causality and the
   A/B test. Say each answer out loud.
3. **Self-test:** `python3 src/quiz.py --topic experiment`.

### Day 5 — Assembly and dress rehearsal (3 hrs)
1. Run the whole pipeline yourself, watching the output: `./run_all.sh`.
2. Open the dashboard: `streamlit run dashboard/app.py`. Click every tab.
3. Do the **full mock**: `python3 src/quiz.py --mock`. It asks 15 questions in interview
   order, no hints. Anything you fumble, go back to that section.
4. Say the **2-minute version** out loud three times, then record yourself once and
   listen back. You'll hear the parts you don't believe yet — those are the parts to
   re-read.

---

## The parallel track: actually writing SQL

Start on Day 2 and keep going after the 5 days are up. 30–45 minutes a day.

1. Finish [`01-sql-from-zero.md`](01-sql-from-zero.md), including the **exercises** at the
   end of each part. They run against *your own database*, so the answers are real.
2. Then do **[sqlbolt.com](https://sqlbolt.com)** (free, ~3 hours total, browser-based) —
   it drills the basics faster than anything else.
3. Then **[stratascratch.com](https://stratascratch.com)** or **LeetCode Database**
   (easy → medium). Target: 3 problems a day. Aim for ~40 problems before an on-site.
4. The five patterns that cover most PA interview SQL questions — you should be able to
   write all five from memory:
   - group-and-aggregate with a filter (`GROUP BY` + `HAVING`)
   - join two tables and aggregate
   - "first event per user" (a `MIN(timestamp)` CTE, then join back)
   - month-over-month or period-over-period (`LAG` window function)
   - rank / top-N per group (`ROW_NUMBER()` or `NTILE`)

**Every one of those five appears in `sql/`.** That is not a coincidence — the project was
built so that learning it *is* the interview prep.

---

## What to say if you get caught short

You will hit a question you can't answer. Everyone does. The good answer is short and
specific, never vague:

> "I don't know that off the top of my head. My instinct is [X], because [reason] — but
> I'd want to check [specific thing] before I said it with confidence."

That reads as an analyst. Waffle reads as a bluff. And *never* invent a number — if you
misquote your own project's figure, the interview is over.

---

## Files in this folder

| file | what it teaches |
|---|---|
| [`01-sql-from-zero.md`](01-sql-from-zero.md) | SQL from `SELECT` to window functions, taught entirely on this project's tables |
| [`02-product-metrics.md`](02-product-metrics.md) | north star, guardrails, cohorts, retention, funnels, RFM, unit economics |
| [`03-experimentation.md`](03-experimentation.md) | causation, confounders, A/B testing, power, p-values, CIs, guardrails |
| `../src/quiz.py` | interactive self-test, including a 15-question mock interview |
