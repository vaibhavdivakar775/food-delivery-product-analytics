# The Second-Order Problem — Executive Summary
**Audience:** Product / Growth leadership · **Analyst:** Vaibhav Divakar ·
**Data:** 60,000 users, 70,005 orders, Jan–Jun 2026 (simulated)

---

## 1. The problem
We activate users well and lose them immediately.

- **67.3%** of registered users place a first order — acquisition is not the problem.
- Only **29.9%** of new users place a **second order within 30 days**.
- Month-1 retention has fallen from **27%** (January cohort) to
  **19%** (May cohort) while order volume grew — we are buying
  growth that leaks straight back out.

Every ₹ of acquisition spend is amortised over **1.73 orders per user**. That is
the business problem: not traffic, not supply — **the second order**.

## 2. What the data says

**Finding 1 — A late first delivery is the single largest killer of the second order.**
Users whose first order arrived >10 min past the promised ETA repeat at
**20.5%** vs **32.6%** for on-time users — a **12.2pp** raw gap
(p < 0.001). Held constant within 69 city × channel × membership × platform cells covering
30,054 users, the gap is still **11.8pp**, and it shows a clean
dose–response once the ETA is genuinely missed:
  - Early / on time: **32.9%** repeat (n = 7,196)
  - 0-10 min late: **32.5%** repeat (n = 17,592)
  - 10-20 min late: **20.4%** repeat (n = 6,376)
  - 20-30 min late: **20.9%** repeat (n = 536)
  - 30+ min late: **11.1%** repeat (n = 27)
(the first ~10 minutes cost nothing — users forgive a small overrun, which is exactly
why the "late" threshold is set at 10 minutes rather than 0.)
Lateness is **concentrated**, not systemic: Bengaluru at
dinner peak runs **38.0%** late vs
a **20.7%** company average.

**Finding 2 — One funnel step is broken on one platform.**
Checkout → payment converts at **62.0% on Android vs 81.0% on iOS**, while
*every other step is within 0.5pp across platforms*. A gap isolated to a single step is
the signature of a defect, not of user intent. At current volume that is
**~15,491 lost orders in six months**.

**Finding 3 — We are buying the wrong users.**
Paid-social users repeat at **21.6%** vs **35.5%** for referral, and
consume the heaviest discounts. Members repeat at **48.2%** vs
**26.5%** for non-members.

## 3. The recommendation

| # | Action | Owner | Est. annual GMV | Confidence |
|---|---|---|---|---|
| 1 | **Fix the Android payment step** (SDK/UPI retry, fallback rail) | Eng · Payments | **₹69 L** | High — measured gap, one step, one platform |
| 2 | **Cut late deliveries 6pp in the worst city × daypart cells** (rider capacity + honest ETAs at peak) | Ops · City teams | **₹5.5 L** | Medium — observational, but stratified + dose–response |
| 3 | **Ship the Next-Order Nudge**, targeted (below) | Growth · CRM | **₹11.1 L net** | High — randomised experiment |

**Total ≈ ₹86 L / year** on a 60k-user base, at
AOV ₹447 and 2.72 incremental orders per retained user (both measured, not assumed).

Sequencing matters: **#1 is a bug fix, #2 is the durable fix, #3 is the fast lever.**
Do #3 while #1 and #2 are in flight — but do not let the coupon become the strategy.
Discounting a bad delivery experience is renting retention; fixing the delivery buys it.

## 4. The experiment (evidence for #3)

> **Hypothesis:** a ₹75 coupon valid 7 days, sent immediately after a user's first
> delivered order, raises the share who order again within 14 days.
> **Unit:** user · **Split:** 50/50 · **Primary metric:** repeat within 14 days
> **MDE:** 2.0pp absolute at 80% power, α = 0.05 → **6,275 users per arm required**

| | Control | Treatment |
|---|---|---|
| Users | 9,681 | 9,620 |
| Repeat within 14d | 18.99% | **22.28%** |

- **Absolute lift +3.29pp** (relative **+17.3%**),
  95% CI **[2.15pp, 4.43pp]**, z = 5.65, **p < 0.0001**.
- **Sample-ratio-mismatch check passed** (χ² p = 0.66) and the arms are balanced on
  pre-assignment covariates — the randomisation is trustworthy.
- **Guardrail breach:** treated users' second-order AOV falls **₹26** — they trade
  down to make the coupon worth using. That costs ₹3.7 L/yr and is already
  netted out above. Cancellation rate is unchanged.

**Decision: SHIP — but targeted, not blanket.** The lift is real and the CI excludes
zero, yet the effect is similar for users whose first delivery went well
(**+3.61pp**) and badly (**+2.04pp**): the coupon buys an extra order, it does
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
