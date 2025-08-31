# app.py
import streamlit as st
from pages.holdings import show as show_holdings
from pages.orderbook import show as show_orderbook
from pages.trades import show as show_trades
from pages.login import show as show_login
from pages.place_order import show as show_place_order
from pages.gtt_orderbook import show as show_gtt_orderbook
from pages.positions import show as show_positions   # ✅ Positions page import

# ---- Page config ----
st.set_page_config(page_title="📊 Trade Dashboard", layout="wide")
st.title("📊 Trade Dashboard")

# ---- Sidebar: Radio Buttons for Page Selection ----
page = st.sidebar.radio(
    "Select Page",
    [
        "Login",
        "Holdings",
        "Positions",        # ✅ Now separate option
        "Order Book",
        "Trades",
        "Place Order",
        "GTT Order Book"
    ]
)

# ---- Show selected page ----
if page == "Login":
    show_login()
else:
    # Check client is logged in
    if "client" not in st.session_state:
        st.warning("⚠️ Please login first via Login page.")
        st.stop()

    if page == "Holdings":
        show_holdings()
    elif page == "Positions":
        show_positions()   # ✅ Separate page show
    elif page == "Order Book":
        show_orderbook()
    elif page == "Trades":
        show_trades()
    elif page == "Place Order":
        show_place_order()
    elif page == "GTT Order Book":
        show_gtt_orderbook()
        
