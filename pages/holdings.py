import streamlit as st
import pandas as pd
from definedge_api import DefinedgeClient, DefinedgeAPIError

def show():
    st.header("📊 Holdings")

    # client check
    if "client" not in st.session_state or st.session_state["client"] is None:
        st.warning("Please login first to view holdings.")
        return

    client: DefinedgeClient = st.session_state["client"]

    try:
        with st.spinner("Fetching holdings..."):
            data = client.get_holdings()   # <-- API call
        if not data:
            st.info("No holdings found.")
            return

        # कभी-कभी API list देता है, कभी dict["data"] में देता है
        if isinstance(data, dict) and "data" in data:
            data = data["data"]

        df = pd.DataFrame(data)
        if df.empty:
            st.info("No holdings available.")
            return

        # अगर API columns बहुत ज्यादा हैं तो कुछ main fields ही दिखाओ
        cols = ["tradingSymbol","exchange","product","quantity","averagePrice","lastPrice","pnl"]
        df = df[[c for c in cols if c in df.columns]]

        st.dataframe(df, use_container_width=True)

    except DefinedgeAPIError as e:
        st.error(f"Definedge API error: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")
