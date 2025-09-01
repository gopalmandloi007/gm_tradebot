import streamlit as st
import pandas as pd
import numpy as np
import io
import zipfile
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go

# ---- CONFIG ----
MASTER_URL = "https://app.definedgesecurities.com/public/allmaster.zip"
MASTER_FILE = "data/master/allmaster.csv"
SEGMENTS = ["NSE", "BSE", "NFO", "MCX"]

INDEX_TOKENS = {
    "Nifty 50": "256265",
    "Nifty 500": "999920005",
    "Nifty MidSmall 400": "999920388"
}

def download_and_extract_master():
    try:
        r = requests.get(MASTER_URL)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            csv_name = z.namelist()[0]
            with z.open(csv_name) as f:
                df = pd.read_csv(f, header=None)
        df.columns = ["SEGMENT","TOKEN","SYMBOL","TRADINGSYM","INSTRUMENT","EXPIRY",
                      "TICKSIZE","LOTSIZE","OPTIONTYPE","STRIKE","PRICEPREC","MULTIPLIER","ISIN","PRICEMULT","COMPANY"]
        import os
        os.makedirs("data/master", exist_ok=True)
        df.to_csv(MASTER_FILE, index=False)
        return df
    except Exception as e:
        st.error(f"Failed to download master file: {e}")
        return pd.DataFrame()

def load_master_symbols():
    try:
        df = pd.read_csv(MASTER_FILE)
        return df
    except:
        return download_and_extract_master()

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

def fetch_current_candle(client, exchange, token):
    try:
        q = client.get_quotes(exchange, str(token))
        o = float(q.get("day_open", np.nan))
        h = float(q.get("day_high", np.nan))
        l = float(q.get("day_low", np.nan))
        c = float(q.get("ltp", np.nan))
        v = float(q.get("volume", np.nan))
        dt = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)  # EOD
        return {"DateTime": dt, "Open": o, "High": h, "Low": l, "Close": c, "Volume": v}
    except Exception as e:
        return None

def calc_ema(df, period):
    return df['Close'].ewm(span=period, adjust=False).mean()

def calc_vol_sma(df, period):
    return df["Volume"].rolling(window=period).mean()

def fetch_benchmark(client, token, days):
    try:
        return fetch_historical(client, "NSE", token, days)
    except:
        return None

def calc_relative_strength(main_df, bench_df):
    merged = pd.merge(main_df[["DateTime", "Close"]], bench_df[["DateTime", "Close"]],
                      on="DateTime", suffixes=('', '_bench'))
    if len(merged) < 5:
        return None, None
    rs = merged["Close"] / merged["Close_bench"]
    rs = rs / rs.iloc[0]
    return merged["DateTime"], rs

st.markdown(
    "<h1 style='text-align:center; color:#2D9CDB;'>📈 Chart Viewer</h1>",
    unsafe_allow_html=True)

client = st.session_state.get("client")
if not client:
    st.error("⚠️ Not logged in. Please login first from the Login page.")
    st.stop()

df_symbols = load_master_symbols()
segment = st.selectbox("Exchange/Segment", SEGMENTS, index=0)
df_exch = df_symbols[df_symbols["SEGMENT"] == segment]
selected_symbol = st.selectbox("Trading Symbol", df_exch["TRADINGSYM"].tolist())
token_row = df_exch[df_exch["TRADINGSYM"] == selected_symbol]
token = int(token_row["TOKEN"].values[0]) if not token_row.empty else None

days = st.number_input("How many candles (days)?", min_value=20, max_value=250, value=70, step=1)

st.markdown("##### Overlay EMAs:")
col1, col2, col3, col4 = st.columns(4)
ema20 = col1.toggle("EMA 20", value=True)
ema50 = col2.toggle("EMA 50", value=False)
ema100 = col3.toggle("EMA 100", value=False)
ema200 = col4.toggle("EMA 200", value=False)
ema_periods = []
if ema20: ema_periods.append(20)
if ema50: ema_periods.append(50)
if ema100: ema_periods.append(100)
if ema200: ema_periods.append(200)

st.markdown("##### Volume & Volume SMA (20):")
show_volume = st.toggle("Show Volume", value=True)
show_volsma = st.toggle("Show Volume SMA 20", value=True)

st.markdown("##### Relative Strength:")
rs_bench = st.selectbox("Overlay RS against", ["None"] + list(INDEX_TOKENS.keys()), index=0)

if token:
    try:
        # 1. Fetch Historical Data
        hist_df = fetch_historical(client, segment, token, days)
        current = fetch_current_candle(client, segment, token)
        # Add current candle if not already present
        if current is not None:
            last_hist_date = hist_df.iloc[-1]["DateTime"].date() if not hist_df.empty else None
            if current["DateTime"].date() != last_hist_date:
                hist_df = pd.concat([hist_df, pd.DataFrame([current])], ignore_index=True)
        hist_df = hist_df.sort_values("DateTime").reset_index(drop=True)

        # 2. Calculate EMAs
        ema_lines = {}
        for p in ema_periods:
            ema_lines[p] = calc_ema(hist_df, p)

        # 3. Main Chart: Candlestick + EMA's
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=hist_df["DateTime"],
            open=hist_df["Open"],
            high=hist_df["High"],
            low=hist_df["Low"],
            close=hist_df["Close"],
            name="Price",
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
            showlegend=False
        ))
        colors = {20: "#1976d2", 50: "#d32f2f", 100: "#f57c00", 200: "#388e3c"}
        for p, ema in ema_lines.items():
            fig.add_trace(go.Scatter(
                x=hist_df["DateTime"], y=ema,
                name=f"EMA {p}", mode="lines", line=dict(width=2, color=colors.get(p, None)),
                showlegend=True
            ))
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=10,r=10,t=40,b=10),
            height=500,
            xaxis=dict(type="category", showgrid=False, tickfont=dict(size=12)),
            yaxis=dict(title="Price", showgrid=True, gridcolor="#444"),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        # 4. Volume chart below
        if show_volume or show_volsma:
            fig_vol = go.Figure()
            if show_volume:
                fig_vol.add_trace(go.Scatter(
                    x=hist_df["DateTime"], y=hist_df["Volume"],
                    name="Volume",
                    mode="lines", line=dict(width=1, color="#bdbdbd")
                ))
            if show_volsma:
                volsma = calc_vol_sma(hist_df, 20)
                fig_vol.add_trace(go.Scatter(
                    x=hist_df["DateTime"], y=volsma,
                    name="Volume SMA 20",
                    mode="lines", line=dict(width=2, color="#1976d2", dash='dot')
                ))
            fig_vol.update_layout(
                template="plotly_dark",
                title="Volume",
                margin=dict(l=10,r=10,t=40,b=10),
                height=200,
                xaxis=dict(type="category", showgrid=False, tickfont=dict(size=12)),
                yaxis=dict(title="Volume", showgrid=True, gridcolor="#444"),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_vol, use_container_width=True)

        # 5. Relative Strength chart below
        if rs_bench != "None":
            bench_token = INDEX_TOKENS.get(rs_bench)
            bench_df = fetch_benchmark(client, bench_token, days)
            if bench_df is not None:
                rs_x, rs_y = calc_relative_strength(hist_df, bench_df)
                if rs_x is not None:
                    fig_rs = go.Figure()
                    fig_rs.add_trace(go.Scatter(
                        x=rs_x, y=rs_y,
                        mode='lines', name=f"RS vs {rs_bench}",
                        line=dict(width=2, color="#F9A825")
                    ))
                    fig_rs.update_layout(
                        template="plotly_dark",
                        title=f"Relative Strength vs {rs_bench}",
                        margin=dict(l=10,r=10,t=40,b=10),
                        height=200,
                        xaxis=dict(type="category", showgrid=False, tickfont=dict(size=12)),
                        yaxis=dict(title="RS (Normalized)", showgrid=True, gridcolor="#444"),
                        showlegend=False,
                    )
                    st.plotly_chart(fig_rs, use_container_width=True)
                else:
                    st.info("Not enough data for Relative Strength calculation.")
            else:
                st.info("Benchmark data not found.")

    except Exception as e:
        st.error(f"Failed to fetch or display chart: {e}")
        st.info("Please ensure symbol has valid history and try again.")
