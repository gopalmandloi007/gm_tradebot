# app.py
import streamlit as st
from holdings import show as show_holdings
from orderbook import show as show_orderbook
from trades import show as show_trades

# ---- App Config ----
st.set_page_config(page_title="📊 Trade Dashboard", layout="wide")
st.title("📊 Trade Dashboard")

# ---- Sidebar: Radio Buttons for Page Selection ----
page = st.sidebar.radio("Select Page", ["Holdings", "Order Book", "Trades"])

# ---- Show selected page ----
if page == "Holdings":
    show_holdings()
elif page == "Order Book":
    show_orderbook()
elif page == "Trades":
    show_trades()
