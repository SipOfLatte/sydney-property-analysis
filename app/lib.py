"""Shared data loading, palette and chart styling for the Streamlit dashboard."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "data" / "exports"

# Same palette as the notebook figures, so report and dashboard read as one system
HOUSE = "#2a78d6"
UNIT = "#eb6834"
SEGMENT_COLORS = {"House": HOUSE, "Unit/Townhouse": UNIT}
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"
GOOD = "#0ca30c"
BAD = "#d03b3b"

PAGE_ICON = "🏠"


def page_style() -> None:
    """Shared CSS. Called once from app.py (set_page_config lives there too)."""
    st.markdown(
        f"""<style>
        .block-container {{padding-top: 2.2rem; max-width: 1250px;}}
        h1, h2, h3 {{color: {INK};}}
        [data-testid="stMetricValue"] {{font-size: 1.6rem;}}
        .caption {{color: {INK_2}; font-size: 0.92rem;}}
        </style>""",
        unsafe_allow_html=True,
    )


@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_csv(EXPORTS / f"{name}.csv")


@st.cache_data
def cpi_factor() -> pd.Series:
    """Quarter -> factor that converts a nominal price into Dec-2023 dollars."""
    cpi = pd.read_csv(ROOT / "data/external/cpi_sydney_quarterly.csv").set_index("quarter")["cpi_sydney"]
    return cpi["2023Q4"] / cpi


def style_fig(fig: go.Figure, height: int = 420, legend: bool = True, ylabel: str = "", xlabel: str = "") -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=20, t=30, b=10),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family="Segoe UI, system-ui, sans-serif", size=13, color=INK),
        hovermode="x unified",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
        yaxis=dict(title=ylabel, gridcolor=GRID, zerolinecolor=GRID, linecolor=SURFACE, tickfont=dict(color=MUTED)),
        xaxis=dict(title=xlabel, gridcolor=SURFACE, linecolor=GRID, tickfont=dict(color=MUTED)),
    )
    return fig


def money(v: float) -> str:
    if pd.isna(v):
        return "–"
    return f"${v / 1e6:.2f}M" if v >= 1e6 else f"${v / 1e3:,.0f}k"


def takeaway(text: str) -> None:
    """A finding callout, matching the 'What this means' boxes in the notebooks."""
    st.markdown(
        f"""<div style="border-left: 3px solid {HOUSE}; background: #f4f8fe; padding: 0.7rem 1rem;
        border-radius: 4px; margin: 0.4rem 0 1rem 0; color: {INK};">{text}</div>""",
        unsafe_allow_html=True,
    )


def footer_note() -> None:
    st.markdown(
        f"""<p class="caption" style="margin-top:2rem;">Source: NSW Valuer General sales (881,664 Sydney metro sales,
        2014–2023) and Domain listings via Kaggle · Inflation: ABS Sydney CPI · Built with Python and Streamlit ·
        Method and limitations are on the <b>Features &amp; Method</b> page.</p>""",
        unsafe_allow_html=True,
    )
