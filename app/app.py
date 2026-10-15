"""Sydney residential property dashboard — entry point and navigation.

Run locally:  streamlit run app/app.py
"""
import streamlit as st

from lib import PAGE_ICON, page_style

st.set_page_config(page_title="Sydney Property Dashboard", page_icon=PAGE_ICON, layout="wide")
page_style()

pages = [
    st.Page("views/market_overview.py", title="Market Overview", icon=":material/trending_up:", default=True),
    st.Page("views/suburb_explorer.py", title="Suburb Explorer", icon=":material/location_city:"),
    st.Page("views/rental_yield.py", title="Rental Yield", icon=":material/payments:"),
    st.Page("views/investment_screener.py", title="Investment Screener", icon=":material/filter_alt:"),
    st.Page("views/features_method.py", title="Features & Method", icon=":material/science:"),
]
st.navigation(pages).run()
