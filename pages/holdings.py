# holdings.py
import streamlit as st
import pandas as pd

def show():
    st.title("📊 Holdings Page (Debug Mode)")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in")
        st.stop()

    st.write("🔎 Debug: Current session_state keys:", list(st.session_state.keys()))

    try:
        resp = client.get_holdings()
        st.write("🔎 Debug: Raw holdings API response:", resp)

        if resp.get("status") != "SUCCESS":
            st.error("⚠️ Holdings API failed")
            st.stop()

        raw_data = resp.get("data", [])
        st.write("🔎 Debug: Extracted data field:", raw_data)

        # ---- Flatten NSE only ----
        records = []
        for h in raw_data:
            base = {k: v for k, v in h.items() if k != "tradingsymbol"}
            for ts in h.get("tradingsymbol", []):
                if ts.get("exchange") == "NSE":   # ✅ Only NSE
                    row = {**base, **ts}
                    records.append(row)

        st.write("🔎 Debug: Flattened records:", records)

        if records:
            df = pd.DataFrame(records)
            st.write(f"🔎 Debug: DataFrame created with shape: {df.shape}")
            st.write("🔎 Debug: Available columns for display:", list(df.columns))

            # Clean view
            df = df.rename(columns={
                "dp_qty": "Quantity",
                "avg_buy_price": "Avg Buy Price",
                "tradingsymbol": "Symbol",
                "exchange": "Exchange"
            })

            cols = ["Symbol", "Exchange", "Quantity", "Avg Buy Price", "isin"]
            df = df[cols]

            st.success(f"✅ NSE Holdings found: {len(df)}")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("⚠️ No NSE holdings found")

    except Exception as e:
        st.error(f"Holdings fetch failed: {e}")
