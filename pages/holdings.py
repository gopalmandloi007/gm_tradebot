# holdings.py
import streamlit as st
import pandas as pd
from definedge_api import DefinedgeClient

st.title("📊 Holdings (NSE Only)")

client = st.session_state.get("client")
if not client or not client.api_session_key:
    st.error("⚠️ Please login first.")
    st.stop()

try:
    resp = client.get_holdings()

    if resp.get("status") != "SUCCESS":
        st.error("⚠️ Holdings API failed")
        st.stop()

    raw_data = resp.get("data", [])

    # Flatten only NSE
    records = []
    for h in raw_data:
        common = {k: v for k, v in h.items() if k != "tradingsymbol"}
        for ts in h.get("tradingsymbol", []):
            if ts.get("exchange") == "NSE":   # ✅ Only NSE
                row = {**common, **ts}
                records.append(row)

    if records:
        df = pd.DataFrame(records)

        # Optional: rename & select clean columns
        df = df.rename(columns={
            "dp_qty": "Quantity",
            "avg_buy_price": "Avg Buy Price",
            "tradingsymbol": "Symbol",
            "exchange": "Exchange"
        })

        df = df[["Symbol", "Exchange", "Quantity", "Avg Buy Price", "isin"]]

        st.success(f"✅ Total NSE Holdings: {len(df)}")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("⚠️ No NSE holdings found")

except Exception as e:
    st.error(f"Holdings fetch failed: {e}")
