# pages/orderbook.py
import streamlit as st
import traceback
import pandas as pd

def show():
    st.header("📑 Orderbook — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    if st.button("Fetch Orderbook"):
        try:
            orders = client.get_orders()   # this is the orderbook
            if isinstance(orders, dict) and "data" in orders:
                df = pd.DataFrame(orders["data"])
                if not df.empty:
                    st.success("✅ Orderbook fetched successfully")
                    st.dataframe(df)
                else:
                    st.info("No active orders in the orderbook.")
            elif isinstance(orders, list):
                df = pd.DataFrame(orders)
                if not df.empty:
                    st.success("✅ Orderbook fetched successfully")
                    st.dataframe(df)
                else:
                    st.info("No active orders in the orderbook.")
            else:
                st.warning("Unexpected response format")
                st.json(orders)
        except Exception as e:
            st.error(f"Fetching orderbook failed: {e}")
            st.text(traceback.format_exc())
            
