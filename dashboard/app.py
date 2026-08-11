"""
Streamlit dashboard — the "self-serve" layer on top of the same SQL.

Run:  pip install streamlit && streamlit run dashboard/app.py

Design intent: a PM should be able to answer "how are we doing, and where is the
leak this month?" without asking an analyst. Every number comes from sql/*.sql via
sqlkit, so the dashboard can never disagree with the report.
"""

import os
import sys
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from sqlkit import connect, HERE  # noqa: E402

st.set_page_config(page_title="Food Delivery — Product Analytics", layout="wide",
                   page_icon="🍜")

RED = "#E23744"


@st.cache_resource
def get_conn():
    return connect()


@st.cache_data
def run(name):
    return get_conn().q(name)


st.markdown(f"""
<h1 style='margin-bottom:0'>The Second-Order Problem</h1>
<p style='color:#8E8E93;margin-top:4px;font-size:1.05rem'>
Why do new users not come back — and which fix is worth the most GMV?<br>
Simulated marketplace data, Jan–Jun 2026 · all figures generated from <code>sql/</code>
</p><hr>""", unsafe_allow_html=True)

head = run("headline").iloc[0]
ns = run("north_star").iloc[0]

c = st.columns(5)
c[0].metric("Registered users", f"{int(head.registered_users):,}")
c[1].metric("Orders (delivered)", f"{int(head.orders):,}")
c[2].metric("GMV", f"₹{head.gmv/1e7:.2f} Cr")
c[3].metric("AOV", f"₹{int(head.aov):,}")
c[4].metric("⭐ 30-day repeat rate", f"{ns.repeat_30d_rate_pct:.1f}%",
            help="NORTH STAR: share of new users who order again within 30 days "
                 "of their first order (matured cohorts only).")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📈 Health", "🔁 Retention", "🚰 Funnel", "👥 Segments", "🧪 Experiment"])

# ---------------------------------------------------------------- Health
with tab1:
    trend = run("monthly_trend")
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Monthly trend")
        st.bar_chart(trend.set_index("month")[["orders"]], color=RED, height=260)
        st.line_chart(trend.set_index("month")[["late_rate_pct", "discount_pct_of_gmv"]],
                      height=240)
    with right:
        st.subheader("Guardrails")
        st.dataframe(run("guardrails"), hide_index=True, use_container_width=True)
    st.caption("Orders are growing, but the late-delivery rate is rising with them — "
               "growth is being bought with a worse delivery experience.")

# ---------------------------------------------------------------- Retention
with tab2:
    st.subheader("Cohort retention (% of first-order cohort ordering in month M+k)")
    cm = run("cohort_matrix")
    piv = cm.pivot(index="cohort_month", columns="period_index", values="retention_pct")
    st.dataframe(piv.style.background_gradient(cmap="Reds", axis=None).format("{:.0f}"),
                 use_container_width=True)
    st.subheader("Retention by first-delivery experience")
    cbl = run("cohort_by_late")
    st.line_chart(cbl.pivot(index="period_index", columns="segment", values="retention_pct"),
                  height=300)
    st.subheader("Dose–response: repeat rate vs how late the first order was")
    st.dataframe(run("dose_response"), hide_index=True, use_container_width=True)

# ---------------------------------------------------------------- Funnel
with tab3:
    st.subheader("Session funnel")
    fun = run("funnel_overall")
    st.dataframe(fun, hide_index=True, use_container_width=True)
    st.subheader("By platform — where the leak actually is")
    fbp = run("funnel_by_platform")
    st.bar_chart(fbp.pivot(index="event_name", columns="platform", values="step_conv_pct"),
                 height=300)
    leak = run("payment_leak_size").iloc[0]
    st.error(f"**Android checkout→payment: {leak.android_pay_conv_pct}% vs iOS "
             f"{leak.ios_pay_conv_pct}%.** Every earlier step is identical across "
             f"platforms, which points to a payment-SDK defect rather than user intent. "
             f"Closing the gap is worth ~{int(leak.recoverable_orders_6mo):,} orders "
             f"over the 6-month window.")

# ---------------------------------------------------------------- Segments
with tab4:
    st.subheader("RFM segments")
    st.dataframe(run("rfm_summary"), hide_index=True, use_container_width=True)
    a, b = st.columns(2)
    with a:
        st.subheader("Acquisition-channel quality")
        st.dataframe(run("behaviour_by_channel"), hide_index=True, use_container_width=True)
    with b:
        st.subheader("Orders by hour of day")
        st.bar_chart(run("hour_of_day").set_index("hour")[["orders"]], color=RED, height=260)

# ---------------------------------------------------------------- Experiment
with tab5:
    st.subheader("Next-Order Nudge — ₹75 off the 2nd order, valid 7 days")
    srm = run("srm_check")
    prim = run("ab_primary")
    ctrl = prim[prim.variant == "control"].iloc[0]
    trt = prim[prim.variant == "treatment"].iloc[0]
    lift = trt.repeat_14d_pct - ctrl.repeat_14d_pct
    k = st.columns(4)
    k[0].metric("Control", f"{ctrl.repeat_14d_pct:.2f}%", f"n={int(ctrl.n):,}")
    k[1].metric("Treatment", f"{trt.repeat_14d_pct:.2f}%", f"n={int(trt.n):,}")
    k[2].metric("Absolute lift", f"+{lift:.2f} pp")
    k[3].metric("Relative lift", f"+{100*lift/ctrl.repeat_14d_pct:.1f}%")
    st.write("**Sample-ratio-mismatch check** (must be ~50/50 before reading anything else)")
    st.dataframe(srm, hide_index=True)
    st.write("**Guardrails**")
    st.dataframe(run("ab_guardrails"), hide_index=True, use_container_width=True)
    st.write("**Heterogeneous effect** — does the nudge work for everyone?")
    st.dataframe(run("ab_by_segment"), hide_index=True, use_container_width=True)
    st.info("Decision: **ship**, with the coupon targeted rather than blanket — see "
            "`reports/EXECUTIVE_SUMMARY.md` for the full ship/no-ship reasoning.")

st.markdown("---")
st.caption("Data is simulated with a documented causal structure "
           "(`src/generate_data.py`); the analysis techniques are production-standard.")
