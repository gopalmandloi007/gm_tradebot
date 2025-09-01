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

st.title("📈 Chart Viewer (OHLCV)")

client = st.session_state.get("client")
if not client:
    st.error("⚠️ Not logged in. Please login first from the Login page.")
    st.stop()

# Load master symbol list
df_master = load_master_symbols()

# UI for symbol selection
segment = st.selectbox("Exchange/Segment", sorted(df_master["SEGMENT"].unique()), index=0)
segment_symbols = df_master[df_master["SEGMENT"] == segment].sort_values("TRADINGSYM")
symbol = st.selectbox("Trading Symbol", segment_symbols["TRADINGSYM"].unique())
token_row = segment_symbols[segment_symbols["TRADINGSYM"] == symbol]
token = str(token_row["TOKEN"].iloc[0]) if not token_row.empty else None

days_back = st.slider("How many candles (days)?", min_value=20, max_value=250, value=70, step=1)

if st.button("Show Chart") and token:
    try:
        df = fetch_historical(client, segment, token, days_back)
        if df.empty:
            st.error("No data returned for selected symbol.")
        else:
            df = df.sort_values("DateTime")
            # OHLCV Chart
            fig = go.Figure()

            fig.add_trace(go.Candlestick(
                x=df["DateTime"],
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="OHLC",
                increasing_line_color='green',
                decreasing_line_color='red'
            ))

            # Add Volume as bar chart (secondary y-axis)
            fig.add_trace(go.Bar(
                x=df["DateTime"],
                y=df["Volume"],
                name="Volume",
                marker=dict(color="#636EFA"),
                opacity=0.3,
                yaxis='y2'
            ))

            fig.update_layout(
                title=f"{segment} : {symbol} ({token}) OHLCV Chart",
                xaxis=dict(title="Date", rangeslider=dict(visible=False)),
                yaxis=dict(title="Price"),
                yaxis2=dict(
                    title="Volume",
                    overlaying='y',
                    side='right',
                    showgrid=False,
                    position=1.0
                ),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=600,
                template="plotly_white",
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)

            st.info("OHLCV = Open, High, Low, Close, Volume. Use the controls above to select other stocks or timeframes.")

    except Exception as e:
        st.error(f"Error fetching chart data: {e}")
