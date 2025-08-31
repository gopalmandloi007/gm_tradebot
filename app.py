import streamlit as st
from pages.holdings import show as show_holdings
from pages.orderbook import show as show_orderbook
from pages.trades import show as show_trades
from pages.login import show as show_login
from pages.place_order import show as show_place_order
from pages.gtt_orderbook import show as show_gtt_orderbook
from pages.positions import show as show_positions
from pages.place_gtt_order import show_place_gtt_order
from pages.place_oco_order import show_place_oco_order
from pages.dashboard import show_dashboard

# Import update_master script
from scripts import update_master  # <-- yahan se call hoga

# ---- Page config ----
st.set_page_config(page_title="📊 Trade Dashboard", layout="wide")
st.title("📊 Trade Dashboard")

# ---- Sidebar: Tools & Page Selection ----
with st.sidebar:
    st.header("⚙️ Tools")
    if st.button("Update Master File"):
        st.info("Downloading and updating master file...")
        try:
            update_master.download_master("All Segments")
            st.success("✅ Master file updated successfully!")
        except Exception as e:
            st.error(f"Failed to update master file: {e}")

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
