"""Rental yield and total return: does income change the houses-vs-units answer?"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import INK_2, MUTED, SEGMENT_COLORS, footer_note, load, money, style_fig, takeaway

st.title("Rental Yield & Total Return")
st.markdown('<p class="caption">Median weekly rent for new bonds lodged (NSW Department of Communities and Justice) '
            "against median sale prices, by postcode. Gross yields, before ownership costs and tax.</p>",
            unsafe_allow_html=True)

yields = load("yield_by_postcode")
total = load("total_return_by_segment")
rent = load("rent_by_postcode")

latest = yields[yields.year == yields.year.max()]
by_seg = latest.groupby("segment")["gross_yield_%"].median()
tr = total.set_index("segment")

k1, k2, k3, k4 = st.columns(4)
k1.metric("House gross yield", f"{by_seg['House']:.1f}%", f"{yields.year.max()} median postcode", delta_color="off")
k2.metric("Unit gross yield", f"{by_seg['Unit/Townhouse']:.1f}%", f"{yields.year.max()} median postcode",
          delta_color="off")
k3.metric("House total return", f"{tr.loc['House', 'total return after costs %']:.1f}%",
          "growth + net rent, a year", delta_color="off")
k4.metric("Unit total return", f"{tr.loc['Unit/Townhouse', 'total return after costs %']:.1f}%",
          "growth + net rent, a year", delta_color="off")

st.divider()
st.subheader("Does rental income close the gap between houses and units?")

fig = go.Figure()
for seg in ["Unit/Townhouse", "House"]:
    r = tr.loc[seg]
    fig.add_trace(go.Bar(y=[seg], x=[r["capital growth %"]], orientation="h", name="Capital growth",
                         marker_color=SEGMENT_COLORS[seg], showlegend=seg == "House", legendgroup="growth",
                         hovertemplate="capital growth %{x:.2f}%<extra></extra>"))
    fig.add_trace(go.Bar(y=[seg], x=[r["gross yield %"] * 0.75], orientation="h",
                         name="Rental income after costs", marker_color=SEGMENT_COLORS[seg], marker_opacity=0.45,
                         showlegend=seg == "House", legendgroup="rent",
                         hovertemplate="net rent %{x:.2f}%<extra></extra>"))
    fig.add_annotation(x=r["total return after costs %"], y=seg,
                       text=f"  <b>{r['total return after costs %']:.1f}%</b>", showarrow=False,
                       xanchor="left", font=dict(size=14, color=INK_2))
fig.update_layout(barmode="stack", hovermode="y unified")
fig.add_vline(x=3.14, line=dict(color="#0b0b0b", width=1.4, dash="dot"),
              annotation_text="inflation", annotation_font=dict(size=11, color=INK_2))
fig.update_xaxes(range=[0, tr["total return after costs %"].max() * 1.3], ticksuffix="%")
st.plotly_chart(style_fig(fig, 300, xlabel="Annual total return, 2017–2023"), use_container_width=True)

takeaway(
    "<b>No. Income narrows the gap by about a third, then houses still win by 3.4 points a year.</b> "
    "Units earn about 1 point more rent, but houses gained 4.1 points more in capital growth. After inflation, "
    "houses returned 4.8% a year and units 1.5%."
)

st.divider()
c1, c2 = st.columns(2)

with c1:
    st.subheader("Yields through the cycle")
    series = yields.groupby(["year", "segment"])["gross_yield_%"].median().reset_index()
    fig = go.Figure()
    for seg in SEGMENT_COLORS:
        d = series[series.segment == seg]
        fig.add_trace(go.Scatter(x=d.year, y=d["gross_yield_%"], name=seg, mode="lines+markers",
                                 line=dict(color=SEGMENT_COLORS[seg], width=2.6), marker=dict(size=8),
                                 hovertemplate="%{y:.2f}%<extra>" + seg + "</extra>"))
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(style_fig(fig, 330, ylabel="Gross yield"), use_container_width=True)
    st.markdown('<p class="caption">Yields bottomed in 2022 when prices peaked, then jumped as rents rose about '
                "25% in a year.</p>", unsafe_allow_html=True)

with c2:
    st.subheader("Income vs price")
    fig = go.Figure()
    for seg in SEGMENT_COLORS:
        d = latest[latest.segment == seg]
        fig.add_trace(go.Scatter(x=d.median_price, y=d["gross_yield_%"], mode="markers", name=seg,
                                 marker=dict(size=8, color=SEGMENT_COLORS[seg], opacity=0.75,
                                             line=dict(width=0.6, color="white")),
                                 text=d.main_suburb, customdata=d.median_weekly_rent,
                                 hovertemplate="<b>%{text}</b><br>yield %{y:.2f}%<br>rent $%{customdata:,.0f}/wk"
                                               "<br>median $%{x:,.0f}<extra></extra>"))
    fig.update_xaxes(type="log", tickvals=[5e5, 1e6, 2e6, 4e6, 8e6],
                     ticktext=["$500k", "$1M", "$2M", "$4M", "$8M"])
    fig.update_yaxes(ticksuffix="%")
    fig.update_layout(hovermode="closest")
    st.plotly_chart(style_fig(fig, 330, ylabel="Gross yield", xlabel="Median sale price (log scale)"),
                    use_container_width=True)
    st.markdown('<p class="caption">The cheaper the postcode, the higher the income. For houses that trade-off is '
                "priced fairly; for units the high-yield end gave up more growth than it paid in rent.</p>",
                unsafe_allow_html=True)

st.divider()
st.subheader("Yield by postcode")
seg = st.radio("Dwelling type", list(SEGMENT_COLORS), horizontal=True, label_visibility="collapsed")
table = (latest[latest.segment == seg].sort_values("gross_yield_%", ascending=False)
         [["main_suburb", "post_code", "median_weekly_rent", "median_price", "gross_yield_%", "sales"]])
st.dataframe(
    table.rename(columns={"main_suburb": "Main suburb", "post_code": "Postcode",
                          "median_weekly_rent": "Weekly rent", "median_price": "Median price",
                          "gross_yield_%": "Gross yield %", "sales": "Sales"}),
    hide_index=True, use_container_width=True, height=400,
    column_config={
        "Postcode": st.column_config.NumberColumn(format="%d"),
        "Weekly rent": st.column_config.NumberColumn(format="$%d"),
        "Median price": st.column_config.NumberColumn(format="$%,.0f"),
        "Gross yield %": st.column_config.NumberColumn(format="%.2f%%"),
    })

bed_rent = rent[(rent.year == rent.year.max())
                & rent.bedrooms.isin(["1 Bedroom", "2 Bedrooms", "3 Bedrooms", "4 or more Bedrooms"])]
ladder = bed_rent.groupby(["segment", "bedrooms"]).median_weekly_rent.median().unstack()
st.markdown("##### Median weekly rent by bedroom count")
st.dataframe(ladder.style.format("${:,.0f}"), use_container_width=True)

takeaway(
    "<b>4-bedroom houses are the income sweet spot.</b> A 4th bedroom adds only about 5% to a house's price "
    "(see Features &amp; Method) but roughly 28% to its rent. For units, stop at 3 bedrooms — 4-bedroom units rent "
    "for less than 3-bedroom ones."
)

footer_note()
