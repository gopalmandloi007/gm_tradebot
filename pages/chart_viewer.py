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

def select_symbol(df, label="Trading Symbol"):
    # Returns row of selected symbol (segment, token, etc.)
    symbol = st.selectbox(label, df["TRADINGSYM"].unique())
    row = df[df["TRADINGSYM"] == symbol].iloc[0]
    return row

def select_index_symbol(df, label="Index Symbol"):
    # Try to select index-like symbols: filter by common names or instrument
    index_candidates = df[
        df["INSTRUMENT"].str.contains("INDEX", case=False, na=False) |
        df["TRADINGSYM"].str.contains("NIFTY|IDX|SENSEX|BANKNIFTY|MIDSMALL|500|100", case=False, na=False)
    ].drop_duplicates("TRADINGSYM")
    # If none, fallback to all unique
    if index_candidates.empty:
        index_candidates = df
    index_symbol = st.selectbox(label, index_candidates["TRADINGSYM"].unique())
    row = index_candidates[index_candidates["TRADINGSYM"] == index_symbol].iloc[0]
    return row

def fetch_historical(client, segment, token, days):
    today = datetime.today()
    from_date = (today - timedelta(days=days*2)).strftime("%d%m%Y%H%M")
    to_date = today.strftime("%d%m%Y%H%M")
    hist_csv = client.historical_csv(segment=segment, token=token, timeframe="day", frm=from_date, to=to_date)
    if not hist_csv.strip():
        return pd.DataFrame()
    hist_df = pd.read_csv(io.StringIO(hist_csv), header=None)
    if hist_df.shape[1] == 7:
        hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume", "OI"]
    elif hist_df.shape[1] == 6:
        hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume"]
    else:
        return pd.DataFrame()
    hist_df["DateTime"] = pd.to_datetime(hist_df["DateTime"])
    hist_df = hist_df.sort_values("DateTime")
    hist_df = hist_df.drop_duplicates(subset=["DateTime"])
    hist_df = hist_df.tail(days)
    hist_df = hist_df.reset_index(drop=True)
    return hist_df

st.title("📈 Relative Strength Chart")

client = st.session_state.get("client")
if not client:
    st.error("⚠️ Not logged in. Please login first from the Login page.")
    st.stop()

df_master = load_master_symbols()

# Exchange filter for user convenience
segment = st.selectbox("Exchange/Segment", sorted(df_master["SEGMENT"].unique()), index=0)
segment_df = df_master[df_master["SEGMENT"] == segment]

# Symbol selection
st.markdown("#### Select Stock Symbol")
stock_row = select_symbol(segment_df, label="Stock Trading Symbol")

# Index selection, from same file (but let user select any symbol)
st.markdown("#### Select Index or Benchmark Symbol")
index_row = select_index_symbol(df_master, label="Index Trading Symbol")

days_back = st.number_input("Number of Days (candles)", min_value=20, max_value=250, value=55, step=1)
sma_period = st.number_input("RS SMA Period", min_value=2, max_value=55, value=20, step=1)

if st.button("Show Relative Strength Chart"):
    try:
        df_stock = fetch_historical(client, stock_row["SEGMENT"], stock_row["TOKEN"], days_back)
        if df_stock.empty:
            st.warning(f"No data for: {stock_row['TRADINGSYM']} ({stock_row['TOKEN']}, {stock_row['SEGMENT']})")
            st.stop()

        df_index = fetch_historical(client, index_row["SEGMENT"], index_row["TOKEN"], days_back)
        if df_index.empty:
            st.warning(f"No data for index: {index_row['TRADINGSYM']} ({index_row['TOKEN']}, {index_row['SEGMENT']})")
            st.stop()

        # Align and calculate RS
        df_stock = df_stock[["DateTime", "Close"]].rename(columns={"Close": "StockClose"})
        df_index = df_index[["DateTime", "Close"]].rename(columns={"Close": "IndexClose"})
        df_merged = pd.merge(df_stock, df_index, on="DateTime", how="inner")
        df_merged = df_merged.sort_values("DateTime").reset_index(drop=True)
        if df_merged.empty:
            st.warning("No overlapping dates between stock and index data.")
            st.stop()

        df_merged["RS"] = (df_merged["StockClose"] / df_merged["IndexClose"]) * 100
        df_merged["RS_SMA"] = df_merged["RS"].rolling(window=sma_period).mean()

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
            title=f"Relative Strength: {stock_row['TRADINGSYM']} vs {index_row['TRADINGSYM']}",
            xaxis_title="Date",
            yaxis_title="Relative Strength",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=500,
            template="plotly_white",
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)
        st.info(
            f"Relative Strength = Stock Close / Index Close × 100\n\n"
            f"Blue: Raw RS, Red Dashed: SMA({sma_period}) of RS"
        )
    except Exception as e:
        st.error(f"Error fetching/calculating Relative Strength: {e}")
