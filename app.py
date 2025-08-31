import streamlit as st
import scripts.update_master as um

# ---- Page config ----
st.set_page_config(page_title="📊 Trade Dashboard", layout="wide")
st.title("📊 Trade Dashboard")

# ---- Sidebar: Button to update master file ----
st.sidebar.subheader("⚡ Utilities")
if st.sidebar.button("Update Master File"):
    with st.spinner("Downloading and updating master file..."):
        success = um.download_master()
        if success:
            st.success("✅ Master file updated successfully!")
        else:
            st.error("❌ Failed to update master file.")

# ---- Sidebar: Radio Buttons for Page Selection ----
page = st.sidebar.radio(
    "Select Page",
    [
        "Login",
        "Holdings",
        "Positions",        
        "Order Book",
        "Trades",
        "Place Order",
        "GTT Order Book",
        "Place GTT Order",
        "Place OCO Order",
        "Dashboard"
    ]
)

# ---- Show selected page (existing logic, no change) ----
from pages.holdings import show as show_holdings
from pages.orderbook import show as show_orderbook
from pages.trades import show as show_trades
from pages.login import show as show_login
from pages.place_order import show as show_place_order
from pages.gtt_orderbook import show as show_gtt_orderbook
from pages.positions import show as show_positions
from pages.place_gtt_order import show_place_gtt_order
from pages.place_oco_order import show as show_place_oco_order
from pages.dashboard import show_dashboard

if page == "Login":
    show_login()
else:
    if "client" not in st.session_state:
        st.warning("⚠️ Please login first via Login page.")
        st.stop()

    if page == "Holdings":
        show_holdings()
    elif page == "Positions":
        show_positions()
    elif page == "Order Book":
        show_orderbook()
    elif page == "Trades":
        show_trades()
    elif page == "Place Order":
        show_place_order()
    elif page == "GTT Order Book":
        show_gtt_orderbook()
    elif page == "Place GTT Order":
        show_place_gtt_order()
    elif page == "Place OCO Order": 
        show_place_oco_order()
    elif page ==  "Dashboard":
        show_dashboard()
        
