# Project Brief: Sydney Residential Property Market Analysis

**Client (simulated):** Residential property investment fund, acquisitions team
**Analyst:** Jack
**Scope:** Sydney metro residential sales, 2014–2023 (postcodes 2000–2234, 2555–2570, 2745–2770)

## Data sources
| Dataset | Source | Used for |
|---|---|---|
| NSW property sales (primary) | NSW Valuer General, via Kaggle `josephcheng123456/nsw-australia-property-data` | Q1–Q3, Q5–Q7 · 881k clean sales |
| Domain Sydney sales (supporting) | Kaggle `alexlau203/sydney-house-prices` | Q4 feature value (beds/baths/parking), 2016–2021 sample |
| ABS CPI (planned) | Australian Bureau of Statistics | Real (inflation-adjusted) growth |
| ABS Census by postcode (stretch) | Australian Bureau of Statistics | Q8 growth drivers |

**Tools:** Python (pandas, scikit-learn, statsmodels) → Streamlit dashboard

## Business context
The fund wants to put capital into Sydney residential property. It needs evidence on
**where**, **what type** and **when** to buy, and on what drives the price it will pay.
The decision is about where to allocate money, so the findings must be defensible:
say how confident we are, give the sample size, and state the caveats.

## Key business questions

| # | Question | Stakeholder use | Method |
|---|----------|-----------------|--------|
| Q1 | How have Sydney prices moved from 2014–2023, and what were the major cycles? | Market timing, context | Median price by quarter/year, YoY %, rolling medians |
| Q2 | Which suburbs/postcodes had the strongest long-run growth (CAGR)? | Shortlist growth areas | Per-suburb median CAGR with minimum sales threshold |
| Q3 | Houses vs units: which gave better growth, and how has the gap changed? | Asset-type allocation | Segment trend comparison, significance test |
| Q4 | Which features (bedrooms, bathrooms, parking) add the most value, and is there a point where they stop adding much? *(Domain dataset)* | Renovation / acquisition spec | Grouped medians, regression coefficients |
| Q5 | Is there seasonality in sale prices or volumes? | Timing of purchases | Month/quarter effects, controlling for year |
| Q6 | Which suburbs look *undervalued* relative to their characteristics? | Deal sourcing | Model residuals aggregated by suburb |
| Q7 | How volatile is each area? (risk vs return) | Risk-adjusted selection | Std dev of annual growth vs CAGR (risk/return quadrant) |
| Q8 | *(stretch, with ABS data)* Is growth related to income / population / distance to the CBD? | Understand what drives growth | Join census data, correlation |

## Deliverables
1. Cleaned, documented dataset plus a data quality report
2. Analysis notebooks, one per question group
3. Explainable price model (feature importance, undervalued-suburb list)
4. Streamlit dashboard (deployed, public URL): Market Overview · Suburb Explorer · Investment Screener
5. Executive summary (1–2 pages): findings, recommendations, limitations

## Known limitations (full detail in data_quality_report.md)
- The main source has no beds/baths/parking. Q4 uses the smaller Domain sample, and growth uses a repeat-sales index to control for property mix.
- It covers **sales records only**: no rent (so no yield) and no property condition. Land size is available for freestanding houses only.
- Medians are affected by which properties sold (composition bias). Where possible, compare like with like (same dwelling type, or repeat sales of the same property).
- Prices are nominal. Consider CPI-adjusting (ABS CPI) to report real growth.
