import streamlit as st
import pandas as pd

def show():
    st.header("📊 Holdings")

    # client object check
    if "client" not in st.session_state or st.session_state["client"] is None:
        st.warning("⚠️ Please login first from sidebar → Login page.")
        return

    client = st.session_state["client"]

    try:
        # API se holdings fetch
        data = client.get_holdings()

        if not data or "data" not in data:
            st.error("❌ No holdings data received from API.")
            st.json(data)  # raw debug
            return

        holdings = data["data"]

        if isinstance(holdings, list) and len(holdings) > 0:
            df = pd.DataFrame(holdings)

            # better column naming if available
            rename_map = {
                "symbol": "Symbol",
                "qty": "Quantity",
                "avgPrice": "Avg. Price",
                "ltp": "LTP",
                "pnl": "P&L",
                "product": "Product"
            }
            df.rename(columns={k: v for k,v in rename_map.items() if k in df.columns}, inplace=True)

            # calculate P&L % if columns exist
            if "Avg. Price" in df.columns and "LTP" in df.columns:
                df["P&L %"] = ((df["LTP"] - df["Avg. Price"]) / df["Avg. Price"] * 100).round(2)

            st.dataframe(df, use_container_width=True)
        else:
            st.info("No holdings available.")
            st.json(holdings)

    except Exception as e:
        st.error(f"Error fetching holdings: {e}")
