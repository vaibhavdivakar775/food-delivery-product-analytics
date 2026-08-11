# Product metrics, in plain English

Everything here is explained with **your project's actual numbers**, so learning the
concept and learning your project are the same activity.

---

## 1. What a product analyst is actually for

A PM has a budget and a team and must choose what to build next. Ten things look
plausible. The analyst's job is to say *"do this one, here's the evidence, here's roughly
what it's worth."*

Which means: **an analysis that doesn't change a decision was a waste of time.** That
sentence, said in an interview, is worth more than any chart. It is also the honest
summary of what your project does — the entire thing exists to rank three fixes.

---

## 2. The metric vocabulary

### North-star metric
The one number the team steers by. A good one is: (a) a genuine proxy for user value,
(b) fast enough to move that you can learn from it, (c) **not buyable with money**.

**Yours: the 30-day repeat rate of new users — currently ~30%.**
Of people who placed a first order at least 30 days ago, what share ordered again within
30 days of that first order?

Why not GMV or DAU? Because you can raise both tomorrow by spending more on ads. A metric
that goes up when marketing spends more is measuring the budget, not the product. Repeat
rate cannot be bought that way — it only moves if the experience gets better.

> **Say it like this:** "GMV and DAU are outcomes. Repeat rate is a cause. I want the team
> steering by a cause."

### Guardrail metric
Something that must **not** get worse while you chase the north star. Guardrails exist
because almost any metric can be gamed if it's the only one you watch.

Yours: cancellation rate, average delivery time, average rating, discount as a % of GMV,
net revenue per order.

Concrete example: give every user a 50% coupon and repeat rate soars — while discount %
of GMV explodes and you lose money on every order. The guardrail catches it. **This
actually happened in your experiment**: repeat rate went up, AOV went down ₹26.

### Activation
The share of registered users who reach the first real moment of value. Here: placing a
first order. **Yours: 67%.**

### Retention vs churn
Retention = the share still active after some period. Churn = 1 − retention. Same fact,
two framings; use whichever makes the sentence clearer.

### AOV, GMV
- **GMV** (gross merchandise value) = total rupee value of orders. **Yours: ₹3.13 Cr.**
- **AOV** (average order value) = GMV ÷ orders. **Yours: ₹447.**

GMV is *not* revenue. The platform keeps a **take rate** (commission), typically ~18–22%
in Indian food delivery. Confusing GMV with revenue is a rookie error and interviewers
listen for it.

### DAU / MAU and stickiness
Daily and monthly active users. DAU ÷ MAU is the "stickiness" ratio — 0.5 means the
average monthly user shows up ~15 days a month. Food delivery sits far lower than social
apps; that's normal, since people don't order daily.

---

## 3. How this business actually makes money

Learn this. It is the difference between "an analyst" and "a student with charts."

```
Customer pays for a ₹447 order
  → the restaurant gets most of it back (food cost)
  → the platform keeps a take rate, ~18-22%  ≈ ₹90
      − rider payout            (the biggest variable cost)
      − platform-funded discount
      − payment gateway fee
  = contribution margin per order   (thin — often single-digit rupees, sometimes negative)
```

Three sides of the marketplace, each with its own metrics:
- **Customers** — retention, frequency, AOV
- **Restaurants** — supply density, menu quality, availability
- **Delivery partners** — riders per hour, utilisation, delivery time

**The structural fact your entire project rests on:**
first orders carry ~28% discount, repeat orders ~9%. So **the first order loses money and
the repeat orders make it back.** A user who never places a second order is a user you
paid to acquire and never recovered.

That's why "30% second-order rate" is not a soft problem. It's the business.

> **Blinkit / quick commerce version:** dark stores instead of restaurants, 10-minute
> promise, smaller baskets but much higher frequency, and *item availability* becomes a
> funnel step that food delivery doesn't have. Same skeleton, different constants.

---

## 4. Cohorts and retention curves

A **cohort** is a group of users bucketed by when they started. Here: by the month of
their first order.

Why bucket at all? Because if you look at "all users" together, an influx of new signups
makes retention look like it's falling even when nothing changed. Cohorts hold the start
date constant so you're comparing like with like.

### Reading the cohort heatmap (`charts/02_cohort_heatmap.png`)

There is a fixed grammar. Learn both sentences:

- **Across a row** → how fast does one cohort decay? Yours: 100% → 27% → 18% → 11%.
  Most of the loss is in the very first month.
- **Down a column** → are newer cohorts better or worse than older ones? Yours (M1
  column): 27 → 27 → 24 → 23 → 19. **Newer cohorts are worse.** That's the alarm.

### Right-censoring — say this word in an interview

A user who first ordered five days ago has not *had* 30 days to come back. If you count
them as "didn't repeat", your retention number is fake and gets worse every month
automatically.

**Your fix:** the north-star metric only counts **matured cohorts** — users whose first
order was at least 30 days before the data cut-off.

This is a favourite trap question ("your May cohort looks terrible, why?") and knowing the
term instantly signals you've done this before. The May cohort partly *is* censored — you
say so, and point at the matured-cohort filter as the reason the headline number isn't.

---

## 5. The second-order problem (your headline)

Only ~30% of new users order again within 30 days. Because first orders are
loss-making, that means most acquisition spend never gets recovered.

**Finding: a late first delivery is the biggest single driver.**
- On-time first delivery → **32.6%** repeat within 30 days
- Late first delivery (>10 min past the promised ETA) → **20.5%**
- A gap of **12.2 percentage points**

Two things to be careful about, because both come up:

**"Percentage points" vs "percent."** 20.5% → 32.6% is a **12.2 percentage point** gap and
about a **59% relative** increase. Mixing these up is a tell. Say "pp" when you mean the
arithmetic difference.

**Why >10 minutes, not >0?** Because a 2-minute overrun isn't a bad experience, and the
data agrees: the dose–response curve is flat for the first 10 minutes and then falls off a
cliff. The threshold was chosen to match where user behaviour actually changes — and you
should volunteer that, because "why that threshold?" is a natural probe.

---

## 6. Funnels

A funnel is the ordered set of steps a user passes through. Yours:

```
app_open → search → restaurant_view → add_to_cart → checkout_start → payment_success
```

**Step conversion** = sessions at step k ÷ sessions at step k−1.

Your funnel: 100% → 88% → 86% → 78% → 69% → **66%** at the last step.

### The one rule that matters

**Never read an aggregate funnel without segmenting it.** The aggregate tells you *a step
is weak*; the segments tell you *who it's weak for* — and only the second one is
actionable.

Yours, segmented by platform:
- Android checkout→payment: **62%**
- iOS checkout→payment: **81%**
- **Every earlier step matches within 0.2pp**

That last line is the whole argument. If Android users were simply poorer or less
interested, they'd browse less and abandon earlier *too*. They don't — they behave
identically until the moment they try to pay. **A gap isolated to one step is the
signature of a bug, not of user intent.** That's an engineering ticket, not a growth
experiment, and it's worth ~15,500 orders over six months.

Be ready for: *"how would you confirm it's a bug?"* → ask Eng for payment-failure logs
split by rail (UPI / card / wallet), by SDK version, and by app version.

---

## 7. Segmentation and RFM

Averages hide everything. Segmentation is just "stop averaging over people who are
different."

**RFM** scores each user 1–5 on three axes:
- **R**ecency — how recently did they order? (recent = high score)
- **F**requency — how often?
- **M**onetary — how much have they spent?

You compute the scores with `NTILE(5)` (see the SQL guide, part 7) and then map score
combinations to names a PM can act on: Champions, Loyal, At Risk, Hibernating.

Your result: **Champions are ~19% of users but carry ~36% of GMV.** So retention spend
should be weighted toward keeping them, not sprayed across everyone.

Also from segmentation: **paid-social users repeat at 21.6% vs 35.5% for referral**, on
the heaviest discounts. You are buying discount-chasers. The implication isn't "stop
spending" — it's *"measure channels on repeat rate and payback, not on cost per install."*

---

## 8. Turning a finding into a number

An analysis that stops at "statistically significant" is unfinished. Every recommendation
in your project carries a rupee value **and its assumptions**, so a sceptic argues with
the assumption rather than dismissing the whole thing.

The nudge, worked through:

```
new first-time users per year          ≈ 63,000
× lift from the experiment                +3.29pp
= extra retained users per year        ≈ 2,088
× extra orders per retained user           2.72   (measured from the data)
× AOV                                      ₹447
= gross extra GMV                      ≈ ₹25.4 L
− coupon cost (₹75 × every treated repeater)  − ₹10.6 L
− AOV guardrail loss (₹26 × those orders)     − ₹3.7 L
= net                                  ≈ ₹11.1 L per year
```

Two habits to point out when you present this, because they're what makes it credible:
1. **Subtract the guardrail cost.** Most write-ups count the coupon and quietly ignore
   that treated users spend less per order.
2. **Measure what you can, assume the rest — and label which is which.** 2.72 orders per
   retained user is measured; the 6pp lateness reduction is an assumption, and it's the
   weakest number in the project. Say so before they find it.

---

## Self-test (answer out loud, no notes)

1. What's your north-star metric and why not GMV?
2. What's a guardrail metric — and which one moved in your experiment?
3. Explain right-censoring to someone who's never heard the term.
4. Reading your cohort heatmap: what does a column tell you vs a row?
5. Why is a gap in one funnel step on one platform evidence of a bug?
6. Why do first orders lose money?
7. What's the difference between 12 percentage points and 12 percent?
8. Which number in your project would you attack first if you were the interviewer?

If you can answer all eight cleanly, you can defend the metrics half of the project.
Then run `python3 src/quiz.py --topic metrics` to check yourself against the real figures.
