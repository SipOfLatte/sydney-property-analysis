"""Filterable screener: find suburbs that match the fund's criteria."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import (FAINT, GRID, HOUSE, INK_2, MUTED, SEGMENT_COLORS, UNIT, footer_note, load, money,
                 style_fig, takeaway)

st.title("Investment Screener")
st.markdown('<p class="caption">Filter every measured suburb by growth, risk, price and value gap. '
            "Export the result for your acquisition pipeline.</p>", unsafe_allow_html=True)

growth = load("suburb_growth")
value = load("suburb_value_gap")[["suburb", "value_gap_%", "median_price_2022_23", "value_candidate"]]
councils = load("council_risk_return")

with st.sidebar:
    st.header("Filters")
    segment = st.selectbox("Dwelling type", list(SEGMENT_COLORS))
    d = growth[growth.segment == segment].merge(value, on="suburb", how="left")

    budget = st.slider("Median price 2023 ($M)", 0.3, float(round(d.median_2023.max() / 1e6 + 0.5, 1)),
                       (0.3, float(round(d.median_2023.max() / 1e6 + 0.5, 1))), step=0.1)
    min_growth = st.slider("Minimum real growth a year (%)", float(round(d["real_cagr_%"].min(), 1)),
                           float(round(d["real_cagr_%"].max(), 1)), float(round(d["real_cagr_%"].median(), 1)), 0.1)
    max_vol = st.slider("Maximum council volatility (%)", float(round(d["council_volatility_%"].min(), 1)),
                        float(round(d["council_volatility_%"].max(), 1)),
                        float(round(d["council_volatility_%"].max(), 1)), 0.1)
    max_gap = st.slider("Maximum value gap (%)", -25, 40, 40, 1,
                        help="Negative means cheaper than comparable areas. Houses only — units have no value gap.")
    min_pairs = st.slider("Minimum repeat-sale pairs", 100, 800, 100, 10)
    council_filter = st.multiselect("Councils", sorted(d.council.unique()))
    only_flagged = st.checkbox("Growth shortlist only", value=False)

mask = (d.median_2023.between(budget[0] * 1e6, budget[1] * 1e6)
        & (d["real_cagr_%"] >= min_growth)
        & (d["council_volatility_%"] <= max_vol)
        & (d.pairs >= min_pairs)
        & (d["value_gap_%"].isna() | (d["value_gap_%"] <= max_gap)))
if council_filter:
    mask &= d.council.isin(council_filter)
if only_flagged:
    mask &= d.shortlist
res = d[mask].sort_values("real_cagr_%", ascending=False)

m1, m2, m3 = st.columns(3)
m1.metric("Suburbs matching", f"{len(res)}", f"of {len(d)} measured", delta_color="off")
m2.metric("Median growth of matches", f"{res['real_cagr_%'].median():.1f}%" if len(res) else "–",
          "real, a year", delta_color="off")
m3.metric("Median price of matches", money(res.median_2023.median()) if len(res) else "–", "2023", delta_color="off")

if not len(res):
    st.warning("No suburbs match these filters. Try widening the price range or lowering the growth threshold.")
    st.stop()

tab1, tab2 = st.tabs(["Growth vs value", "Risk vs return"])

with tab1:
    plot = res.dropna(subset=["value_gap_%"])
    if plot.empty:
        st.info("Value gaps are only modelled for houses. Switch the dwelling type to House to use this view.")
    else:
        fig = go.Figure()
        others = d.dropna(subset=["value_gap_%"])
        fig.add_trace(go.Scatter(x=others["value_gap_%"], y=others["real_cagr_%"], mode="markers",
                                 name="All suburbs", marker=dict(size=7, color=FAINT),
                                 text=others.suburb, hovertemplate="%{text}<extra></extra>"))
        fig.add_trace(go.Scatter(x=plot["value_gap_%"], y=plot["real_cagr_%"], mode="markers", name="Matches",
                                 marker=dict(size=11, color=SEGMENT_COLORS[segment],
                                             line=dict(width=1.4, color="white")),
                                 text=plot.suburb, customdata=plot.median_2023,
                                 hovertemplate="<b>%{text}</b><br>growth %{y:.1f}%/yr · value gap %{x:+.0f}%"
                                               "<br>median $%{customdata:,.0f}<extra></extra>"))
        fig.add_vline(x=0, line=dict(color=MUTED, width=1, dash="dot"))
        fig.update_xaxes(ticksuffix="%")
        fig.update_yaxes(ticksuffix="%")
        fig.update_layout(hovermode="closest")
        st.plotly_chart(style_fig(fig, 470, ylabel="Real growth a year, 2014–2023",
                                  xlabel="Value gap: price vs comparable areas (negative = cheaper)"),
                        use_container_width=True)
        st.markdown('<p class="caption">Top-left is the target zone: proven demand, still priced below comparable '
                    "areas. Cheap suburbs with weak growth are often cheap for a reason the model cannot see.</p>",
                    unsafe_allow_html=True)

with tab2:
    cdata = councils[councils.segment == segment]
    matched = set(res.council)
    fig = go.Figure()
    for inside, name, colr, size in [(False, "Other councils", FAINT, 9), (True, "Councils in results",
                                                                               SEGMENT_COLORS[segment], 14)]:
        sub = cdata[cdata.council.isin(matched) == inside]
        fig.add_trace(go.Scatter(x=sub["volatility_%"], y=sub["real_cagr_%"], mode="markers", name=name,
                                 marker=dict(size=size, color=colr, line=dict(width=1.2, color="white")),
                                 text=sub.council, customdata=sub["downturn_2017_19_%"],
                                 hovertemplate="<b>%{text}</b><br>growth %{y:.1f}%/yr · volatility %{x:.1f}%"
                                               "<br>2017–19 downturn %{customdata:+.1f}%<extra></extra>"))
    fig.add_vline(x=cdata["volatility_%"].median(), line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_hline(y=cdata["real_cagr_%"].median(), line=dict(color=MUTED, width=1, dash="dot"))
    fig.update_xaxes(ticksuffix="%")
    fig.update_yaxes(ticksuffix="%")
    fig.update_layout(hovermode="closest")
    st.plotly_chart(style_fig(fig, 470, ylabel="Real growth a year, 2014–2023",
                              xlabel="Volatility (noise-adjusted, % a year)"), use_container_width=True)
    st.markdown('<p class="caption">Risk is measured by council, where there are enough repeat sales to separate '
                "real volatility from sampling noise. Top-left = higher return with lower risk.</p>",
                unsafe_allow_html=True)

st.subheader("Matching suburbs")
table = res[["suburb", "council", "real_cagr_%", "value_gap_%", "median_2023", "pairs",
             "council_volatility_%", "shortlist"]].copy()
st.dataframe(
    table.rename(columns={"suburb": "Suburb", "council": "Council", "real_cagr_%": "Real growth %/yr",
                          "value_gap_%": "Value gap %", "median_2023": "Median 2023",
                          "pairs": "Pairs", "council_volatility_%": "Council volatility %",
                          "shortlist": "Shortlist"}),
    hide_index=True, use_container_width=True, height=430,
    column_config={
        "Median 2023": st.column_config.NumberColumn(format="$%,.0f"),
        "Real growth %/yr": st.column_config.NumberColumn(format="%.1f%%"),
        "Value gap %": st.column_config.NumberColumn(format="%+.0f%%"),
        "Council volatility %": st.column_config.NumberColumn(format="%.1f%%"),
        "Shortlist": st.column_config.CheckboxColumn(),
    })

st.download_button("Download these suburbs (CSV)", table.to_csv(index=False).encode(),
                   file_name=f"sydney_screener_{segment.replace('/', '_')}.csv", mime="text/csv")

takeaway(
    "<b>Use this as a due-diligence list, not a buy list.</b> The model cannot see flood or bushfire exposure, "
    "school catchments, planned transport or zoning changes. Check those before acting on any discount."
)

footer_note()
