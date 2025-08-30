# frontend/streamlit_app.py
import sys
import os
import streamlit as st

# 🔑 Ensure repo root is in sys.path (important for Streamlit Cloud)
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.session import SessionManager
from backend.holdings import HoldingsService
from backend.orders import OrdersService


# ----------------------------------------------------
# App Entry Point
# ----------------------------------------------------
def main():
    st.set_page_config(page_title="GM TradeBot", layout="wide")
    st.title("🚀 GM TradeBot Dashboard")

    # --- Session management ---
    api_token = st.secrets["DEFINEDGE_API_TOKEN"]
    api_secret = st.secrets["DEFINEDGE_API_SECRET"]
    totp_secret = st.secrets.get("DEFINEDGE_TOTP_SECRET")

    try:
        session = SessionManager(api_token, api_secret, totp_secret)
        client = session.get_client()
        st.success("✅ Logged in successfully")
    except Exception as e:
        st.error(f"❌ Login failed: {e}")
        return

    # --- Holdings ---
    holdings_service = HoldingsService(client)
    holdings = holdings_service.get_holdings()

    st.subheader("📊 Your Holdings")
    if holdings:
        st.dataframe(holdings)
    else:
        st.write("No holdings available.")

    # --- Orders ---
    st.subheader("📝 Place an Order")
    symbol = st.text_input("Symbol", "NIFTY")
    qty = st.number_input("Quantity", min_value=1, value=1)
    side = st.selectbox("Side", ["BUY", "SELL"])

    if st.button("Place Order"):
        orders_service = OrdersService(client)
        try:
            order = orders_service.place_order(symbol=symbol, qty=qty, side=side)
            st.success(f"✅ Order placed: {order}")
        except Exception as e:
            st.error(f"❌ Failed to place order: {e}")


# ----------------------------------------------------
if __name__ == "__main__":
    main()
