import streamlit as st
import pandas as pd
from definedge_api import DefinedgeClient, DefinedgeAPIError

def show():
    st.header("📊 Holdings Page (Debug Mode)")

    # Debug: session state check
    st.write("🔎 Debug: Current session_state keys:", list(st.session_state.keys()))

    if "client" not in st.session_state or st.session_state["client"] is None:
        st.warning("⚠️ Please login first to view holdings.")
        return

    client: DefinedgeClient = st.session_state["client"]

    try:
        st.write("🔎 Debug: Calling get_holdings() API...")
        with st.spinner("Fetching holdings from Definedge API..."):
            data = client.get_holdings()

        # Debug: raw response
        st.write("🔎 Debug: Raw holdings API response:", data)

        if not data:
            st.info("ℹ️ API returned empty data (no holdings).")
            return

        # कभी API dict देता है "data" के अंदर
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
            st.write("🔎 Debug: Extracted data field:", data)

        # DataFrame में convert
        df = pd.DataFrame(data)
        st.write("🔎 Debug: DataFrame created with shape:", df.shape)

        if df.empty:
            st.info("ℹ️ No holdings found in account.")
            return

        # सिर्फ main fields चुनो
        cols = ["tradingSymbol","exchange","product","quantity","averagePrice","lastPrice","pnl"]
        available_cols = [c for c in cols if c in df.columns]
        st.write("🔎 Debug: Available columns for display:", available_cols)

        df = df[available_cols]

        # Final table show
        st.dataframe(df, use_container_width=True)

    except DefinedgeAPIError as e:
        st.error(f"❌ Definedge API error: {e}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
