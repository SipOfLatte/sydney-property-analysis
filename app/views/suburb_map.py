"""Map view: where the growth, the value and the income actually are, geographically."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import (FAINT, HOUSE, INK, INK_2, MUTED, SEGMENT_COLORS, SURFACE, UNIT, footer_note, load,
                 style_fig, takeaway)

st.title("Suburb Map")
st.markdown('<p class="caption">Every measured suburb, placed at its centre point. Pick a measure to see how it '
            "runs across the city: dot colour is the measure, dot size is how much data stands behind it.</p>",
            unsafe_allow_html=True)

CBD = (-33.8688, 151.2093)

# Centre and zoom for the "Zoom to" presets, so a region is one click away
VIEWS = {
    "Whole metro": (-33.87, 150.99, 9.45),
    "Inner Sydney (10 km)": (-33.88, 151.17, 11.2),
    "Eastern suburbs": (-33.91, 151.24, 11.8),
    "North Shore & Beaches": (-33.76, 151.21, 10.7),
    "Inner West & the south": (-33.95, 151.10, 10.9),
    "Parramatta & the west": (-33.80, 150.92, 10.2),
    "South-west": (-34.00, 150.84, 10.2),
}

# Colour ramps built for the dark basemap: the low end stays visible instead of fading out.
GROWTH_SCALE = [[0.0, "#5c5c58"], [0.3, "#1c5cab"], [0.65, HOUSE], [1.0, "#b8d6f7"]]
YIELD_SCALE = [[0.0, "#5c5c58"], [0.35, "#8f3a1c"], [0.7, UNIT], [1.0, "#f3b48f"]]
PRICE_SCALE = [[0.0, "#3d4f63"], [0.5, "#4c7fbf"], [1.0, "#e8f1fc"]]
GAP_SCALE = [[0.0, "#2f7fd6"], [0.5, "#5c5c58"], [1.0, "#d95926"]]

MEASURES = {
    "Capital growth": dict(
        col="real_cagr_%", label="Real growth a year, 2014–2023", bar="% a year", unit="a year", kpi="Median growth", scale=GROWTH_SCALE, fmt="{:+.1f}%",
        hover="%{customdata[2]:+.1f}%/yr real growth", mid=None,
        note="Darker grey is slower, bright blue is faster. Growth comes from repeat sales of the same dwelling, "
             "so it is not distorted by which suburbs happened to sell.",
    ),
    "Value gap": dict(
        col="value_gap_%", label="Price vs comparable areas", bar="% vs peers", unit="vs comparable areas", kpi="Median value gap", scale=GAP_SCALE, fmt="{:+.0f}%",
        hover="%{customdata[4]:+.0f}% vs comparable areas", mid=0.0,
        note="Blue is priced below what its land size, location, distance and local income support; orange above. "
             "Houses only — units have no value model.",
    ),
    "Rental yield": dict(
        col="gross_yield_%", label="Gross rental yield, 2023", bar="% gross", unit="gross, 2023", kpi="Median yield", scale=YIELD_SCALE, fmt="{:.1f}%",
        hover="%{customdata[3]:.2f}% gross yield", mid=None,
        note="Yield is measured by postcode, so suburbs sharing a postcode share a figure. Gross, before costs.",
    ),
    "Median price": dict(
        col="median_2023", label="Median sale price, 2023", bar="Median price", unit="median, 2023", kpi="Citywide median price", scale=PRICE_SCALE, fmt="${:,.0f}",
        hover="median $%{customdata[5]:,.0f}", mid=None,
        note="Colour is clipped at the 5th and 95th percentile so the harbourside extremes do not flatten "
             "everywhere else.",
    ),
}

GRADIENT_NOTE = {
    ("Capital growth", "House"):
        "<b>House growth fades with distance, but only gently.</b> Houses within 10 km of the CBD grew 5.6% a year "
        "after inflation, against 4.7% beyond 40 km. Distance explains some of growth, not most of it "
        "(correlation −0.32): there are strong and weak markets at every radius.",
    ("Capital growth", "Unit/Townhouse"):
        "<b>For units, distance tells you almost nothing (correlation −0.06) — the middle ring is the problem.</b> "
        "Units 10–20 km out grew just 0.2% a year after inflation, the worst band on the map, while inner units "
        "managed 2.0% and the outer fringe 1.5–2.8%. That band is where most of the decade's apartment towers "
        "were built.",
    ("Value gap", "House"):
        "<b>The value candidates are not one corner of the city.</b> Thirty suburbs pass the screen, led by the "
        "Northern Beaches (6), then Hornsby, Campbelltown and Sutherland (3 each). Their median distance from the "
        "CBD is 19.7 km against 22.6 km for all measured suburbs, so this is a middle-ring story, not a fringe one.",
    ("Value gap", "Unit/Townhouse"):
        "<b>The value model covers houses only.</b> Switch the dwelling type to House, or colour the map by growth "
        "or yield.",
    ("Rental yield", "House"):
        "<b>House income is almost a straight function of distance (correlation 0.75).</b> Gross yield runs from "
        "2.1% inside 10 km to 3.5% beyond 40 km. Because total return was near-identical across house yield "
        "quartiles, choosing a radius is a cash-flow decision rather than a performance one.",
    ("Rental yield", "Unit/Townhouse"):
        "<b>Unit yields are flat across the city (correlation 0.06)</b> — 3.7% inside 10 km and 4.2% beyond 40 km. "
        "Going further out buys a unit investor almost no extra income, and the outer unit markets grew least. "
        "This is the geography behind not chasing unit yield.",
    ("Median price", "House"):
        "<b>Price falls steeply with distance, which is exactly why the map is useful.</b> Growth and value gaps "
        "have to be read against this gradient: a cheap suburb is not a discounted one until it is compared with "
        "suburbs at the same radius, which is what the value model does.",
    ("Median price", "Unit/Townhouse"):
        "<b>Unit prices flatten quickly with distance.</b> Beyond the inner ring a unit costs much the same "
        "wherever it is, so location is paid for in growth and rent rather than in the purchase price.",
}


@st.cache_data
def build(segment: str) -> pd.DataFrame:
    """One row per mappable suburb, carrying every measure the map can colour by."""
    coords = load("suburb_coords")
    growth = load("suburb_growth")
    growth = growth[growth.segment == segment].drop(columns="segment")
    value = load("suburb_value_gap")[["suburb", "value_gap_%", "value_candidate"]]

    yields = load("yield_by_postcode")
    yields = yields[(yields.year == yields.year.max()) & (yields.segment == segment)]
    yields = (load("suburb_postcode")
              .merge(yields[["post_code", "gross_yield_%", "median_weekly_rent"]], on="post_code", how="inner"))

    d = (coords.merge(growth, on="suburb", how="left")
               .merge(value, on="suburb", how="left")
               .merge(yields, on="suburb", how="left"))
    d["value_candidate"] = d.value_candidate.fillna(False)
    if segment != "House":  # the value model is fitted on houses; it says nothing about units
        d[["value_gap_%", "value_candidate"]] = [pd.NA, False]
    return d


c1, c2 = st.columns([3, 2])
with c1:
    measure = st.radio("Colour the map by", list(MEASURES), horizontal=True)
with c2:
    segment = st.radio("Dwelling type", list(SEGMENT_COLORS), horizontal=True)

m = MEASURES[measure]
d = build(segment)

with st.sidebar:
    st.header("Filters")
    if segment == "Unit/Townhouse" and measure == "Value gap":
        st.info("The value model covers houses only.")
    budget = st.slider("Median price 2023 ($M)", 0.3, 10.0, (0.3, 10.0), step=0.1,
                       help="Suburbs with no 2023 median are kept.")
    max_km = st.slider("Maximum distance from the CBD (km)", 5, 70, 70, 5)
    councils = st.multiselect("Councils", sorted(d.council.dropna().unique()))
    only_candidates = st.checkbox("Value-screen candidates only", value=False)
    show_cbd = st.checkbox("Mark the CBD", value=True)
    st.divider()
    view = st.selectbox("Zoom to", list(VIEWS),
                        help="Jumps the map to a part of the city. You can also scroll, drag, "
                             "or use the + / − buttons on the map.")

plot = d[d[m["col"]].notna() & (d.km_from_cbd <= max_km)].copy()
plot = plot[plot.median_2023.isna() | plot.median_2023.between(budget[0] * 1e6, budget[1] * 1e6)]
if councils:
    plot = plot[plot.council.isin(councils)]
if only_candidates:
    plot = plot[plot.value_candidate]

if plot.empty:
    if measure == "Value gap" and segment != "House":
        st.info("The value model is fitted on houses only, so there is no unit value gap to map. "
                "Switch the dwelling type to House, or colour the map by growth, yield or price.")
    else:
        st.warning("Nothing to map with these filters. Widen the price range or the distance limit.")
    st.stop()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Suburbs on the map", f"{len(plot)}", f"of {len(d)} with a centre point", delta_color="off")
k2.metric(m["kpi"], m["fmt"].format(plot[m["col"]].median()),
          "across mapped suburbs", delta_color="off")
k3.metric("Highest", plot.loc[plot[m["col"]].idxmax(), "suburb"],
          f'{m["fmt"].format(plot[m["col"]].max())} {m["unit"]}', delta_color="off")
k4.metric("Lowest", plot.loc[plot[m["col"]].idxmin(), "suburb"],
          f'{m["fmt"].format(plot[m["col"]].min())} {m["unit"]}', delta_color="off")

# ------------------------------------------------------------------ the map

# Dot size carries sample weight: repeat-sale pairs where there are any, a small dot otherwise.
pairs = plot.pairs.fillna(0)
size = 7 + 17 * np.sqrt(pairs / max(pairs.max(), 1))
size = size.where(pairs > 0, 6.5)

vals = plot[m["col"]]
if m["mid"] is not None:
    span = max(abs(vals.quantile(0.03)), abs(vals.quantile(0.97)))
    zmin, zmax = -span, span
else:
    zmin, zmax = vals.quantile(0.05), vals.quantile(0.95)

custom = np.column_stack([plot.suburb, plot.council.fillna("–"), plot["real_cagr_%"], plot["gross_yield_%"],
                          plot["value_gap_%"], plot.median_2023, pairs, plot.km_from_cbd])
hover = ("<b>%{customdata[0]}</b> · %{customdata[1]}<br>" + m["hover"]
         + "<br><span style='color:#c3c2b7'>%{customdata[7]:.0f} km from the CBD · "
           "%{customdata[6]:,.0f} repeat sales</span><extra></extra>")

fig = go.Figure()

cand = plot[plot.value_candidate]
if len(cand):  # halo behind the value-screen candidates, so they stay findable at any zoom
    fig.add_trace(go.Scattermap(lat=cand.lat, lon=cand.lng, mode="markers",
                                marker=dict(size=size[cand.index] + 7, color="rgba(255,255,255,0.33)"),
                                hoverinfo="skip", showlegend=False))

fig.add_trace(go.Scattermap(
    lat=plot.lat, lon=plot.lng, mode="markers", customdata=custom, hovertemplate=hover,
    marker=dict(size=size, color=vals, colorscale=m["scale"], cmin=zmin, cmax=zmax, opacity=0.92,
                colorbar=dict(title=dict(text=m["bar"], side="top", font=dict(size=12, color=INK_2)),
                              thickness=11, len=0.6, x=0.985, y=0.5, xpad=0, bgcolor="rgba(13,13,13,0.55)",
                              outlinewidth=0,
                              tickfont=dict(size=11, color=MUTED),
                              tickprefix="$" if m["col"] == "median_2023" else "",
                              ticksuffix="" if m["col"] == "median_2023" else "%")),
))

if show_cbd:
    fig.add_trace(go.Scattermap(lat=[CBD[0]], lon=[CBD[1]], mode="markers+text", text=["Sydney CBD"],
                                textposition="top right", textfont=dict(size=12, color=INK_2),
                                marker=dict(size=9, color="#ffffff"), hoverinfo="skip", showlegend=False))

lat0, lon0, zoom0 = VIEWS[view]
fig.update_layout(
    map=dict(style="carto-darkmatter", center=dict(lat=lat0, lon=lon0), zoom=zoom0),
    height=620, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor=SURFACE,
    # keyed on the preset: changing filters or the measure keeps the view you panned to,
    # picking a new preset moves the map there
    uirevision=f"map-{view}",
    font=dict(family="Segoe UI, system-ui, sans-serif", size=13, color=INK), showlegend=False,
)
st.plotly_chart(fig, use_container_width=True,
                config={"scrollZoom": True, "displayModeBar": True, "displaylogo": False})
st.markdown(f'<p class="caption">{m["note"]} Dot size is the number of repeat sales behind the suburb, so small '
            "dots deserve less weight. White rings mark the 30 value-screen candidates. "
            "<b>Scroll or use the + / − buttons to zoom, drag to pan</b>, or jump to a region with "
            "<i>Zoom to</i> in the sidebar.</p>", unsafe_allow_html=True)

# ------------------------------------------------------------------ distance gradient

st.divider()
st.subheader("The same measure, against distance from the CBD")

band = pd.cut(plot.km_from_cbd, [0, 5, 10, 15, 20, 25, 30, 40, 50, 80])
prof = plot.groupby(band, observed=True)[m["col"]].median().reset_index()
prof["mid"] = prof.km_from_cbd.apply(lambda i: i.mid)

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=plot.km_from_cbd, y=vals, mode="markers", name="Suburbs",
                          marker=dict(size=7, color=FAINT), text=plot.suburb,
                          hovertemplate="%{text}<extra></extra>"))
fig2.add_trace(go.Scatter(x=prof["mid"], y=prof[m["col"]], mode="lines+markers", name="Median by distance band",
                          line=dict(color=SEGMENT_COLORS[segment], width=2.8), marker=dict(size=8),
                          hovertemplate="%{y:.2f} at %{x:.0f} km<extra></extra>"))
if m["mid"] is not None:
    fig2.add_hline(y=0, line=dict(color=MUTED, width=1, dash="dot"))
fig2.update_layout(hovermode="closest")
if m["col"] == "median_2023":
    fig2.update_yaxes(tickprefix="$", tickformat=",.0f")
else:
    fig2.update_yaxes(ticksuffix="%")
st.plotly_chart(style_fig(fig2, 330, ylabel=m["label"], xlabel="Kilometres from the CBD"),
                use_container_width=True)

if (measure, segment) in GRADIENT_NOTE:
    takeaway(GRADIENT_NOTE[(measure, segment)])

# ------------------------------------------------------------------ ranked lists

st.divider()
cols = ["suburb", "council", m["col"], "km_from_cbd"]
rename = {"suburb": "Suburb", "council": "Council", "km_from_cbd": "km", m["col"]: measure}
cfg = {measure: st.column_config.NumberColumn(format="$%,.0f" if m["col"] == "median_2023" else "%.2f%%"),
       "km": st.column_config.NumberColumn(format="%.0f")}

left, right = st.columns(2)
with left:
    st.markdown(f"##### Highest {measure.lower()}")
    st.dataframe(plot.nlargest(10, m["col"])[cols].rename(columns=rename), hide_index=True,
                 use_container_width=True, column_config=cfg)
with right:
    st.markdown(f"##### Lowest {measure.lower()}")
    st.dataframe(plot.nsmallest(10, m["col"])[cols].rename(columns=rename), hide_index=True,
                 use_container_width=True, column_config=cfg)

st.download_button("Download the mapped suburbs (CSV)",
                   plot[["suburb", "council", "lat", "lng", "km_from_cbd", "real_cagr_%", "value_gap_%",
                         "gross_yield_%", "median_2023", "pairs", "value_candidate"]].to_csv(index=False).encode(),
                   file_name=f"sydney_map_{segment.replace('/', '_')}.csv", mime="text/csv")

takeaway(
    "<b>Points, not boundaries.</b> Each dot sits at the centre of its suburb, so dot spacing reflects suburb size, "
    "not where the housing is. Use the map to spot clusters and gaps, not to read a boundary."
)

footer_note()
