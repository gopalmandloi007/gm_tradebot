# orderbook.py
import streamlit as st
import pandas as pd

def show():
    st.title("📈 Order Book Page (All Fields)")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in")
        st.stop()

    st.write("🔎 Debug: Current session_state keys:", list(st.session_state.keys()))

    try:
        resp = client.get_orders()
        st.write("🔎 Debug: Raw order book API response:", resp)

        if resp.get("status") != "SUCCESS":
            st.error("⚠️ Order Book API failed")
            st.stop()

        raw_data = resp.get("data", [])
        st.write("🔎 Debug: Extracted data field:", raw_data)

        # ---- Flatten all fields (Only NSE) ----
        records = []
        for o in raw_data:
            base = {k: v for k, v in o.items() if k != "tradingsymbol"}
            for ts in o.get("tradingsymbol", []):
                if ts.get("exchange") == "NSE":   # ✅ Only NSE
                    row = {**base, **ts}
                    records.append(row)

        st.write("🔎 Debug: Flattened records:", records)

        if records:
            df = pd.DataFrame(records)
            st.success(f"✅ NSE Orders found: {len(df)}")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("⚠️ No NSE orders found")

    except Exception as e:
        st.error(f"Order Book fetch failed: {e}")
