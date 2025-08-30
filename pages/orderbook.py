# orderbook.py
import streamlit as st
import pandas as pd
import requests

def show():
    st.title("📈 Order Book Page (All Fields)")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in")
        st.stop()

    try:
        # ---- Use actual API session key ----
        api_key = client.api_session_key  # replace with actual attribute
        url = "https://api.definedge.com/orders"  # Replace with actual base URL + endpoint
        headers = {
            "Authorization": api_key
        }

        resp = requests.get(url, headers=headers)
        data = resp.json()
        st.write("🔎 Debug: Raw API response:", data)

        if data.get("status") != "SUCCESS":
            st.error("⚠️ Order Book API failed")
            st.stop()

        raw_data = data.get("data", [])
        records = []

        for o in raw_data:
            base = {k: v for k, v in o.items() if k != "tradingsymbol"}
            for ts in o.get("tradingsymbol", []):
                if ts.get("exchange") == "NSE":  # Only NSE
                    row = {**base, **ts}
                    records.append(row)

        if records:
            df = pd.DataFrame(records)
            st.success(f"✅ NSE Orders found: {len(df)}")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("⚠️ No NSE orders found")

    except Exception as e:
        st.error(f"Order Book fetch failed: {e}")
