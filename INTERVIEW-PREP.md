# Interview prep — defending this project cold

Everything below is a question I expect and the answer I can give without notes.
If I can't defend a number, it does not belong in the project.

---

## The 30-second version

> "I looked at a food-delivery marketplace where 67% of signups place a first order but
> only 30% place a second one within 30 days. I found the biggest driver of that drop is
> a **late first delivery** — it costs about 12 percentage points of 30-day repeat rate,
> and that survives stratification and shows a clean dose–response. I also found a broken
> checkout→payment step on Android worth ~15k orders in six months. Then I ran an
> experiment on a post-first-order coupon, got a +3.3pp lift with a real AOV guardrail
> cost, and recommended shipping it *targeted* — while making the point that discounting
> a bad delivery is renting retention, not buying it. Total sizing is about ₹86 lakh a
> year on a 60k-user base."

## The 2-minute version

1. **Framing.** Retention, not acquisition, is the constraint — 67% activate, ~30% come
   back within 30 days, and each cohort is worse than the last. So I picked one question:
   *why is there no second order, and which fix is worth the most GMV?*
2. **Metric first.** North star = 30-day repeat rate of new users, on matured cohorts
   only. Guardrails = cancellation rate, delivery time, rating, discount % of GMV.
3. **Where it leaks.** Cohort heatmap → the whole loss is in month 1. Split the retention
   curve by first-delivery experience → late-first-delivery users sit permanently lower.
4. **Is it causal?** Stratified across 69 city × channel × Gold × platform cells: gap goes
   12.2pp → 11.8pp. Dose–response is monotone past the 10-minute mark. Not proof, but
   strong enough to fund an ops change and a proper geo test.
5. **The second leak.** Funnel: biggest drop is checkout→payment. Segmented: Android 62%
   vs iOS 81%, every other step identical. That's a bug, not behaviour.
6. **Experiment.** ₹75 coupon after the first order: +3.29pp, CI [2.15, 4.43],
   p < 0.0001, SRM passed. AOV guardrail moved −₹26, so net value is ~₹11L, not ~₹25L.
7. **Decision & sizing.** Fix Android first (₹69L), fund rider capacity at peak in the two
   worst cells (₹5.5L), ship the nudge targeted (₹11.1L net). Then I automated the weekly
   monitor so the metrics don't go stale.

---

## The hard questions

### "Why that north-star metric? Why not GMV or DAU?"
GMV and DAU both go up when you spend more on acquisition — they measure the marketing
budget as much as the product. 30-day repeat rate of new users can't be bought that way;
it only moves if the experience improves. It is also the earliest strong LTV signal in
food delivery, because most of the churn happens between order 1 and order 2, and it
returns a read in weeks rather than quarters. GMV is still on the dashboard — as a
*supporting* metric, which is where it belongs.

### "Why 30 days? Why not 7 or 90?"
Food-delivery ordering has a natural weekly-to-fortnightly rhythm, so 7 days is too tight
— it labels normal users as churned. 90 days is a better LTV proxy but you wait a quarter
to learn anything, which kills the iteration loop. 30 days covers roughly two ordering
cycles. I'd track 90-day as a secondary check specifically to catch the "we just pulled
the order forward" failure mode.

### "Your late-delivery finding is correlational. Convince me."
Three things, and I'll say up front it's not proof:
1. **Stratification.** Within like-for-like cells (city × channel × Gold × platform) the
   gap barely moves: 12.2pp → 11.8pp. So it isn't composition.
2. **Dose–response.** Flat for the first 10 minutes, then a cliff. Confounders rarely
   produce a threshold-shaped curve that lines up with the promise the user was given.
3. **Mechanism.** There's a plausible story — the ETA is the promise, and the first order
   is where the user decides whether the promise is real.
   **What would settle it:** a geo experiment. Add rider capacity at peak in two matched
   cities, hold two as control, and compare new-user 30-day repeat rate. That's what I'd
   ask for next, and I'd rather say that than overclaim.

### "The reverse-causation version: maybe low-intent users order at peak, and peak is late."
That's the right challenge, and it's exactly why platform, channel and Gold status are in
the stratification — those are the observable proxies for intent. It's also why the
dose–response matters: within the *same* peak hour, a 25-minute overrun hurts much more
than a 5-minute one, and intent doesn't vary with the rider's traffic.

### "Your A/B test showed +3.3pp. Would you ship it?"
Yes, with two conditions. The statistics are clean — powered for a 2.0pp MDE (6,275/arm
required, 9,620 actual), SRM passed, arms balanced, CI excludes zero. But:
1. **A guardrail moved.** Second-order AOV fell ₹26 — people trade down to use the
   coupon. Netting the coupon *and* the AOV loss, it's worth ~₹11L/yr, not the ~₹25L the
   gross number implies. Still positive, so still ship.
2. **Targeting, not blanket.** The lift is +3.61pp for users whose first delivery went
   well but only +2.04pp for those whose went badly — the coupon is *weakest* exactly
   where the damage is, which tells me it isn't repairing anything — it's buying an
   order. So don't pay it to users who were coming back anyway, and keep a permanent
   10% holdout to keep the measurement honest.

### "What if the nudge just pulls forward an order that would have happened in week 5?"
Then the 14-day win is an accounting illusion and the 90-day effect is ~0. I flagged this
as the main threat to the result. The permanent holdout answers it: compare 90-day orders
per user, not just the 14-day flag. If the 90-day curves converge, the coupon is a
subsidy, not a growth lever, and I'd turn it off.

### "Which of your three recommendations would you do first, with only one engineer?"
The Android payment fix. It's the biggest number (₹69L/yr), the highest confidence — one
step, one platform, every other step within 0.2pp — and it's a bounded engineering task
rather than an ops budget or a CRM programme. It also has no guardrail downside: nobody
loses when a payment stops failing.

### "How do you know the Android gap is a bug and not that Android users are poorer / lower intent?"
Because if it were user intent, it would show up *before* checkout too — those users would
browse less, add to cart less, and abandon earlier. They don't; every step above checkout
matches iOS within 0.2pp. The gap appears only after the user has decided to pay.
That's the signature of a payment-rail failure. The first thing I'd ask Eng for is
payment-failure logs split by rail (UPI vs card vs wallet) and SDK version, to confirm.

### "This data is simulated. Doesn't that make it worthless?"
It makes the *effect sizes* worthless as facts about any real company, and I say so in the
README rather than hiding it. What transfers is everything else: the metric definitions,
the SQL, the cohort and funnel logic, the confounder handling, the experiment design and
guardrails, the decision framework. I simulated because public food-delivery datasets have
orders but no clickstream and no experiment assignments — so funnel and A/B analysis are
literally impossible on them, and those are the two things this job actually asks for. I'd
rather demonstrate the technique honestly than skip it. Also worth saying: I wrote the
simulator with a hidden causal structure and then tried to *recover* it — and on the first
pass my event generator silently erased a platform gap I'd injected, which I only caught
because the funnel came out suspiciously flat. That debugging is in the commit history.

### "What would you do differently with real data?"
- Join to **CAC by channel** so retention can be expressed as payback period, not just
  repeat rate — that changes the acquisition recommendation from directional to fundable.
- Use **restaurant- and rider-level data** to separate "the kitchen was slow" from "the
  rider was slow" — those are different fixes owned by different teams.
- Model **contribution margin per order**, not GMV. GMV is the vanity version; a coupon-led
  order at 8% margin isn't worth the same as an organic one.
- Add **survival analysis** for time-to-second-order instead of a binary 30-day flag —
  the binary throws away information about *how fast* users come back.

### "How would you extend this to Blinkit's 10-minute model?"
The structure holds but the constants change. Quick commerce has much higher order
frequency, so the equivalent north star is more like **7-day repeat rate** or weekly
orders per active user, and the retention window compresses accordingly. The lateness
finding gets *sharper*, not weaker: when the promise is 10 minutes, a 5-minute overrun is
a 50% miss rather than a rounding error, so I'd expect the threshold effect to kick in far
earlier. The funnel gains a step that food delivery doesn't have — **item availability**
— and I'd expect out-of-stock at the dark store to be a leak comparable to the payment
bug. Basket composition matters more too, because dark-store assortment is a decision you
control, unlike a restaurant's menu.

### "Walk me through one query."
Point at `sql/02_cohort_retention.sql` → `cohort_by_late`. Three CTEs: `first_order` gets
each user's first delivered order; `first_flag` joins back to tag whether that specific
order was late; `activity` computes months-elapsed with an explicit year×12 + month
arithmetic rather than a date-diff function so it behaves at year boundaries. Then a join
to cohort sizes for the denominator. The subtle bit is the denominator: it's the *cohort
size*, fixed, not the number of users active in the previous period — otherwise
"retention" quietly becomes a survival-conditional rate and looks far better than it is.

### "What's the weakest part of this project?"
The lateness impact estimate. It multiplies a 6pp assumed reduction by an observational
11.8pp effect by 2.72 measured orders per retained user — three numbers, and only the last
is measured. The direction is solid; the magnitude is a planning estimate, not a forecast,
and I'd present it as a range in a real review. The second-weakest is that "Gold members
repeat at 48%" is mostly selection, and I deliberately kept it out of the recommendations
because I can't separate the subscription's effect from the fact that people who intend to
order a lot are the ones who subscribe.

---

## Vocabulary I should be fluent in

| term | one-line definition I can say out loud |
|---|---|
| **North-star metric** | the single metric that best proxies delivered user value, that the team steers by |
| **Guardrail metric** | a metric that must not degrade while you push the north star |
| **Cohort** | a group of users bucketed by when they started, tracked over time |
| **Right-censoring** | recent users haven't had time to show the behaviour yet — counting them as failures biases retention down |
| **Funnel step conversion** | sessions at step *k* ÷ sessions at step *k−1* |
| **AOV** | average order value = GMV ÷ orders |
| **Take rate** | the platform's commission as a share of GMV |
| **Contribution margin** | revenue per order minus the variable costs of serving it (delivery, discount, payment fees) |
| **CAC payback** | months of contribution margin needed to recover the cost of acquiring a user |
| **RFM** | recency / frequency / monetary scoring, used to segment a user base |
| **MDE** | minimum detectable effect — the smallest lift the test is powered to find |
| **Statistical power** | probability of detecting a real effect of MDE size (convention: 80%) |
| **SRM** | sample ratio mismatch — the split isn't the split you designed, so the test is broken |
| **HTE** | heterogeneous treatment effect — the treatment works differently for different segments |
| **Novelty effect** | a lift that fades as the novelty of a change wears off |
| **Dark store** | the small fulfilment warehouse behind 10-minute quick commerce |

## Unit economics of this business (be ready to sketch it)

```
GMV per order                    ₹447
  − restaurant payout            (platform keeps a take rate, typically ~18–22%)
  = platform revenue             ~₹90
  − delivery cost                (rider payout, the biggest variable cost)
  − discount funded by platform  (here: ~28% on first orders, ~9% on repeat orders)
  − payment gateway fee
  = contribution margin per order
```

The key structural fact, and the reason this project is about the second order:
**first orders are loss-making** (heavy acquisition discount) and **repeat orders are
where the margin is** (discount drops from ~28% to ~9%). A user who never places a second
order is a user you paid to acquire and never recovered. That is the whole thesis in one
sentence.
