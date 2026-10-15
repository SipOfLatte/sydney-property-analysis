"""Sydney property dashboard — market overview (home page)."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import (BAD, GRID, HOUSE, INK_2, MUTED, SEGMENT_COLORS, UNIT, cpi_factor, footer_note,
                 load, money, style_fig, takeaway)


st.title("Sydney Residential Property, 2014–2023")
st.markdown(
    '<p class="caption">Prepared for a property investment fund · 881,664 Sydney metro sales from the NSW Valuer '
    "General · Growth measured like-for-like (the same dwelling sold twice), not by median price.</p>",
    unsafe_allow_html=True,
)

idx = load("sydney_index_quarterly")
annual = load("annual_market")
seasonality = load("seasonality")

factor = cpi_factor()
idx["real_index"] = idx.repeat_sales_index * idx.quarter.map(factor) / factor[idx.quarter.iloc[0]]

# ---------------------------------------------------------------- KPI row
house, unit = idx[idx.segment == "House"], idx[idx.segment == "Unit/Townhouse"]
k1, k2, k3, k4 = st.columns(4)
k1.metric("House growth 2014→2023", f"+{house.repeat_sales_index.iloc[-1] - 100:.0f}%",
          f"{house.real_index.iloc[-1] - 100:+.0f}% after inflation", delta_color="off")
k2.metric("Unit growth 2014→2023", f"+{unit.repeat_sales_index.iloc[-1] - 100:.0f}%",
          f"{unit.real_index.iloc[-1] - 100:+.0f}% after inflation", delta_color="off")
k3.metric("COVID boom (2019 → 2021 peak)", "+52%", "houses, like-for-like", delta_color="off")
k4.metric("Cheapest month to buy", "January", "−3% like-for-like, half the listings", delta_color="off")

st.divider()

# ---------------------------------------------------------------- Index chart
left, right = st.columns([3, 1])
with right:
    st.markdown("##### Chart options")
    segments = st.multiselect("Dwelling type", list(SEGMENT_COLORS), default=list(SEGMENT_COLORS))
    basis = st.radio("Prices shown in", ["Nominal", "After inflation (real)"], index=0)
    show_median = st.checkbox("Compare with median price", value=True,
                              help="The median tracks what sold. New, cheaper stock drags it down, so it understates "
                                   "what an existing owner's property gained.")

with left:
    st.subheader("Price index, 2014 Q1 = 100")
    fig = go.Figure()
    col = "real_index" if basis.startswith("After") else "repeat_sales_index"
    for seg in segments:
        d = idx[idx.segment == seg]
        x = pd.PeriodIndex(d.quarter, freq="Q").to_timestamp()
        if show_median and basis == "Nominal":
            fig.add_trace(go.Scatter(x=x, y=d.median_index, name=f"{seg} — median price", mode="lines",
                                     line=dict(color=MUTED, width=1.6, dash="dash"),
                                     hovertemplate="%{y:.0f}<extra>median</extra>"))
        fig.add_trace(go.Scatter(x=x, y=d[col], name=f"{seg} — like-for-like", mode="lines",
                                 line=dict(color=SEGMENT_COLORS[seg], width=2.6),
                                 hovertemplate="%{y:.0f}<extra>" + seg + "</extra>"))
    fig.add_hline(y=100, line=dict(color=GRID, width=1))
    for q, label in [("2017Q3", "2017 peak"), ("2019Q1", "2019 trough"), ("2022Q1", "2021–22 peak")]:
        fig.add_vline(x=pd.Period(q, "Q").start_time, line=dict(color=GRID, width=1, dash="dot"),
                      annotation_text=label, annotation_font=dict(size=11, color=MUTED), annotation_position="top")
    st.plotly_chart(style_fig(fig, 430, ylabel="Index (2014 Q1 = 100)"), use_container_width=True)

takeaway(
    "<b>Medians understate growth by about 20 points.</b> Like-for-like, houses rose 112% and units 52% over the decade. "
    "Both downturns (2017–19 and 2022) took only about 6–10% off prices, while the COVID boom added 52% to houses."
)

st.divider()

# ---------------------------------------------------------------- Annual + seasonality
c1, c2 = st.columns(2)
with c1:
    st.subheader("Year-on-year change in the median")
    yoy = annual.dropna(subset=["yoy_nominal_%"])
    fig = go.Figure(go.Bar(x=yoy.year, y=yoy["yoy_nominal_%"],
                           marker_color=np.where(yoy["yoy_nominal_%"] >= 0, HOUSE, BAD),
                           hovertemplate="%{x}: %{y:+.1f}%<extra></extra>"))
    fig.update_xaxes(dtick=1)
    st.plotly_chart(style_fig(fig, 330, legend=False, ylabel="% change"), use_container_width=True)
    st.markdown('<p class="caption">All dwellings, nominal median. Volume turned before price at both '
                "turning points.</p>", unsafe_allow_html=True)

with c2:
    st.subheader("Best time of year to buy")
    metric = st.radio("Show", ["Price effect", "Sales volume"], index=0, horizontal=True, label_visibility="collapsed")
    s = seasonality.sort_values("month_num")
    fig = go.Figure()
    if metric == "Price effect":
        for seg in SEGMENT_COLORS:
            d = s[s.segment == seg]
            fig.add_trace(go.Bar(x=d.month, y=d["price_effect_%"], name=seg, marker_color=SEGMENT_COLORS[seg],
                                 hovertemplate="%{x}: %{y:+.1f}%<extra>" + seg + "</extra>"))
        ylab = "% vs a typical month"
    else:
        d = s[s.segment == "House"]
        fig.add_trace(go.Bar(x=d.month, y=d["volume_effect_%"], name="All dwellings",
                             marker_color=np.where(d["volume_effect_%"] >= 0, HOUSE, BAD),
                             hovertemplate="%{x}: %{y:+.0f}%<extra></extra>"))
        ylab = "% vs a typical month"
    st.plotly_chart(style_fig(fig, 330, legend=metric == "Price effect", ylabel=ylab), use_container_width=True)
    st.markdown('<p class="caption">Like-for-like seasonal effect: suburb-adjusted and with the within-year trend '
                "removed. Raw January medians look 21% lower, but that is mostly which homes sell.</p>",
                unsafe_allow_html=True)

takeaway(
    "<b>Timing the cycle matters about ten times more than timing the month.</b> Cycles moved prices 10–52%; "
    "the January discount is about 3%, and comes with half the usual choice of listings."
)

footer_note()
