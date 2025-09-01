import streamlit as st
import pandas as pd
import numpy as np
import io
import zipfile
from datetime import datetime, timedelta
import requests
import plotly.graph_objects as go

# --- CONFIG ---
MASTER_URL = "https://app.definedgesecurities.com/public/allmaster.zip"
MASTER_FILE = "data/master/allmaster.csv"
NIFTY50_TOKEN = "256265"
NIFTY500_TOKEN = "999920005"
MIDSMALL400_TOKEN = "999920388"
SEGMENTS = ["NSE", "BSE", "NFO", "MCX"]

# --- UTILITIES ---
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
    from_date = (today - timedelta(days=days*2)).strftime("%d%m%Y%H%M")  # extra buffer for holidays
    to_date = today.strftime("%d%m%Y%H%M")
    hist_csv = client.historical_csv(segment=segment, token=token, timeframe="day", frm=from_date, to=to_date)
    hist_df = pd.read_csv(io.StringIO(hist_csv), header=None)
    if hist_df.shape[1] == 7:
        hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume", "OI"]
    elif hist_df.shape[1] == 6:
        hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume"]
    else:
        raise Exception(f"Unexpected columns in historical data: {hist_df.shape[1]}")
    hist_df["DateTime"] = pd.to_datetime(hist_df["DateTime"])
    hist_df = hist_df.sort_values("DateTime")
    # Remove duplicates and keep only last N trading days
    hist_df = hist_df.drop_duplicates(subset=["DateTime"])
    hist_df = hist_df.tail(days)
    hist_df = hist_df.reset_index(drop=True)
    return hist_df

def fetch_current_candle(client, exchange, token):
    # Fetch quote and build OHLCV row
    try:
        q = client.get_quotes(exchange, str(token))
        o = float(q.get("day_open", np.nan))
        h = float(q.get("day_high", np.nan))
        l = float(q.get("day_low", np.nan))
        c = float(q.get("ltp", np.nan))
        v = float(q.get("volume", np.nan))
        dt = datetime.now().replace(hour=15, minute=30, second=0, microsecond=0)
        return {"DateTime": dt, "Open": o, "High": h, "Low": l, "Close": c, "Volume": v}
    except Exception as e:
        st.warning(f"Failed to fetch current candle: {e}")
        return None

def overlay_ema(df, periods):
    emas = {}
    for p in periods:
        emas[p] = df['Close'].ewm(span=p, adjust=False).mean()
    return emas

def overlay_vol_sma(df, period):
    return df["Volume"].rolling(window=period).mean()

def calc_relative_strength(df, bench_df):
    # Simple ratio of close vs. benchmark close, normalized to 1 at start
    rs = df["Close"].values / bench_df["Close"].values
    return rs / rs[0]

def fetch_benchmark(client, benchmark, days):
    token_map = {
        "Nifty 50": NIFTY50_TOKEN,
        "Nifty 500": NIFTY500_TOKEN,
        "Nifty MidSmall 400": MIDSMALL400_TOKEN,
    }
    token = token_map.get(benchmark)
    if not token:
        return None
    return fetch_historical(client, "NSE", token, days)

# --- MAIN PAGE ---
def show_chart_viewer():
    st.header("📈 Chart Viewer")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    # --- 1. Symbol Selection ---
    df_symbols = load_master_symbols()
    segment = st.selectbox("Exchange/Segment", SEGMENTS, index=0)
    df_exch = df_symbols[df_symbols["SEGMENT"] == segment]

    selected_symbol = st.selectbox("Trading Symbol", df_exch["TRADINGSYM"].tolist())
    token_row = df_exch[df_exch["TRADINGSYM"] == selected_symbol]
    token = int(token_row["TOKEN"].values[0]) if not token_row.empty else None

    # --- 2. Candles/Days selection
    days = st.number_input("How many candles (days)?", min_value=20, max_value=250, value=70, step=1)

    # --- 3. Overlay options ---
    st.markdown("**Overlay EMAs:**")
    ema20 = st.checkbox("20 EMA", value=True)
    ema50 = st.checkbox("50 EMA")
    ema100 = st.checkbox("100 EMA")
    ema200 = st.checkbox("200 EMA")
    ema_periods = []
    if ema20: ema_periods.append(20)
    if ema50: ema_periods.append(50)
    if ema100: ema_periods.append(100)
    if ema200: ema_periods.append(200)

    st.markdown("**Volume & Volume SMA (20):**")
    show_volume = st.checkbox("Show Volume", value=True)
    show_volsma = st.checkbox("Show Volume SMA 20", value=True)

    st.markdown("**Relative Strength:**")
    rs_bench = st.selectbox("Overlay RS against", ["None", "Nifty 50", "Nifty 500", "Nifty MidSmall 400"], index=0)

    # --- 4. Fetch Data
    if token:
        try:
            hist_df = fetch_historical(client, segment, token, days)
            current = fetch_current_candle(client, segment, token)
            # If current day not present or not last, append it
            if current and (hist_df.empty or current["DateTime"].date() != hist_df.iloc[-1]["DateTime"].date()):
                hist_df = pd.concat([hist_df, pd.DataFrame([current])], ignore_index=True)
            hist_df = hist_df.sort_values("DateTime").reset_index(drop=True)

            # --- 5. Chart Building (Main OHLCV) ---
            fig = go.Figure()

            # Candlestick
            fig.add_trace(go.Candlestick(
                x=hist_df["DateTime"],
                open=hist_df["Open"],
                high=hist_df["High"],
                low=hist_df["Low"],
                close=hist_df["Close"],
                name=selected_symbol
            ))

            # --- EMA overlays ---
            if ema_periods:
                emas = overlay_ema(hist_df, ema_periods)
                for p, series in emas.items():
                    fig.add_trace(go.Scatter(
                        x=hist_df["DateTime"], y=series,
                        mode='lines', name=f"EMA {p}",
                        line=dict(width=1.5)
                    ))

            # --- Volume subplot ---
            if show_volume or show_volsma:
                fig.add_trace(go.Bar(
                    x=hist_df["DateTime"], y=hist_df["Volume"],
                    name="Volume", marker_color="rgba(150,150,255,0.3)", yaxis="y2"
                ))
                if show_volsma:
                    vol_sma = overlay_vol_sma(hist_df, 20)
                    fig.add_trace(go.Scatter(
                        x=hist_df["DateTime"], y=vol_sma,
                        mode='lines', name="Vol SMA 20",
                        yaxis="y2", line=dict(color="blue", width=1, dash="dash")
                    ))

            # --- Layout adjustments ---
            fig.update_layout(
                title=f"{selected_symbol} OHLCV Chart ({days} Days)",
                xaxis=dict(type="category", categoryorder="category ascending"),
                yaxis=dict(title="Price"),
                yaxis2=dict(title="Volume", overlaying="y", side="right", showgrid=False, showticklabels=False),
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

            # --- 6. Relative Strength Subplot ---
            if rs_bench != "None":
                bench_df = fetch_benchmark(client, rs_bench, days)
                # Align both by date
                if bench_df is not None:
                    merged = pd.merge(hist_df[["DateTime", "Close"]], bench_df[["DateTime", "Close"]],
                                      on="DateTime", suffixes=('', '_bench'))
                    if len(merged) > 5:
                        rs = merged["Close"] / merged["Close_bench"]
                        rs = rs / rs.iloc[0]
                        fig_rs = go.Figure()
                        fig_rs.add_trace(go.Scatter(
                            x=merged["DateTime"], y=rs,
                            mode='lines', name=f"RS vs {rs_bench}",
                            line=dict(width=2, color="orange")
                        ))
                        fig_rs.update_layout(
                            title=f"Relative Strength vs {rs_bench}",
                            yaxis=dict(title="RS Ratio (Normalized)"),
                            xaxis=dict(type="category"),
                            showlegend=True,
                            height=250
                        )
                        st.plotly_chart(fig_rs, use_container_width=True)
                    else:
                        st.info(f"Not enough data to compute RS against {rs_bench}.")

        except Exception as e:
            st.error(f"Failed to fetch or display chart: {e}")

# --- Page Entry Point ---
if __name__ == "__main__" or "chart_viewer" in st.session_state:
    show_chart_viewer()
