"""Suburb-level detail: growth, risk, value gap and price history."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import (BAD, GOOD, GRID, HOUSE, INK_2, MUTED, SEGMENT_COLORS, footer_note, load, money,
                 style_fig, takeaway)

st.title("Suburb Explorer")
st.markdown('<p class="caption">Like-for-like growth, risk and value for every suburb with enough repeat sales '
            "to measure (at least 100 pairs of the same dwelling sold twice).</p>", unsafe_allow_html=True)

growth = load("suburb_growth")
value = load("suburb_value_gap").set_index("suburb")
councils = load("council_risk_return")
history = load("suburb_annual_medians")
yields = load("yield_by_postcode")
suburb_pc = load("suburb_postcode").set_index("suburb")["post_code"]

c1, c2 = st.columns([1, 2])
segment = c1.selectbox("Dwelling type", list(SEGMENT_COLORS))
options = growth[growth.segment == segment].sort_values("rank")
suburb = c2.selectbox("Suburb", options.suburb, format_func=lambda s: f"{s}  (rank {int(options.set_index('suburb').loc[s, 'rank'])})")

row = options.set_index("suburb").loc[suburb]
colour = SEGMENT_COLORS[segment]
gap = value.loc[suburb, "value_gap_%"] if suburb in value.index and segment == "House" else None

postcode = suburb_pc.get(suburb)
yield_row = yields[(yields.year == yields.year.max()) & (yields.segment == segment)
                   & (yields.post_code == postcode)]
suburb_yield = yield_row["gross_yield_%"].iloc[0] if len(yield_row) else None

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Real growth a year", f"{row['real_cagr_%']:.1f}%", f"rank {int(row['rank'])} of {len(options)}",
          delta_color="off")
m2.metric("Median price 2023", money(row.median_2023), f"2014: {money(row.median_2014)}", delta_color="off")
m3.metric("Council", row.council, f"volatility {row['council_volatility_%']:.1f}%", delta_color="off")
m4.metric("Repeat-sale pairs", f"{int(row.pairs):,}", "sample behind the estimate", delta_color="off")
m5.metric("Value gap vs comparable areas", f"{gap:+.0f}%" if gap is not None else "–",
          "cheaper" if gap is not None and gap < 0 else ("dearer" if gap is not None else "houses only"),
          delta_color="off")
m6.metric("Gross rental yield", f"{suburb_yield:.1f}%" if suburb_yield is not None else "–",
          f"${int(yield_row.median_weekly_rent.iloc[0]):,}/wk in {int(postcode)}" if suburb_yield is not None
          else "no postcode-level rent", delta_color="off")

badges = []
if row.shortlist:
    badges.append(("Growth shortlist", GOOD, "Top-quartile growth in a low-volatility council"))
if gap is not None and value.loc[suburb, "value_candidate"]:
    badges.append(("Value candidate", HOUSE, "Above-median growth and priced 5%+ below comparable areas"))
if badges:
    st.markdown(" ".join(
        f'<span style="background:{c}1a; color:{c}; border:1px solid {c}55; padding:0.25rem 0.7rem; '
        f'border-radius:999px; font-size:0.85rem; margin-right:0.4rem;" title="{tip}">{label}</span>'
        for label, c, tip in badges), unsafe_allow_html=True)

st.divider()

left, right = st.columns([3, 2])
with left:
    st.subheader(f"Median price: {suburb} vs Sydney")
    h = history[(history.suburb == suburb) & (history.segment == segment)].sort_values("year")
    syd = history[history.segment == segment].groupby("year").median_price.median()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=syd.index, y=syd.values, name="Sydney (all suburbs)", mode="lines",
                             line=dict(color=MUTED, width=1.8, dash="dash"),
                             hovertemplate="$%{y:,.0f}<extra>Sydney</extra>"))
    fig.add_trace(go.Scatter(x=h.year, y=h.median_price, name=suburb, mode="lines+markers",
                             line=dict(color=colour, width=2.6), marker=dict(size=7),
                             customdata=h.sales, hovertemplate="$%{y:,.0f} · %{customdata} sales<extra></extra>"))
    fig.update_xaxes(dtick=1)
    st.plotly_chart(style_fig(fig, 380, ylabel="Median sale price"), use_container_width=True)
    st.markdown('<p class="caption">Annual medians (years with at least 5 sales). Medians bounce around in small '
                "suburbs — the growth figure above uses the repeat-sales method instead.</p>", unsafe_allow_html=True)

with right:
    st.subheader("How it compares")
    council_row = councils[(councils.segment == segment) & (councils.council == row.council)]
    bars = pd.DataFrame({
        "label": [suburb, f"{row.council} (council)", f"Sydney median suburb"],
        "value": [row["real_cagr_%"],
                  council_row["real_cagr_%"].iloc[0] if len(council_row) else float("nan"),
                  options["real_cagr_%"].median()],
    })
    fig = go.Figure(go.Bar(x=bars.value, y=bars.label, orientation="h",
                           marker_color=[colour, "#9ec5f4", "#c3c2b7"],
                           text=[f"{v:.1f}%" for v in bars.value], textposition="outside",
                           hovertemplate="%{y}: %{x:.1f}%<extra></extra>"))
    fig.update_layout(xaxis_range=[0, max(bars.value.max() * 1.35, 1)])
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(style_fig(fig, 220, legend=False, xlabel="Real growth a year, 2014–2023"),
                    use_container_width=True)

    st.markdown("##### Top 10 in this dwelling type")
    top = options.nsmallest(10, "rank")[["suburb", "real_cagr_%", "median_2023"]].copy()
    top["median_2023"] = top.median_2023.map(money)
    st.dataframe(top.rename(columns={"suburb": "Suburb", "real_cagr_%": "Real growth %", "median_2023": "Median 2023"}),
                 hide_index=True, use_container_width=True, height=390)

if gap is not None:
    context = (
        "A discount is a reason to investigate (flood and bushfire overlays, school catchments, transport projects), "
        "not proof of a bargain — the model cannot see those."
        if gap < 0 else
        "A premium usually reflects something the model cannot see: schools, views, a beach or a train line. "
        "It is not evidence the suburb is overpriced."
    )
    takeaway(
        f"<b>{suburb} prices {abs(gap):.0f}% {'below' if gap < 0 else 'above'} comparable areas.</b> The value model "
        "compares it with suburbs that have similar land sizes, distance to the CBD, incomes and location — never "
        f"with itself. {context}"
    )

footer_note()
