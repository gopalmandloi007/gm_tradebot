import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta
import plotly.graph_objects as go

@st.cache_data
def load_master_symbols(master_csv_path="data/master/allmaster.csv"):
    df = pd.read_csv(master_csv_path)
    return df

def fetch_historical(client, segment, token, days):
    today = datetime.today()
    from_date = (today - timedelta(days=days*2)).strftime("%d%m%Y%H%M")
    to_date = today.strftime("%d%m%Y%H%M")
    hist_csv = client.historical_csv(segment=segment, token=token, timeframe="day", frm=from_date, to=to_date)
    if not hist_csv.strip():
        raise Exception("No data returned from broker for this symbol.")
    hist_df = pd.read_csv(io.StringIO(hist_csv), header=None)
    if hist_df.shape[1] == 7:
        hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume", "OI"]
    elif hist_df.shape[1] == 6:
        hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume"]
    else:
        raise Exception(f"Unexpected columns in historical data: {hist_df.shape[1]}")
    hist_df["DateTime"] = pd.to_datetime(hist_df["DateTime"])
    hist_df = hist_df.sort_values("DateTime")
    hist_df = hist_df.drop_duplicates(subset=["DateTime"])
    hist_df = hist_df.tail(days)
    hist_df = hist_df.reset_index(drop=True)
    return hist_df

INDEX_MAPPING = {
    "Nifty 50": {"segment": "NSE", "token": "256265"},
    "Nifty 500": {"segment": "NSE", "token": "999920005"},
    "Nifty MidSmall 400": {"segment": "NSE", "token": "999920388"},
}

st.title("📈 Relative Strength Chart")

client = st.session_state.get("client")
if not client:
    st.error("⚠️ Not logged in. Please login first from the Login page.")
    st.stop()

df_master = load_master_symbols()
segment = st.selectbox("Exchange/Segment", sorted(df_master["SEGMENT"].unique()), index=0)
segment_symbols = df_master[df_master["SEGMENT"] == segment].sort_values("TRADINGSYM")
symbol = st.selectbox("Trading Symbol", segment_symbols["TRADINGSYM"].unique())
token_row = segment_symbols[segment_symbols["TRADINGSYM"] == symbol]
token = str(token_row["TOKEN"].iloc[0]) if not token_row.empty else None

index_choice = st.selectbox("Compare Against Index", ["Nifty 50", "Nifty 500", "Nifty MidSmall 400"], index=0)
days_back = st.number_input("Number of Days (candles)", min_value=20, max_value=250, value=55, step=1)
sma_period = st.number_input("RS SMA Period", min_value=2, max_value=55, value=20, step=1)

if st.button("Show Relative Strength Chart") and token:
    try:
        # Fetch symbol and index data
        df_symbol = fetch_historical(client, segment, token, days_back)
        index_info = INDEX_MAPPING[index_choice]
        df_index = fetch_historical(client, index_info["segment"], index_info["token"], days_back)
        # Align by date
        df_symbol = df_symbol[["DateTime", "Close"]].rename(columns={"Close": "SymbolClose"})
        df_index = df_index[["DateTime", "Close"]].rename(columns={"Close": "IndexClose"})
        df_merged = pd.merge(df_symbol, df_index, on="DateTime", how="inner")
        df_merged = df_merged.sort_values("DateTime").reset_index(drop=True)
        # Relative Strength calculation
        df_merged["RS"] = (df_merged["SymbolClose"] / df_merged["IndexClose"]) * 100
        df_merged["RS_SMA"] = df_merged["RS"].rolling(window=sma_period).mean()
        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_merged["DateTime"], y=df_merged["RS"],
            mode="lines", name="Relative Strength",
            line=dict(color="#1976d2", width=2)
        ))
        fig.add_trace(go.Scatter(
            x=df_merged["DateTime"], y=df_merged["RS_SMA"],
            mode="lines", name=f"RS SMA {sma_period}",
            line=dict(color="#d32f2f", width=2, dash='dash')
        ))
        fig.update_layout(
            title=f"Relative Strength: {symbol} vs {index_choice}",
            xaxis_title="Date",
            yaxis_title="Relative Strength",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=500,
            template="plotly_white",
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.info(
            f"Relative Strength = Symbol Close / Index Close × 100\n\n"
            f"Blue: Raw RS, Red Dashed: SMA({sma_period}) of RS"
        )
    except Exception as e:
        st.error(f"Error fetching or calculating Relative Strength: {e}")
