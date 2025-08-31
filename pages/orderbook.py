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
            resp = client.get_orders()   # calls /orders
            if not resp:
                st.warning("⚠️ API returned empty response")
                return

            status = resp.get("status")
            orders = resp.get("orders", [])

            if status != "SUCCESS":
                st.error(f"❌ API returned error. Response: {resp}")
                return

            if not orders:
                st.info("No orders found in orderbook today.")
                return

            # Convert to dataframe
            df = pd.DataFrame(orders)
            st.success(f"✅ Orderbook fetched ({len(df)} orders)")
            st.dataframe(df)

        except Exception as e:
            st.error(f"Fetching orderbook failed: {e}")
            st.text(traceback.format_exc())
            
