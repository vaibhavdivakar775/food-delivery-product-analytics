# Causation and A/B testing, in plain English

This is the highest-leverage file in the folder. Most candidates can describe a funnel.
Very few can defend a causal claim or read an experiment properly. If you learn one thing
deeply, learn this.

---

## Part A — Correlation vs causation

### The problem, concretely

You observe: users whose first delivery was late repeat at **20.5%**; on-time users repeat
at **32.6%**. A 12.2pp gap.

The tempting conclusion: *late deliveries cause churn.*
The honest objection: *maybe late deliveries and churn just happen to the same people.*

Both could produce that table. Say the objection **before the interviewer does** — it is
the single strongest signal you can send.

### Confounder

A third thing that causes both. Example: Bengaluru has the worst traffic (more late
orders) **and** the most competition (users churn more anyway). Then "late" would look bad
even if lateness itself changed nothing.

### Your three defences

**1. Stratification.** Compare late vs on-time users *inside* the same box — same city,
same acquisition channel, same Gold status, same platform — then re-weight the boxes by
size. If Bengaluru were the explanation, the gap would collapse once you compare Bengaluru
to Bengaluru.

Yours: 69 boxes, ~30,000 users, gap goes **12.2pp → 11.8pp**. It barely moves. Composition
explains almost none of it.

> Plain-English version: *"I compared like with like, and the gap survived."*

**2. Dose–response.** If lateness truly causes churn, *more* lateness should cause *more*
churn. It does:

| how late | 30-day repeat rate |
|---|---|
| early / on time | 32.9% |
| 0–10 min | 32.5% |
| 10–20 min | 20.4% |
| 20–30 min | 20.9% |
| 30+ min | 11.1% (only 27 users — small sample, say so) |

Flat, then a cliff. Confounders rarely produce a threshold-shaped curve that lines up
exactly with the promise the user was given.

**Say the caveat yourself:** the 30+ bucket has 27 users, which is far too few to lean on.
Volunteering the weak part of your own evidence is what makes the strong part believable.

**3. A mechanism.** There's a story that makes sense: for a first-time user the app isn't
the product — the *delivery* is. A missed ETA teaches them the promise is unreliable.

### What would actually settle it

An experiment: add rider capacity at peak in two cities, hold two matched cities as
control, compare new-user 30-day repeat rate. That's a **geo experiment**, and proposing
it is the right answer to *"how confident are you?"*

**Your honest position, memorise it:**
> "It's observational. Stratification and dose–response make confounding unlikely, but the
> clean test is a geo experiment. I'd fund the ops change on this evidence and run the geo
> test alongside to confirm the size of the effect."

That answer is better than claiming causation. It shows you know the difference.

---

## Part B — A/B testing

### The idea

You can't compare people who chose a thing with people who didn't — the choosing is
itself informative. So you **randomly** split users into two groups, change one thing for
one group, and compare. Randomisation makes the groups identical *on average* in every
respect, including things you never measured. That's the whole magic.

### Your experiment

> **Hypothesis:** a ₹75 coupon valid 7 days, sent right after a user's first delivered
> order, increases the share who order again within 14 days.
>
> - **Unit of randomisation:** the user (not the order, not the session)
> - **Split:** 50/50 · **Primary metric:** repeat order within 14 days
> - **MDE:** 2.0pp absolute, 80% power, α = 0.05
> - **Guardrails:** second-order AOV, second-order cancellation rate, coupon cost

### The vocabulary, one at a time

**Unit of randomisation.** What gets flipped — a user, a session, a city. Must match how
the treatment is experienced. Yours is the user, because a coupon belongs to a person; if
you randomised per *order*, the same person could land in both arms and the arms would
contaminate each other.

**Primary metric.** The one metric that decides the call. Exactly one. If you have three
"primary" metrics, you will find a win in at least one by luck.

**MDE (minimum detectable effect).** The smallest effect the test is big enough to find.
Yours: 2.0pp. Smaller effects would need more users.

**Power.** The chance of detecting a real effect of MDE size. Convention: 80%. Under-
powered tests produce "no significant difference" and everyone wrongly concludes "it
doesn't work" — when the truth is "we couldn't tell."

**Sample size — computed BEFORE the test.** From base rate + MDE + power + α: **6,275
users per arm required**. You had 9,620 and 9,681. Adequately powered.
> Doing this calculation *before* rather than after is what separates a real experiment
> from a dashboard comparison. Be ready to say why: if you only decide the sample size
> once you've seen the result, you're choosing the moment that flatters you.

**p-value.** *If the coupon truly did nothing*, how likely is a difference at least this
big by pure chance? Yours: **< 0.0001** — extremely unlikely to be a fluke.

> It is **not** "the probability the coupon works." Getting this backwards is the classic
> stats-interview trap. Practise the correct sentence out loud.

**Confidence interval.** The range of effects consistent with your data. Yours:
**[2.15pp, 4.43pp]**. Because the whole interval is above zero, the direction is not in
doubt. A CI is more useful than a p-value because it carries the *size*: you can plan
against "somewhere between 2 and 4.4 points," not against "significant."

**SRM (sample ratio mismatch).** You designed 50/50 — did you get it? If the split is
lopsided, assignment or logging is broken and **nothing else in the readout can be
trusted**, no matter how good the lift looks. Yours passed (χ² p = 0.60).
> Mentioning SRM unprompted is a strong signal. Almost nobody at entry level knows it.

**Balance check.** The arms should also match on things decided *before* assignment —
first-order AOV, lateness, city. If they don't, randomisation didn't work. Yours match.

**Guardrails.** Yours moved: treated users' second-order AOV fell **₹26**. People trade
down to make the coupon worth using. That is a real cost — it drops the value from ~₹25L
gross to ~₹11L net. Still positive, so still ship, but the honest number is the net one.

**Heterogeneous treatment effect (HTE).** Does it work differently for different people?
Yours: **+3.61pp** for users whose first delivery went fine, **+2.04pp** for those whose
went badly. The coupon is *weakest exactly where the damage is* — so it buys an extra
order, it doesn't repair a bad experience. **That's the most interesting sentence in your
whole project**, because it's the finding a growth team would rather not hear.

**Novelty effect.** A lift that fades once the change stops being new. The reason you keep
a holdout and re-read the result later.

### The ship / don't-ship answer

> "Yes, ship — targeted, with a permanent 10% holdout. The statistics are clean: powered
> for a 2pp MDE, SRM passed, arms balanced, CI excludes zero. But a guardrail moved — AOV
> down ₹26 — so the real value is ~₹11L, not the ~₹25L the gross lift implies. And since
> the effect is *weaker* for users with a bad first delivery, this isn't a substitute for
> fixing delivery. So: ship it, don't spray it, and don't let it become the strategy."

Notice the shape: **statistics → guardrail → limitation → decision.** Copy that shape for
any experiment question you're ever asked, about any product.

### The threat you should raise yourself

Fourteen days is short. If the coupon merely **pulls forward** an order that would have
happened in week five, the 14-day win is an accounting illusion and the 90-day effect is
zero. The permanent holdout answers it: compare 90-day orders per user, not the 14-day
flag. If the curves converge, the coupon is a subsidy, not growth, and you turn it off.

---

## Part C — Questions you will be asked

**"What's a p-value?"**
> "If the treatment truly had no effect, the p-value is the probability of seeing a
> difference at least as large as the one I saw, by chance alone. Mine was under 0.0001,
> so chance is a poor explanation. It doesn't tell me the probability that the treatment
> works, and it says nothing about whether the effect is big enough to matter — that's
> what the confidence interval is for."

**"Your result is significant but the lift is 0.1pp. Ship it?"**
> "No. Significance says the effect is real; it doesn't say it's worth having. With a big
> enough sample, trivially small effects become significant. I'd weigh it against the cost
> and the guardrails — a 0.1pp lift that costs ₹75 a head is a loss."

**"You ran the test for a week and it wasn't significant. Now what?"**
> "First check whether it was powered for the effect I cared about — 'not significant'
> often just means 'too small a sample'. If it was powered, I'd take it as evidence the
> effect is smaller than my MDE, and I'd rather kill it than keep peeking until it goes
> green, which inflates false positives."

**"How would you test the delivery finding?"**
> "Geo experiment. Match cities on volume, late rate and AOV, add rider capacity at peak
> in the treatment cities, and compare new-user 30-day repeat rate. Randomising individual
> users doesn't work here, because you can't give one user in a city a faster rider fleet
> — the treatment is inherently geographic."

**"What could invalidate your whole project?"**
> "Three things. One, the lateness effect could be confounded by something I couldn't
> observe — intent, mainly. Two, the nudge might only pull orders forward, which the
> 14-day window can't see. Three, the data is simulated, so the effect sizes are
> properties of my simulation; the methods transfer, the magnitudes don't."

---

## Self-test

1. Why randomise at the user level, not the order level?
2. State what a p-value is — and what it isn't.
3. What's SRM and why do you check it *first*?
4. Your test won on the primary metric. Name the two reasons you still might not ship.
5. Explain a confounder using your own project as the example.
6. Why is a dose–response curve evidence for causation?
7. What's the difference between "not significant" and "no effect"?

Then run `python3 src/quiz.py --topic experiment`.
