"""
run_analysis.py — runs every analysis, writes charts to charts/ and a machine-readable
results file to reports/results.json (which the README, the exec summary and the
Streamlit dashboard all read, so no number is ever hand-copied and stale).

Run:  python3 src/run_analysis.py
"""

import json
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from scipy import stats

from sqlkit import connect, HERE

CHARTS = os.path.join(HERE, "charts")
REPORTS = os.path.join(HERE, "reports")
os.makedirs(CHARTS, exist_ok=True)
os.makedirs(REPORTS, exist_ok=True)

# ---------------------------------------------------------------------------------
# Chart styling — one place, so every chart looks like it came from the same deck.
# ---------------------------------------------------------------------------------
RED, DARK, GREY, GREEN, AMBER = "#E23744", "#1C1C1C", "#8E8E93", "#2E9E5B", "#E8A33D"
CMAP = LinearSegmentedColormap.from_list("zom", ["#FDECEE", "#F4A0A8", RED, "#8E1620"])

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "savefig.bbox": "tight",
    "font.size": 10, "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.labelcolor": DARK, "text.color": DARK,
    "axes.edgecolor": "#DDDDDD", "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": GREY, "ytick.color": GREY,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.grid": True, "grid.color": "#EEEEEE", "grid.linewidth": 0.8,
})


def save(fig, name):
    path = os.path.join(CHARTS, name)
    fig.savefig(path)
    plt.close(fig)
    print(f"  chart -> charts/{name}")


def subtitle(ax, title, sub):
    """Title + a plain-English 'so what' line under it. Every chart makes a claim."""
    ax.set_title(title, loc="left", pad=22)
    ax.text(0, 1.035, sub, transform=ax.transAxes, fontsize=9.5, color=GREY, va="bottom")


R = {}          # results dict -> reports/results.json


def main():
    a = connect()

    # =============================================================================
    # 1. HEADLINE METRICS
    # =============================================================================
    print("\n[1] headline metrics")
    head = a.q("headline").iloc[0]
    ns = a.q("north_star").iloc[0]
    R["headline"] = head.to_dict()
    R["north_star"] = ns.to_dict()
    print(head.to_string())
    print(ns.to_string())

    trend = a.q("monthly_trend")
    R["monthly_trend"] = trend.to_dict("records")

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax1.bar(trend["month"], trend["orders"], color=RED, alpha=.85, label="Orders")
    ax1.set_ylabel("Orders")
    ax2 = ax1.twinx()
    ax2.plot(trend["month"], trend["late_rate_pct"], color=DARK, marker="o", lw=2,
             label="Late-delivery rate %")
    ax2.set_ylabel("Late-delivery rate (%)")
    ax2.grid(False)
    subtitle(ax1, "Orders are growing — but so is the late-delivery rate",
             "Monthly delivered orders (bars) vs share delivered >10 min past ETA (line)")
    fig.legend(loc="upper left", bbox_to_anchor=(0.12, 0.86), frameon=False, fontsize=9)
    save(fig, "01_monthly_trend.png")

    # =============================================================================
    # 2. COHORT RETENTION
    # =============================================================================
    print("\n[2] cohort retention")
    cm = a.q("cohort_matrix")
    piv = cm.pivot(index="cohort_month", columns="period_index", values="retention_pct")
    sizes = cm.groupby("cohort_month")["cohort_size"].first()
    R["cohort_matrix"] = piv.round(1).fillna(0).to_dict()
    R["cohort_sizes"] = sizes.to_dict()
    print(piv.round(1).to_string())

    fig, ax = plt.subplots(figsize=(8, 4.2))
    data = piv.to_numpy(dtype=float)
    im = ax.imshow(np.ma.masked_invalid(data), cmap=CMAP, aspect="auto", vmin=0, vmax=45)
    ax.set_xticks(range(piv.shape[1]))
    ax.set_xticklabels([f"M{c}" for c in piv.columns])
    ax.set_yticks(range(piv.shape[0]))
    ax.set_yticklabels([f"{m}  (n={sizes[m]:,})" for m in piv.index])
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            v = data[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8.5,
                        color="white" if v > 55 else DARK)
    ax.grid(False)
    subtitle(ax, "Retention collapses after the first month — and is not improving",
             "% of each first-order cohort that ordered again in month M+k")
    fig.colorbar(im, ax=ax, shrink=.85, label="% retained")
    save(fig, "02_cohort_heatmap.png")

    # retention curve split by first-delivery experience
    cbl = a.q("cohort_by_late")
    R["cohort_by_late"] = cbl.to_dict("records")
    fig, ax = plt.subplots(figsize=(7.2, 4))
    for seg, colr in [("First delivery ON TIME", GREEN), ("First delivery LATE", RED)]:
        d = cbl[cbl["segment"] == seg]
        ax.plot(d["period_index"], d["retention_pct"], marker="o", lw=2.4, color=colr,
                label=f"{seg}  (n={int(d['cohort_size'].iloc[0]):,})")
    ax.set_xlabel("Months since first order")
    ax.set_ylabel("% still ordering")
    ax.legend(frameon=False)
    subtitle(ax, "One late first delivery permanently lowers the retention curve",
             "Retention by whether the user's very first order arrived >10 min past ETA")
    save(fig, "03_retention_by_first_delivery.png")

    # =============================================================================
    # 3. FUNNEL
    # =============================================================================
    print("\n[3] funnel")
    fun = a.q("funnel_overall")
    R["funnel_overall"] = fun.to_dict("records")
    print(fun.to_string(index=False))

    fig, ax = plt.subplots(figsize=(8, 4.2))
    labels = [f"{r.event_name}" for r in fun.itertuples()]
    y = np.arange(len(fun))[::-1]
    ax.barh(y, fun["pct_of_top"], color=[RED if s == "payment_success" else "#F0C3C7"
                                         for s in fun["event_name"]], height=.62)
    for i, r in enumerate(fun.itertuples()):
        yy = y[i]
        ax.text(r.pct_of_top + 1.2, yy, f"{r.sessions:,}  ({r.pct_of_top:.0f}%)",
                va="center", fontsize=9)
        if not np.isnan(r.step_conv_pct):
            ax.text(1.5, yy + .42, f"↓ {r.step_conv_pct:.0f}% step conversion "
                                   f"({r.step_dropoff_pct:.0f}% drop)",
                    fontsize=8.2, color=GREY)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.set_xlim(0, 118); ax.set_xlabel("% of sessions that opened the app")
    subtitle(ax, "The biggest leak is checkout → payment",
             "Session funnel, all users, Jan–Jun 2026")
    save(fig, "04_funnel.png")

    fbp = a.q("funnel_by_platform")
    R["funnel_by_platform"] = fbp.to_dict("records")
    leak = a.q("payment_leak_size").iloc[0]
    R["payment_leak"] = leak.to_dict()
    print(leak.to_string())

    fig, ax = plt.subplots(figsize=(7.6, 4))
    w = .38
    for k, (plat, colr) in enumerate([("Android", RED), ("iOS", DARK)]):
        d = fbp[fbp["platform"] == plat].sort_values("step_no")
        x = np.arange(len(d)) + (k - .5) * w
        ax.bar(x, d["step_conv_pct"].fillna(100), width=w, color=colr, label=plat)
    d = fbp[fbp["platform"] == "Android"].sort_values("step_no")
    ax.set_xticks(np.arange(len(d)))
    ax.set_xticklabels(d["event_name"], rotation=18, ha="right")
    ax.set_ylabel("Step conversion %")
    ax.legend(frameon=False)
    subtitle(ax, f"Android loses {leak.ios_pay_conv_pct - leak.android_pay_conv_pct:.0f}pp "
                 f"at the payment step vs iOS",
             "Step-to-step conversion by platform — the gap is isolated to one step, "
             "which points to a bug, not to user intent")
    save(fig, "05_funnel_by_platform.png")

    # =============================================================================
    # 4. SEGMENTATION
    # =============================================================================
    print("\n[4] RFM segmentation")
    rfm = a.q("rfm_summary")
    R["rfm_summary"] = rfm.to_dict("records")
    print(rfm.to_string(index=False))

    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    o = rfm.sort_values("pct_gmv")
    yy = np.arange(len(o))
    ax.barh(yy - .19, o["pct_users"], height=.36, color="#C9CBD1", label="% of users")
    ax.barh(yy + .19, o["pct_gmv"], height=.36, color=RED, label="% of GMV")
    ax.set_yticks(yy); ax.set_yticklabels(o["segment"])
    ax.set_xlabel("%")
    ax.legend(frameon=False)
    for i, r in enumerate(o.itertuples()):
        ax.text(r.pct_gmv + .6, i + .19, f"{r.pct_gmv:.0f}%", va="center", fontsize=8.5)
    subtitle(ax, "A small Champions segment carries a disproportionate share of GMV",
             "RFM segments — share of users vs share of GMV")
    save(fig, "06_rfm_segments.png")

    chan = a.q("behaviour_by_channel")
    R["behaviour_by_channel"] = chan.to_dict("records")
    print(chan.to_string(index=False))

    # =============================================================================
    # 5. DRIVERS OF THE SECOND ORDER
    # =============================================================================
    print("\n[5] drivers")
    rbl = a.q("repeat_by_late")
    strat = a.q("repeat_by_late_stratified").iloc[0]
    dose = a.q("dose_response")
    seg = a.q("repeat_by_segment")
    R["repeat_by_late"] = rbl.to_dict("records")
    R["stratified"] = strat.to_dict()
    R["dose_response"] = dose.to_dict("records")
    R["repeat_by_segment"] = seg.to_dict("records")
    print(rbl.to_string(index=False))
    print(strat.to_string())
    print(dose.to_string(index=False))

    raw_gap = (rbl[rbl.first_delivery == "On time"].repeat_30d_pct.iloc[0]
               - rbl[rbl.first_delivery == "Late"].repeat_30d_pct.iloc[0])
    R["raw_gap_pp"] = round(float(raw_gap), 2)

    # significance of the raw gap (two-proportion z-test)
    n_on = int(rbl[rbl.first_delivery == "On time"].users.iloc[0])
    n_la = int(rbl[rbl.first_delivery == "Late"].users.iloc[0])
    x_on = round(n_on * rbl[rbl.first_delivery == "On time"].repeat_30d_pct.iloc[0] / 100)
    x_la = round(n_la * rbl[rbl.first_delivery == "Late"].repeat_30d_pct.iloc[0] / 100)
    z, p = two_prop_z(x_la, n_la, x_on, n_on)
    R["late_gap_pvalue"] = p

    fig, ax = plt.subplots(figsize=(7.4, 4))
    ax.plot(dose["lateness_bucket"], dose["repeat_30d_pct"], marker="o", lw=2.6, color=RED)
    for r in dose.itertuples():
        ax.annotate(f"{r.repeat_30d_pct:.1f}%", (r.lateness_bucket, r.repeat_30d_pct),
                    textcoords="offset points", xytext=(0, 9), ha="center", fontsize=9)
        ax.annotate(f"n={r.users:,}", (r.lateness_bucket, r.repeat_30d_pct),
                    textcoords="offset points", xytext=(0, -16), ha="center",
                    fontsize=8, color=GREY)
    ax.set_ylabel("30-day repeat rate (%)")
    ax.tick_params(axis="x", labelrotation=12)
    subtitle(ax, "Dose–response: every extra 10 minutes late costs repeat orders",
             "The monotone slope is why we treat this as causal, not just correlated")
    save(fig, "07_dose_response.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    s = seg.copy()
    s["label"] = s["dimension"] + " · " + s["value"]
    s = s.sort_values("repeat_pct")
    base = float(ns.repeat_30d_rate_pct)
    cols = [GREEN if v > base else RED for v in s["repeat_pct"]]
    ax.barh(s["label"], s["repeat_pct"] - base, left=base, color=cols, height=.65)
    ax.axvline(base, color=DARK, lw=1.4)
    ax.text(base, len(s) - .2, f" overall {base:.1f}%", fontsize=8.5, color=DARK)
    ax.set_xlabel("30-day repeat rate (%)")
    subtitle(ax, "Which user groups repeat, and which don't",
             "Deviation from the overall 30-day repeat rate, by dimension")
    save(fig, "08_repeat_by_segment.png")

    lch = a.q("late_by_city_hour")
    R["late_by_city_hour"] = lch.to_dict("records")
    pv = lch.pivot(index="city", columns="daypart", values="late_rate_pct")
    pv = pv[["Off peak", "Lunch peak", "Dinner peak"]].sort_values("Dinner peak", ascending=False)
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    im = ax.imshow(pv.to_numpy(), cmap=CMAP, aspect="auto")
    ax.set_xticks(range(3)); ax.set_xticklabels(pv.columns)
    ax.set_yticks(range(len(pv))); ax.set_yticklabels(pv.index)
    for i in range(pv.shape[0]):
        for j in range(pv.shape[1]):
            v = pv.to_numpy()[i, j]
            ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=9,
                    color="white" if v > 30 else DARK)
    ax.grid(False)
    subtitle(ax, "Lateness is concentrated, not spread evenly",
             "Late-delivery rate by city × daypart — where Ops should be pointed first")
    save(fig, "09_late_heatmap.png")

    # =============================================================================
    # 6. A/B TEST
    # =============================================================================
    print("\n[6] A/B test")
    srm = a.q("srm_check")
    bal = a.q("ab_balance")
    prim = a.q("ab_primary")
    grd = a.q("ab_guardrails")
    hte = a.q("ab_by_segment")
    R["ab_srm"] = srm.to_dict("records")
    R["ab_balance"] = bal.to_dict("records")
    R["ab_primary"] = prim.to_dict("records")
    R["ab_guardrails"] = grd.to_dict("records")
    R["ab_by_segment"] = hte.to_dict("records")

    c = prim[prim.variant == "control"].iloc[0]
    t = prim[prim.variant == "treatment"].iloc[0]
    ab = ab_readout(int(t.conversions), int(t.n), int(c.conversions), int(c.n))
    R["ab_stats"] = ab
    for k, v in ab.items():
        print(f"  {k:>26}: {v}")

    # SRM chi-square
    obs = srm.set_index("variant")["users"]
    chi2, p_srm = stats.chisquare([obs["control"], obs["treatment"]])[:2]
    R["ab_srm_pvalue"] = float(p_srm)
    print(f"  {'SRM chi-square p':>26}: {p_srm:.3f} "
          f"({'PASS' if p_srm > 0.01 else 'FAIL — do not trust this test'})")

    fig, ax = plt.subplots(figsize=(6.6, 4))
    xs = ["Control", "Treatment"]
    vals = [ab["control_rate_pct"], ab["treatment_rate_pct"]]
    errs = [1.96 * ab["se_control_pct"], 1.96 * ab["se_treatment_pct"]]
    ax.bar(xs, vals, color=[GREY, RED], width=.5,
           yerr=errs, capsize=8, ecolor=DARK)
    for i, v in enumerate(vals):
        ax.text(i, v + errs[i] + .35, f"{v:.2f}%", ha="center", fontweight="bold")
    ax.set_ylabel("Repeat order within 14 days (%)")
    ax.set_ylim(0, max(vals) * 1.45)
    subtitle(ax, f"Next-Order Nudge: +{ab['abs_lift_pp']:.2f}pp "
                 f"({ab['rel_lift_pct']:.1f}% relative), p {ab['p_value_str']}",
             f"95% CI on the absolute lift: [{ab['ci_low_pp']:.2f}pp, {ab['ci_high_pp']:.2f}pp] · "
             f"n = {int(t.n):,} vs {int(c.n):,}")
    save(fig, "10_ab_test.png")

    # heterogeneous effect chart
    fig, ax = plt.subplots(figsize=(7.2, 4))
    segs = hte["segment"].unique()
    w = .36
    for k, (var, colr) in enumerate([("control", GREY), ("treatment", RED)]):
        d = hte[hte.variant == var].set_index("segment").loc[segs]
        ax.bar(np.arange(len(segs)) + (k - .5) * w, d["repeat_14d_pct"], width=w,
               color=colr, label=var.title())
    ax.set_xticks(range(len(segs))); ax.set_xticklabels(segs)
    ax.set_ylabel("Repeat within 14 days (%)")
    ax.legend(frameon=False)
    subtitle(ax, "The nudge helps both groups — it does not repair a bad delivery",
             "Treatment effect split by first-delivery experience")
    save(fig, "11_ab_by_segment.png")

    # =============================================================================
    # 7. IMPACT MODEL — turn findings into rupees, with assumptions stated
    # =============================================================================
    print("\n[7] impact model")
    impact = impact_model(a, R)
    R["impact"] = impact
    for k, v in impact.items():
        print(f"  {k:>34}: {v}")

    fig, ax = plt.subplots(figsize=(7.6, 4))
    names = ["Fix Android\npayment step", "Cut late deliveries\n(worst city × daypart)",
             "Ship Next-Order\nNudge"]
    vals = [impact["android_fix_gmv_lakh_yr"], impact["lateness_fix_gmv_lakh_yr"],
            impact["nudge_net_gmv_lakh_yr"]]
    order = np.argsort(vals)
    ax.barh([names[i] for i in order], [vals[i] for i in order], color=RED, height=.6)
    for i, v in enumerate([vals[i] for i in order]):
        ax.text(v + max(vals) * .015, i, f"₹{v:.0f}L / yr", va="center", fontweight="bold")
    ax.set_xlabel("Estimated incremental GMV (₹ lakh per year)")
    ax.set_xlim(0, max(vals) * 1.25)
    subtitle(ax, "Ranked by expected annual GMV impact",
             "Assumptions are listed in the executive summary — all are conservative")
    save(fig, "12_impact.png")

    a.close()
    with open(os.path.join(REPORTS, "results.json"), "w") as f:
        json.dump(R, f, indent=2, default=to_native)
    print("\nwrote reports/results.json")


# ---------------------------------------------------------------------------------
# statistics helpers
# ---------------------------------------------------------------------------------
def two_prop_z(x1, n1, x2, n2):
    """Two-proportion z-test (pooled). Returns (z, two-sided p)."""
    p1, p2 = x1 / n1, x2 / n2
    p_pool = (x1 + x2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    z = (p1 - p2) / se
    return float(z), float(2 * (1 - stats.norm.cdf(abs(z))))


def sample_size_per_arm(p_base, mde_abs, alpha=0.05, power=0.80):
    """Minimum users PER ARM to detect an absolute lift `mde_abs` on a base rate."""
    z_a = stats.norm.ppf(1 - alpha / 2)
    z_b = stats.norm.ppf(power)
    p2 = p_base + mde_abs
    p_bar = (p_base + p2) / 2
    n = ((z_a * np.sqrt(2 * p_bar * (1 - p_bar)) +
          z_b * np.sqrt(p_base * (1 - p_base) + p2 * (1 - p2))) ** 2) / (mde_abs ** 2)
    return int(np.ceil(n))


def ab_readout(x_t, n_t, x_c, n_c, alpha=0.05):
    p_t, p_c = x_t / n_t, x_c / n_c
    se_t, se_c = np.sqrt(p_t * (1 - p_t) / n_t), np.sqrt(p_c * (1 - p_c) / n_c)
    diff = p_t - p_c
    se_diff = np.sqrt(se_t ** 2 + se_c ** 2)                 # unpooled, for the CI
    z_crit = stats.norm.ppf(1 - alpha / 2)
    z, p = two_prop_z(x_t, n_t, x_c, n_c)
    return {
        "control_n": n_c, "treatment_n": n_t,
        "control_rate_pct": round(100 * p_c, 3),
        "treatment_rate_pct": round(100 * p_t, 3),
        "se_control_pct": round(100 * se_c, 3),
        "se_treatment_pct": round(100 * se_t, 3),
        "abs_lift_pp": round(100 * diff, 3),
        "rel_lift_pct": round(100 * diff / p_c, 2),
        "ci_low_pp": round(100 * (diff - z_crit * se_diff), 3),
        "ci_high_pp": round(100 * (diff + z_crit * se_diff), 3),
        "z_stat": round(z, 3),
        "p_value": float(p),
        # p can underflow to exactly 0.0 in float; never print "p = 0" in a report
        "p_value_str": ("< 0.0001" if p < 1e-4 else f"{p:.4f}"),
        "significant_at_5pct": bool(p < alpha),
        # what we PLANNED before looking at data: powered for a +2.0pp MDE
        "planned_mde_pp": 2.0,
        "required_n_per_arm": sample_size_per_arm(p_c, 0.02),
        "actual_min_n_per_arm": min(n_c, n_t),
        "powered": bool(min(n_c, n_t) >= sample_size_per_arm(p_c, 0.02)),
    }


def impact_model(a, R):
    """
    Translate each finding into annual incremental GMV.
    EVERY assumption is explicit and conservative — an interviewer will poke at these,
    so they must be defensible, not optimistic.
    """
    head = R["headline"]
    aov = float(head["aov"])
    months = 6.0                                # observation window

    # ---- 1. Android payment fix -------------------------------------------------
    # Assume closing HALF the Android-vs-iOS payment-step gap is achievable in one
    # release (conservative: a payment SDK fix rarely reaches full parity).
    recoverable = float(R["payment_leak"]["recoverable_orders_6mo"])
    android_orders_yr = recoverable * 0.5 * (12 / months)
    android_gmv = android_orders_yr * aov

    # ---- 2. Lateness reduction ---------------------------------------------------
    # Ops target: cut the OVERALL late rate by 6pp (e.g. 21% -> 15%) by adding rider
    # capacity and widening promised ETAs in the worst city x daypart cells.
    # Effect size = the STRATIFIED (confounder-adjusted) gap, not the raw gap.
    adj_gap = float(R["stratified"]["adjusted_gap_pp"]) / 100.0
    lch = pd.DataFrame(R["late_by_city_hour"])
    worst = lch.sort_values("late_rate_pct", ascending=False).head(2)
    LATE_RATE_REDUCTION = 0.06
    new_first_orders_yr = float(R["north_star"]["matured_new_users"]) * (12 / months)
    users_saved_yr = new_first_orders_yr * LATE_RATE_REDUCTION * adj_gap
    # A saved user is worth their *incremental* orders, not one order. We measure that
    # from the data rather than guessing: among users who did place a 2nd order, how
    # many orders beyond the first did they place? (Right-censored, so it is an
    # under-estimate — which keeps the impact number conservative.)
    orders_per_retained_user = float(a.raw("""
        WITH per_user AS (
            SELECT user_id, COUNT(*) AS n FROM orders
            WHERE status='delivered' GROUP BY user_id
        )
        SELECT ROUND(AVG(n - 1.0), 2) AS extra_orders FROM per_user WHERE n > 1
    """).iloc[0, 0])
    lateness_gmv = users_saved_yr * orders_per_retained_user * aov

    # ---- 3. Next-Order Nudge -----------------------------------------------------
    ab = R["ab_stats"]
    lift = ab["abs_lift_pp"] / 100.0
    new_users_yr = float(R["north_star"]["matured_new_users"]) * (12 / months)
    incr_users_yr = new_users_yr * lift
    gross = incr_users_yr * orders_per_retained_user * aov
    # cost: ₹75 coupon paid to EVERY treated user who repeats, not just incremental ones
    grd = pd.DataFrame(R["ab_guardrails"])
    treat_repeat_rate = ab["treatment_rate_pct"] / 100.0
    coupon_cost_yr = new_users_yr * treat_repeat_rate * 75.0
    # guardrail cost: treated users trade DOWN on the 2nd order. That AOV loss applies
    # to every treated repeat order, not just the incremental ones — easy to forget,
    # and it is the difference between an honest ROI and a flattering one.
    aov_delta = (float(grd[grd.variant == "control"].second_order_aov.iloc[0])
                 - float(grd[grd.variant == "treatment"].second_order_aov.iloc[0]))
    aov_cost_yr = new_users_yr * treat_repeat_rate * aov_delta
    nudge_net = gross - coupon_cost_yr - aov_cost_yr

    L = 1e5                                  # 1 lakh
    return {
        "aov_used": round(aov),
        "orders_per_retained_user_measured": orders_per_retained_user,
        "android_recoverable_orders_6mo": round(recoverable),
        "android_fix_gmv_lakh_yr": round(android_gmv / L, 1),
        "adjusted_lateness_gap_pp": round(adj_gap * 100, 2),
        "lateness_late_rate_reduction_assumed_pp": 6.0,
        "lateness_worst_cells": worst[["city", "daypart", "late_rate_pct"]].to_dict("records"),
        "lateness_fix_users_saved_yr": round(users_saved_yr),
        "lateness_fix_gmv_lakh_yr": round(lateness_gmv / L, 1),
        "nudge_incremental_users_yr": round(incr_users_yr),
        "nudge_gross_gmv_lakh_yr": round(gross / L, 1),
        "nudge_coupon_cost_lakh_yr": round(coupon_cost_yr / L, 1),
        "nudge_aov_guardrail_cost_lakh_yr": round(aov_cost_yr / L, 1),
        "nudge_aov_delta_rupees": round(aov_delta, 1),
        "nudge_net_gmv_lakh_yr": round(nudge_net / L, 1),
        "total_gmv_lakh_yr": round((android_gmv + lateness_gmv + nudge_net) / L, 1),
    }


def to_native(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return str(o)
    return str(o)


if __name__ == "__main__":
    main()
