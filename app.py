# app.py
import streamlit as st
from pages.holdings import show as show_holdings
from pages.orderbook import show as show_orderbook
from pages.trades import show as show_trades
from pages.login import show as show_login  # optional login page

st.set_page_config(page_title="📊 Trade Dashboard", layout="wide")
st.title("📊 Trade Dashboard")

# ---- Sidebar: Radio Buttons for Page Selection ----
page = st.sidebar.radio(
    "Select Page",
    ["Login", "Holdings", "Positions", "Order Book", "Trades"]
)

# ---- Show selected page ----
if page == "Login":
    show_login()  # your login.py page
else:
    # Check client is logged in
    if "client" not in st.session_state:
        st.warning("⚠️ Please login first via Login page.")
        st.stop()

    # Show pages
    if page == "Holdings" or page == "Positions":
        show_holdings()  # Positions can also use show_holdings or separate function
    elif page == "Order Book":
        show_orderbook()
    elif page == "Trades":
        show_trades()
