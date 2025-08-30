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

    st.write("🔎 Debug: Current session_state keys:", list(st.session_state.keys()))

    try:
        # ---- API call using requests ----
        api_key = getattr(client, "api_session_key", None)
        if not api_key:
            st.error("⚠️ API session key missing. Please login again.")
            st.stop()

        url = "https://api.definedge.com/orders"  # Replace with actual base URL
        headers = {"Authorization": api_key}

        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200 or not resp.text.strip():
            st.error(f"⚠️ API returned error or empty response: {resp.status_code}")
            st.stop()

        data = resp.json()
        st.write("🔎 Debug: Raw API response:", data)

        if data.get("status") != "SUCCESS":
            st.error("⚠️ Order Book API failed")
            st.stop()

        raw_data = data.get("data", [])
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

    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Network/API request error: {e}")
    except Exception as e:
        st.error(f"⚠️ Something went wrong: {e}")
