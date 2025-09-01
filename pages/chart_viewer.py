import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

@st.cache_data
def load_master_symbols(master_csv_path="data/master/allmaster.csv"):
    df = pd.read_csv(master_csv_path)
    # Ensure proper columns
    # Columns: SEGMENT,TOKEN,SYMBOL,TRADINGSYM,INSTRUMENT,EXPIRY,TICKSIZE,LOTSIZE,OPTIONTYPE,STRIKE,PRICEPREC,MULTIPLIER,ISIN,PRICEMULT,COMPANY
    return df

def compute_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean().replace(0, 1e-10)
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(data, slow=26, fast=12, signal=9):
    ema_slow = data['Close'].ewm(span=slow, adjust=False).mean()
    ema_fast = data['Close'].ewm(span=fast, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def minervini_sell_signals(df, lookback_days=15):
    if len(df) < lookback_days:
        return {"error": "Insufficient data for analysis"}
    recent = df.tail(lookback_days).copy()
    recent['change'] = recent['Close'].pct_change() * 100
    recent['spread'] = recent['High'] - recent['Low']
    signals = {
        'up_days': 0,
        'down_days': 0,
        'up_day_percent': 0,
        'largest_up_day': 0,
        'largest_spread': 0,
        'exhaustion_gap': False,
        'high_volume_reversal': False,
        'churning': False,
        'heavy_volume_down': False,
        'warnings': []
    }
    for i in range(1, len(recent)):
        if recent['Close'].iloc[i] > recent['Close'].iloc[i-1]:
            signals['up_days'] += 1
        elif recent['Close'].iloc[i] < recent['Close'].iloc[i-1]:
            signals['down_days'] += 1
    signals['up_day_percent'] = (signals['up_days'] / lookback_days) * 100
    signals['largest_up_day'] = recent['change'].max()
    signals['largest_spread'] = recent['spread'].max()
    recent['gap_up'] = recent['Open'] > recent['High'].shift(1)
    recent['gap_down'] = recent['Open'] < recent['Low'].shift(1)
    recent['gap_filled'] = False
    for i in range(1, len(recent)):
        if recent['gap_up'].iloc[i]:
            if recent['Low'].iloc[i] <= recent['High'].shift(1).iloc[i]:
                recent.at[recent.index[i], 'gap_filled'] = True
                signals['exhaustion_gap'] = True
    avg_volume = recent['Volume'].mean()
    for i in range(1, len(recent)):
        if recent['Volume'].iloc[i] > avg_volume * 1.5:
            range_ = recent['High'].iloc[i] - recent['Low'].iloc[i]
            if (recent['High'].iloc[i] > recent['High'].iloc[i-1] and
                (recent['Close'].iloc[i] - recent['Low'].iloc[i]) < range_ * 0.25):
                signals['high_volume_reversal'] = True
                break
    if recent['Volume'].iloc[-1] > avg_volume * 1.8:
        price_change = abs(recent['Close'].iloc[-1] - recent['Open'].iloc[-1])
        if price_change < recent['spread'].iloc[-1] * 0.15:
            signals['churning'] = True
    if recent['Volume'].iloc[-1] > avg_volume * 1.5 and recent['change'].iloc[-1] < -3:
        signals['heavy_volume_down'] = True
    if signals['up_day_percent'] >= 70:
        signals['warnings'].append(
            f"⚠️ {signals['up_day_percent']:.0f}% up days ({signals['up_days']}/{lookback_days}) - Consider selling into strength"
        )
    if signals['largest_up_day'] > 5:
        signals['warnings'].append(
            f"⚠️ Largest up day: {signals['largest_up_day']:.2f}% - Potential climax run"
        )
    if signals['exhaustion_gap']:
        signals['warnings'].append("⚠️ Exhaustion gap detected - Potential reversal signal")
    if signals['high_volume_reversal']:
        signals['warnings'].append("⚠️ High-volume reversal - Institutional selling")
    if signals['churning']:
        signals['warnings'].append("⚠️ Churning detected (high volume, low progress) - Distribution likely")
    if signals['heavy_volume_down']:
        signals['warnings'].append("⚠️ Heavy volume down day - Consider exiting position")
    return signals

def minervini_high_vs_ema20_interpretation(high, ema20):
    if not isinstance(ema20, (int, float, np.floating)) or ema20 == 0 or pd.isnull(high) or pd.isnull(ema20):
        return "", ""
    diff_pct = ((high - ema20) / ema20) * 100
    diff_pct_rounded = round(diff_pct, 2)
    if diff_pct >= 50:
        interp = "🚨 Immediate Sell: High is 50%+ above 20 EMA"
    elif diff_pct >= 40:
        interp = "⚠️ Ready to Sell: High is 40%+ above 20 EMA"
    elif diff_pct >= 20:
        interp = "⚠️ Caution: High is 20%+ above 20 EMA"
    else:
        interp = "✅ Healthy: High is within reasonable range of 20 EMA"
    return diff_pct_rounded, interp

# --- Streamlit UI & Client Data ---
st.title("📈 Chart Viewer")

client = st.session_state.get("client")
if not client:
    st.error("⚠️ Not logged in. Please login first from the Login page.")
    st.stop()

# Load master symbols
df_master = load_master_symbols()

segment = st.selectbox("Exchange/Segment", sorted(df_master["SEGMENT"].unique()), index=0)
segment_symbols = df_master[df_master["SEGMENT"] == segment].sort_values("TRADINGSYM")
symbol = st.selectbox("Trading Symbol", segment_symbols["TRADINGSYM"].unique())
token_row = segment_symbols[segment_symbols["TRADINGSYM"] == symbol]
token = str(token_row["TOKEN"].iloc[0]) if not token_row.empty else None

days_back = st.slider("How many candles (days)?", min_value=20, max_value=250, value=70, step=1)

if st.button("Show Chart") and token:
    try:
        # --- Fetch data using your client-based method ---
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

        df = fetch_historical(client, segment, token, days_back)
        if df.empty:
            st.error("No data returned for selected symbol.")
        else:
            df = df.sort_values("DateTime")
            df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
            df['RSI'] = compute_rsi(df)
            macd, signal = compute_macd(df)
            df['MACD'] = macd
            df['Signal'] = signal

            show_ema = st.checkbox("Show EMAs", value=True)
            show_rsi = st.checkbox("Show RSI", value=True)
            show_macd = st.checkbox("Show MACD", value=True)

            rows_chart = 1 + int(show_rsi) + int(show_macd)
            specs = [[{"secondary_y": True}]] + [[{}]] * (rows_chart - 1)
            row_heights = [0.6] + [0.2] * (rows_chart - 1)
            fig = make_subplots(
                rows=rows_chart, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=row_heights,
                specs=specs
            )

            # Candlestick
            fig.add_trace(
                go.Candlestick(
                    x=df["DateTime"].dt.strftime('%Y-%m-%d'),
                    open=df["Open"],
                    high=df["High"],
                    low=df["Low"],
                    close=df["Close"],
                    name="Price"
                ),
                row=1, col=1
            )
            if show_ema:
                fig.add_trace(
                    go.Scatter(
                        x=df["DateTime"].dt.strftime('%Y-%m-%d'),
                        y=df["EMA20"],
                        mode="lines",
                        name="20 EMA",
                        line=dict(color="blue", width=1.5)
                    ),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(
                        x=df["DateTime"].dt.strftime('%Y-%m-%d'),
                        y=df["EMA50"],
                        mode="lines",
                        name="50 EMA",
                        line=dict(color="orange", width=1.5)
                    ),
                    row=1, col=1
                )
            if show_rsi:
                fig.add_trace(
                    go.Scatter(
                        x=df["DateTime"].dt.strftime('%Y-%m-%d'),
                        y=df["RSI"],
                        mode="lines",
                        name="RSI",
                        line=dict(color="purple", width=1.5)
                    ),
                    row=2, col=1 if rows_chart > 1 else 1
                )
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            if show_macd:
                row_macd = rows_chart if show_macd else 2
                fig.add_trace(
                    go.Bar(
                        x=df["DateTime"].dt.strftime('%Y-%m-%d'),
                        y=df["MACD"],
                        name="MACD",
                        marker_color=np.where(df['MACD'] > 0, 'green', 'red')
                    ),
                    row=row_macd, col=1
                )
                fig.add_trace(
                    go.Scatter(
                        x=df["DateTime"].dt.strftime('%Y-%m-%d'),
                        y=df["Signal"],
                        mode="lines",
                        name="Signal",
                        line=dict(color="blue", width=1.5)
                    ),
                    row=row_macd, col=1
                )
            fig.update_layout(
                height=600,
                title=f"{segment}:{symbol} Technical Analysis",
                showlegend=True,
                xaxis=dict(type="category"),
                xaxis_rangeslider_visible=False
            )
            st.plotly_chart(fig, use_container_width=True)

            # Minervini signals
            minervini_lookback = st.slider("Analysis Lookback (days)", 7, 30, 15, key="minervini_lookback")
            signals = minervini_sell_signals(df, minervini_lookback)
            if signals.get('error'):
                st.warning(signals['error'])
            else:
                st.markdown(f"#### Minervini Sell Signals Analysis")
                col1, col2, col3 = st.columns(3)
                col1.metric("Up Days", f"{signals['up_days']}/{minervini_lookback}")
                col2.metric("Up Day %", f"{signals['up_day_percent']:.1f}%")
                col3.metric("Largest Up Day", f"{signals['largest_up_day']:.2f}%")
                col4, col5, col6 = st.columns(3)
                col4.metric("Largest Spread", f"₹{signals['largest_spread']:.2f}")
                col5.metric("Exhaustion Gap", "Yes" if signals['exhaustion_gap'] else "No")
                col6.metric("Volume Reversal", "Yes" if signals['high_volume_reversal'] else "No")
                latest = df.iloc[-1]
                ema20 = latest['EMA20']
                high = latest['High']
                diff_pct, high_interp = minervini_high_vs_ema20_interpretation(high, ema20)
                col7, col8 = st.columns(2)
                col7.metric("Current High vs 20 EMA", f"{diff_pct:+.2f}%")
                col8.markdown(f"**{high_interp}**")
                if signals['warnings']:
                    st.error(f"🚨 Sell Signals Detected")
                    for warning in signals['warnings']:
                        st.write(f"- {warning}")
                else:
                    st.success("No strong sell signals detected")
    except Exception as e:
        st.error(f"Error fetching chart data: {e}")
