"""
generate_data.py
================
Builds a realistic, SIMULATED food-delivery dataset for the "Second Order Problem"
analysis, then loads it into a SQLite database (`data/delivery.db`).

WHY SIMULATED:
  Public food-delivery datasets have orders but no *event/clickstream* data, and no
  experiment assignment data. Funnel analysis and A/B analysis are impossible without
  them. So we generate data with a documented, explicit causal structure and then
  *recover* that structure with SQL/stats. The analysis techniques are exactly what you
  would run on production data; only the source of the rows differs.

THE GROUND TRUTH BAKED IN (the analysis must rediscover these, not assume them):
  1. A LATE first delivery is the single biggest killer of the 2nd order.
  2. The checkout -> payment step leaks badly on Android (a UPI/payment-SDK failure).
  3. Paid-social users are cheap to acquire but repeat poorly (discount-chasers).
  4. Premium (paid membership) members repeat far more -- partly selection, partly the product.
  5. A post-first-order "₹75 off your next order within 7 days" nudge lifts the repeat
     rate by roughly +3pp absolute (this is what the A/B test should detect).

Everything is seeded, so the numbers are reproducible.
"""

import os
import sqlite3
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)          # one seed -> fully reproducible dataset

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")

# ----------------------------------------------------------------------------------
# 0. Simulation parameters (all knobs live here so they are easy to defend/change)
# ----------------------------------------------------------------------------------
N_USERS = 60_000
START = pd.Timestamp("2026-01-01")       # first signup date
END = pd.Timestamp("2026-06-30")         # data cut-off

CITIES = ["Bengaluru", "Delhi NCR", "Mumbai", "Hyderabad", "Pune", "Kolkata"]
CITY_W = [0.26, 0.22, 0.18, 0.14, 0.11, 0.09]

CHANNELS = ["organic", "paid_social", "paid_search", "referral"]
CHANNEL_W = [0.34, 0.30, 0.22, 0.14]

CUISINES = ["North Indian", "South Indian", "Chinese", "Biryani", "Pizza",
            "Burgers", "Desserts", "Healthy"]
CUISINE_W = [0.20, 0.14, 0.14, 0.16, 0.12, 0.10, 0.08, 0.06]

PLATFORMS = ["Android", "iOS"]
PLATFORM_W = [0.72, 0.28]                # India-realistic split


# ----------------------------------------------------------------------------------
# 1. USERS  -- one row per registered user
# ----------------------------------------------------------------------------------
def make_users() -> pd.DataFrame:
    n = N_USERS

    # Signups grow ~linearly over the 6 months (a growing product).
    span_days = (END - START).days
    # weight later days a bit more heavily -> growth
    day_weights = np.linspace(1.0, 1.8, span_days + 1)
    day_weights /= day_weights.sum()
    signup_offset = RNG.choice(np.arange(span_days + 1), size=n, p=day_weights)
    signup_date = START + pd.to_timedelta(signup_offset, unit="D")

    city = RNG.choice(CITIES, size=n, p=CITY_W)
    platform = RNG.choice(PLATFORMS, size=n, p=PLATFORM_W)
    channel = RNG.choice(CHANNELS, size=n, p=CHANNEL_W)

    # Premium (paid membership) adoption: higher for iOS + organic/referral users.
    p_member = (0.10
              + 0.06 * (platform == "iOS")
              + 0.05 * np.isin(channel, ["organic", "referral"]))
    is_member = RNG.random(n) < p_member

    # Latent "affinity": how much this user intrinsically likes ordering food online.
    # Normally distributed; drives both order frequency and basket size.
    affinity = RNG.normal(0, 1, n)
    # paid_social skews to low-affinity, discount-chasing users
    affinity -= 0.35 * (channel == "paid_social")
    affinity += 0.30 * is_member

    return pd.DataFrame({
        "user_id": np.arange(1, n + 1),
        "signup_date": signup_date,
        "city": city,
        "platform": platform,
        "acquisition_channel": channel,
        "is_member": is_member.astype(int),
        "_affinity": affinity,          # underscore = latent, dropped before export
    })


# ----------------------------------------------------------------------------------
# 2. ORDERS  -- the heart of the simulation
# ----------------------------------------------------------------------------------
# Model, per user:
#   a) does the user ever place a 1st order?          (activation)
#   b) was that 1st order delivered late / rated low? (experience)
#   c) does the user place a 2nd order within 30 days? (the metric we care about)
#   d) if retained, how many more orders + when        (ongoing frequency)
# ----------------------------------------------------------------------------------
def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def _order_timestamps(base_dates: pd.Series, rng) -> pd.Series:
    """Give each order a realistic time-of-day: lunch and dinner peaks."""
    n = len(base_dates)
    # 60% dinner peak (~20:00), 30% lunch peak (~13:00), 10% spread out
    bucket = rng.choice([0, 1, 2], size=n, p=[0.30, 0.58, 0.12])
    hour = np.where(bucket == 0, rng.normal(13.0, 1.0, n),
           np.where(bucket == 1, rng.normal(20.2, 1.1, n),
                                 rng.uniform(8, 23, n)))
    hour = np.clip(hour, 7.5, 23.9)
    minutes = (hour * 60).astype(int)
    return base_dates + pd.to_timedelta(minutes, unit="m")


def make_orders(users: pd.DataFrame):
    rng = RNG
    n = len(users)
    aff = users["_affinity"].to_numpy()
    member = users["is_member"].to_numpy()
    ch = users["acquisition_channel"].to_numpy()
    city = users["city"].to_numpy()
    plat = users["platform"].to_numpy()
    signup = users["signup_date"].to_numpy()

    # ---- (a) activation: does the user ever place a first order? -----------------
    p_activate = _sigmoid(0.95 + 0.55 * aff
                          + 0.35 * member
                          - 0.25 * (ch == "paid_social"))
    activated = rng.random(n) < p_activate

    # first order lands 0-9 days after signup (most on day 0-1)
    lag = rng.choice(np.arange(10), size=n, p=[.42, .18, .11, .07, .05, .05, .04, .03, .03, .02])
    first_date = pd.to_datetime(signup) + pd.to_timedelta(lag, unit="D")
    # a signup whose first order would land after the data cut-off is simply not yet
    # activated in this dataset -- otherwise we'd invent a phantom July cohort
    activated = activated & np.asarray(first_date <= END)

    # ---- (b) first-order delivery experience -------------------------------------
    # Promised ETA ~ 32 min. Actual depends on city load + peak hour.
    city_delay = pd.Series(city).map({
        "Bengaluru": 6.5,      # worst traffic -> most lateness (the story)
        "Delhi NCR": 4.0,
        "Mumbai": 3.0,
        "Hyderabad": 2.0,
        "Pune": 2.0,
        "Kolkata": 1.5,
    }).to_numpy()

    def delivery_block(order_ts, k):
        """Return (promised, actual, is_late) arrays for k orders."""
        hr = pd.Series(order_ts).dt.hour.to_numpy()
        peak = ((hr >= 12) & (hr <= 14)) | ((hr >= 19) & (hr <= 22))
        promised = np.full(k, 32.0)
        actual = (promised
                  + rng.normal(0, 6, k)          # base noise
                  + city_delay[:k] * 0            # placeholder, set by caller
                  + 7.0 * peak)                   # peak-hour surge
        return promised, actual, peak

    # first orders
    m = activated.sum()
    f_idx = np.where(activated)[0]
    f_dates = pd.Series(first_date[f_idx])
    f_ts = _order_timestamps(f_dates, rng)
    f_hr = f_ts.dt.hour.to_numpy()
    f_peak = ((f_hr >= 12) & (f_hr <= 14)) | ((f_hr >= 19) & (f_hr <= 22))
    f_promised = np.full(m, 32.0)
    f_actual = (f_promised - 7.0 + rng.normal(0, 5, m)
                + 0.9 * city_delay[f_idx]
                + 6.0 * f_peak
                + rng.gamma(1.2, 3.2, m))         # long right tail: the bad experiences
    f_late = f_actual > f_promised + 10           # "late" = >10 min past promise

    # basket size / GMV
    def gmv_for(aff_slice, member_slice, k):
        base = 380 + 90 * aff_slice + 40 * member_slice
        return np.clip(base + rng.normal(0, 110, k), 120, 3000).round(0)

    f_gmv = gmv_for(aff[f_idx], member[f_idx], m)
    # first-order discount is heavy (acquisition promo), heaviest on paid_social
    f_disc = np.clip(f_gmv * (0.28 + 0.10 * (ch[f_idx] == "paid_social")
                              + rng.normal(0, 0.05, m)), 0, None).round(0)
    f_deliv_fee = np.where(member[f_idx] == 1, 0, rng.choice([0, 25, 35, 45], m, p=[.15, .35, .30, .20]))

    # rating: driven mostly by lateness
    f_rating_lat = 4.55 - 0.055 * np.clip(f_actual - f_promised, 0, None) + rng.normal(0, 0.45, m)
    f_rating = np.clip(np.round(f_rating_lat * 2) / 2, 1.0, 5.0)

    # a few first orders get cancelled
    f_cancel = rng.random(m) < 0.025

    first_orders = pd.DataFrame({
        "user_id": users["user_id"].to_numpy()[f_idx],
        "order_ts": f_ts.to_numpy(),
        "order_seq": 1,
        "city": city[f_idx],
        "platform": plat[f_idx],
        "cuisine": rng.choice(CUISINES, m, p=CUISINE_W),
        "gmv": f_gmv,
        "discount": f_disc,
        "delivery_fee": f_deliv_fee,
        "promised_minutes": f_promised,
        "delivery_minutes": np.round(f_actual, 1),
        "is_late": f_late.astype(int),
        "rating": f_rating,
        "status": np.where(f_cancel, "cancelled", "delivered"),
    })

    # ---- (c) THE SECOND ORDER: the outcome the whole project is about -------------
    # log-odds of placing a 2nd order within 30 days of the first
    lo = (-1.05
          + 0.60 * aff[f_idx]
          + 0.85 * member[f_idx]
          - 0.62 * f_late                                  # <-- the headline driver
          - 0.45 * f_cancel
          + 0.22 * (f_rating >= 4.5)
          - 0.38 * (ch[f_idx] == "paid_social")
          + 0.15 * (ch[f_idx] == "referral")
          + 0.0009 * (f_gmv - 380))
    p_second = _sigmoid(lo)
    second = rng.random(m) < p_second

    # ---- (d) ongoing behaviour for retained users --------------------------------
    s_idx = np.where(second)[0]                 # index INTO first_orders
    k = len(s_idx)
    # how many extra orders (2nd, 3rd, ...) before the data cut-off
    lam = np.clip(2.2 + 1.6 * aff[f_idx][s_idx] + 2.4 * member[f_idx][s_idx], 0.6, 14)
    # scale by how much time is left in the observation window
    days_left = (END - pd.Series(first_orders["order_ts"].to_numpy()[s_idx])).dt.days.to_numpy()
    lam = lam * np.clip(days_left / 120.0, 0.15, 1.6)
    n_extra = np.maximum(1, rng.poisson(lam))

    rows = []
    uid = first_orders["user_id"].to_numpy()[s_idx]
    t0 = pd.Series(first_orders["order_ts"].to_numpy()[s_idx])
    for i in range(k):
        cnt = int(n_extra[i])
        # gaps: first gap <=30 days (that's the definition of "retained"), then
        # inter-order gaps from an exponential -> realistic spacing
        gaps = np.concatenate([[rng.integers(2, 31)],
                               rng.exponential(14, cnt - 1)]) if cnt > 1 else np.array([rng.integers(2, 31)])
        days = np.cumsum(gaps)
        ts = t0.iloc[i] + pd.to_timedelta(days, unit="D")
        ts = ts[ts <= END]
        for j, t in enumerate(ts):
            rows.append((uid[i], t, j + 2, s_idx[i]))

    if rows:
        rep = pd.DataFrame(rows, columns=["user_id", "order_ts", "order_seq", "_fi"])
        r = len(rep)
        fi = rep["_fi"].to_numpy()
        rep["order_ts"] = _order_timestamps(
            pd.Series(pd.to_datetime(rep["order_ts"]).dt.normalize()), rng)
        hr = pd.to_datetime(rep["order_ts"]).dt.hour.to_numpy()
        peak = ((hr >= 12) & (hr <= 14)) | ((hr >= 19) & (hr <= 22))
        u_i = f_idx[fi]                       # index back into users
        promised = np.full(r, 32.0)
        actual = (promised - 7.5 + rng.normal(0, 5, r) + 0.9 * city_delay[u_i]
                  + 6.0 * peak + rng.gamma(1.2, 3.0, r))
        rep["city"] = city[u_i]
        rep["platform"] = plat[u_i]
        rep["cuisine"] = rng.choice(CUISINES, r, p=CUISINE_W)
        # repeat orders: bigger basket, much smaller discount (this is the margin story)
        rep["gmv"] = gmv_for(aff[u_i], member[u_i], r) + 45
        rep["discount"] = np.clip(rep["gmv"] * (0.09 + rng.normal(0, 0.04, r)), 0, None).round(0)
        rep["delivery_fee"] = np.where(member[u_i] == 1, 0,
                                       rng.choice([0, 25, 35, 45], r, p=[.15, .35, .30, .20]))
        rep["promised_minutes"] = promised
        rep["delivery_minutes"] = np.round(actual, 1)
        rep["is_late"] = (actual > promised + 10).astype(int)
        rep["rating"] = np.clip(np.round(
            (4.55 - 0.055 * np.clip(actual - promised, 0, None) + rng.normal(0, 0.45, r)) * 2) / 2, 1, 5)
        rep["status"] = np.where(rng.random(r) < 0.02, "cancelled", "delivered")
        rep = rep.drop(columns=["_fi"])
        orders = pd.concat([first_orders, rep], ignore_index=True)
    else:
        orders = first_orders

    orders = orders.sort_values(["user_id", "order_ts"]).reset_index(drop=True)
    orders.insert(0, "order_id", np.arange(1, len(orders) + 1))
    orders["gmv"] = orders["gmv"].astype(float)
    return orders


# ----------------------------------------------------------------------------------
# 3. APP EVENTS -- session-level funnel (app_open -> ... -> payment_success)
# ----------------------------------------------------------------------------------
FUNNEL = ["app_open", "search", "restaurant_view", "add_to_cart",
          "checkout_start", "payment_success"]


def make_events(users: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """
    Sessions come in three flavours:
      1. CONVERTING sessions   -- exactly one per order, reach payment_success (step 6).
      2. PAYMENT-FAILED sessions -- reached checkout_start (step 5) and died there.
         Their COUNT per platform is what encodes the injected defect: Android's
         checkout->payment conversion is ~62%, iOS's ~81%. A gap isolated to a single
         step (with every earlier step identical) is the signature of a payment-SDK
         bug rather than of different user intent -- which is exactly the argument the
         analysis makes.
      3. ABANDONED sessions -- died somewhere in steps 1-4 while browsing.
    """
    rng = RNG
    u = users.set_index("user_id")
    span = (END - START).days

    # --- 1. converting sessions ---------------------------------------------------
    o = orders.copy()
    conv = pd.DataFrame({
        "user_id": o["user_id"],
        "session_start": pd.to_datetime(o["order_ts"])
                         - pd.to_timedelta(rng.integers(4, 25, len(o)), unit="m"),
        "platform": o["platform"],
        "city": o["city"],
        "max_step": 6,
    })

    # --- 2. payment-failed sessions (the injected defect) -------------------------
    PAY_CONV = {"Android": 0.62, "iOS": 0.81}
    failed = []
    for plat, target in PAY_CONV.items():
        n_orders = int((o["platform"] == plat).sum())
        # if conv = orders / (orders + failed)  ->  failed = orders * (1/conv - 1)
        n_fail = int(round(n_orders * (1.0 / target - 1.0)))
        pool = o.loc[o["platform"] == plat, "user_id"].to_numpy()
        pick = rng.choice(pool, n_fail)
        day = START + pd.to_timedelta(rng.integers(0, span + 1, n_fail), unit="D")
        failed.append(pd.DataFrame({
            "user_id": pick,
            "session_start": _order_timestamps(pd.Series(day), rng).to_numpy(),
            "platform": plat,
            "city": u.loc[pick, "city"].to_numpy(),
            "max_step": 5,
        }))
    failed = pd.concat(failed, ignore_index=True)

    # --- 3. abandoned browsing sessions (die in steps 1-4) ------------------------
    # IMPORTANT: the abandon count is scaled PER PLATFORM to that platform's number of
    # checkout-reaching sessions (orders + payment failures), not to its order count.
    # Otherwise Android -- which has extra payment-failure sessions sitting at step 5 --
    # would show inflated conversion at steps 1-4 as a pure artifact, and the funnel
    # would no longer isolate the defect to a single step.
    p_adv = {1: 0.80, 2: 0.74, 3: 0.52, 4: 0.58}   # advance probability per step
    browse = []
    for plat, target in PAY_CONV.items():
        n_orders = int((o["platform"] == plat).sum())
        n_b = int(round(2.2 * n_orders / target))
        pool = o.loc[o["platform"] == plat, "user_id"].to_numpy()
        pick = rng.choice(pool, n_b)
        day = START + pd.to_timedelta(rng.integers(0, span + 1, n_b), unit="D")
        max_step = np.ones(n_b, dtype=int)
        alive = np.ones(n_b, dtype=bool)
        for step in range(1, 5):
            adv = alive & (rng.random(n_b) < p_adv[step])
            max_step = np.where(adv, step + 1, max_step)
            alive = adv
        max_step = np.minimum(max_step, 4)         # abandoned = never reached checkout
        browse.append(pd.DataFrame({
            "user_id": pick,
            "session_start": _order_timestamps(pd.Series(day), rng).to_numpy(),
            "platform": plat,
            "city": u.loc[pick, "city"].to_numpy(),
            "max_step": max_step,
        }))
    browse = pd.concat(browse, ignore_index=True)

    sess = pd.concat([conv, failed, browse], ignore_index=True)
    sess = sess[pd.to_datetime(sess["session_start"]).between(START, END)].reset_index(drop=True)
    sess["session_id"] = np.arange(1, len(sess) + 1)

    # explode each session into one row per funnel step it reached
    ev = sess.loc[sess.index.repeat(sess["max_step"].to_numpy())].copy()
    ev["step_no"] = ev.groupby("session_id").cumcount() + 1
    ev["event_name"] = [FUNNEL[i - 1] for i in ev["step_no"]]
    ev["event_ts"] = (pd.to_datetime(ev["session_start"])
                      + pd.to_timedelta(ev["step_no"] * rng.integers(20, 120, len(ev)), unit="s"))
    ev = ev[["session_id", "user_id", "event_ts", "event_name", "step_no", "platform", "city"]]
    return ev.sort_values(["session_id", "step_no"]).reset_index(drop=True)


# ----------------------------------------------------------------------------------
# 4. A/B TEST -- "Next-Order Nudge": ₹75 off your 2nd order, valid 7 days
# ----------------------------------------------------------------------------------
def make_experiment(users: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """
    Population: users whose FIRST order happened during the experiment window.
    Randomised 50/50 at the user level on first-order completion.
    True effect: repeat-in-14-days 21.5% (control) -> 24.6% (treatment), and a small
    NEGATIVE effect on AOV (people trade down to hit the coupon) -- a real guardrail.
    """
    rng = RNG
    firsts = orders[orders["order_seq"] == 1].copy()
    firsts["order_ts"] = pd.to_datetime(firsts["order_ts"])
    win_lo, win_hi = pd.Timestamp("2026-04-01"), pd.Timestamp("2026-06-15")
    exp = firsts[firsts["order_ts"].between(win_lo, win_hi)].copy()

    n = len(exp)
    variant = rng.choice(["control", "treatment"], n, p=[0.5, 0.5])

    # baseline probability of a repeat order within 14 days, per user
    base_lo = (-1.35
               - 0.55 * exp["is_late"].to_numpy()
               + 0.0008 * (exp["gmv"].to_numpy() - 380))
    lift = np.where(variant == "treatment", 0.20, 0.0)      # log-odds lift
    p = _sigmoid(base_lo + lift)
    repeat14 = (rng.random(n) < p).astype(int)

    # guardrail: AOV of the 2nd order (treatment trades down slightly)
    aov2 = np.where(repeat14 == 1,
                    np.clip(rng.normal(430, 120, n) - 22 * (variant == "treatment"), 100, None),
                    np.nan).round(0)
    # guardrail: cancellation of the 2nd order
    cancel2 = np.where(repeat14 == 1, (rng.random(n) < 0.021).astype(float), np.nan)

    return pd.DataFrame({
        "user_id": exp["user_id"].to_numpy(),
        "first_order_id": exp["order_id"].to_numpy(),
        "assigned_ts": exp["order_ts"].to_numpy(),
        "variant": variant,
        "repeat_within_14d": repeat14,
        "second_order_aov": aov2,
        "second_order_cancelled": cancel2,
        "coupon_cost": np.where((variant == "treatment") & (repeat14 == 1), 75.0, 0.0),
    })


# ----------------------------------------------------------------------------------
# 5. Build + persist
# ----------------------------------------------------------------------------------
def main():
    print("generating users ...")
    users = make_users()

    print("generating orders ...")
    orders = make_orders(users)

    print("generating app events ...")
    events = make_events(users, orders)

    print("generating experiment ...")
    exp = make_experiment(users, orders)

    users_out = users.drop(columns=["_affinity"])
    users_out["signup_date"] = users_out["signup_date"].dt.strftime("%Y-%m-%d")
    orders["order_ts"] = pd.to_datetime(orders["order_ts"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    events["event_ts"] = pd.to_datetime(events["event_ts"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    exp["assigned_ts"] = pd.to_datetime(exp["assigned_ts"]).dt.strftime("%Y-%m-%d %H:%M:%S")

    os.makedirs(DATA, exist_ok=True)
    users_out.to_csv(f"{DATA}/users.csv", index=False)
    orders.to_csv(f"{DATA}/orders.csv", index=False)
    events.to_csv(f"{DATA}/app_events.csv", index=False)
    exp.to_csv(f"{DATA}/ab_test_assignments.csv", index=False)

    db = f"{DATA}/delivery.db"
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    users_out.to_sql("users", con, index=False)
    orders.to_sql("orders", con, index=False)
    events.to_sql("app_events", con, index=False)
    exp.to_sql("ab_test_assignments", con, index=False)
    for stmt in [
        "CREATE INDEX idx_orders_user ON orders(user_id)",
        "CREATE INDEX idx_orders_ts ON orders(order_ts)",
        "CREATE INDEX idx_events_sess ON app_events(session_id)",
        "CREATE INDEX idx_events_name ON app_events(event_name)",
    ]:
        con.execute(stmt)
    con.commit()
    con.close()

    print(f"""
built OK
  users            {len(users_out):>9,}
  orders           {len(orders):>9,}
  app_events       {len(events):>9,}
  ab assignments   {len(exp):>9,}
  sqlite db        {db}
""")


if __name__ == "__main__":
    main()
