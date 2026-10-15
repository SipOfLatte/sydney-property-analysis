"""What features are worth, plus the method and limitations behind every number in this app."""
import plotly.graph_objects as go
import streamlit as st

from lib import BAD, HOUSE, INK_2, MUTED, footer_note, load, style_fig, takeaway

st.title("What Features Are Worth · Method & Data")

features = load("feature_values")

st.subheader("Q4 · What each extra bedroom, bathroom or car space adds")
st.markdown('<p class="caption">Comparing houses in the same suburb, sold in the same quarter, on the same land '
            "size. Dollar values are for a typical $1.45M Sydney house.</p>", unsafe_allow_html=True)

order = ["Bathrooms", "Bedrooms", "Car spaces", "Land"]
f = features.set_index("feature").loc[order].reset_index()
fig = go.Figure(go.Bar(
    x=f["marginal_$"], y=[f"{r.feature}: {r.step}" for r in f.itertuples()], orientation="h",
    marker_color=[HOUSE if v > 0 else BAD for v in f["marginal_$"]],
    text=[f"{p:+.1f}%" for p in f["marginal_%"]], textposition="outside",
    hovertemplate="%{y}<br>%{x:$,.0f}<extra></extra>"))
fig.update_yaxes(autorange="reversed")
fig.update_layout(xaxis_range=[f["marginal_$"].min() * 3.5, f["marginal_$"].max() * 1.25])
st.plotly_chart(style_fig(fig, 430, legend=False, xlabel="Added value for a typical $1.45M house"),
                use_container_width=True)

takeaway(
    "<b>Target 4–5 bedroom, 3-bathroom houses with 2 car spaces.</b> A 6th bedroom and a 3rd car space add nothing. "
    "Bathrooms carry the biggest premium — but note the caveat below: this data has no floor area, so a "
    "3-bathroom house is usually a bigger, newer house."
)

st.divider()
st.subheader("Method")

c1, c2 = st.columns(2)
with c1:
    st.markdown("""
**Like-for-like growth (repeat sales).** Median prices track *what sold*, not what properties are worth. When new,
cheaper homes come to market the median falls even if nothing lost value. So growth here compares the **same dwelling
sold twice** (the method behind CoreLogic and Case-Shiller indices), using 111,870 pairs.

**What was excluded, and why**
- Pairs held under 6 months, where land size changed (subdivision), or with implausible returns (renovations and
  rebuilds).
- **New-build first sales.** On a new estate the first "sale" is often the vacant lot or an off-the-plan contract.
  Before this fix, Marsden Park looked like Sydney's fastest-growing suburb at 19% a year. It wasn't; that was the
  cost of building the house.

**Keeping small suburbs honest.** A suburb with 100 sales can post an extreme growth rate by chance. Each estimate is
pulled toward the Sydney average in proportion to its uncertainty (empirical-Bayes shrinkage), so the rankings aren't
led by luck.

**Risk by council, not suburb.** Volatility at suburb level is mostly sampling noise — a dozen suburbs measured
*exactly zero*. Councils have enough sales to separate the signal, and the estimated noise is subtracted.
""")
with c2:
    st.markdown("""
**Value gap.** A gradient-boosting model prices houses from land size, distance to the CBD, suburb income, location,
elevation and density, using **suburb-grouped cross-validation**: every suburb is priced by a model that never saw it.
The gap is the average difference between actual and predicted price (shrunk for small samples).

**Why a value gap alone is misleading.** The model's "cheapest" suburbs were Kurnell (next to a former refinery, near
flight paths), Kings Park (industrial area) and Carramar (flood-prone). They are cheap for reasons the model can't
see. The screener therefore also requires **above-median past growth** as evidence of real demand.

**Known limitations**
- Sales records only: **no rent, so no rental yield**, and no property condition or floor area.
- Feature values come from a smaller Domain sample (7,290 houses, 2016–2021, 50% of them from 2021).
- Value gaps are modelled for **houses only**.
- Repeat sales slightly overstate growth where owners renovated between sales.
- Data ends in 2023 and excludes the Central Coast and Blue Mountains.
""")

st.divider()
st.subheader("Data")
st.markdown("""
| Source | What it provides | Rows used |
|---|---|---|
| NSW Valuer General sales (Kaggle `josephcheng123456/nsw-australia-property-data`) | Every Sydney metro residential sale, 2014–2023 | 881,664 after cleaning |
| Domain listings (Kaggle `alexlau203/sydney-house-prices`) | Bedrooms, bathrooms, parking, suburb fundamentals | 7,290 houses |
| ABS Sydney CPI (table 6401017) | Inflation adjustment (Sydney CPI rose 29% over the decade) | quarterly series |

Cleaning removed duplicate records, non-residential sales, bulk transfers of several dwellings on one contract, and
prices outside $50k–$20M. Every step and its row count is in `docs/data_quality_report.md`; the analysis is in three
Jupyter notebooks in the repository.
""")

footer_note()
