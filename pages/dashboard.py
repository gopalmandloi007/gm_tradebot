# pages/dashboard.py
import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
import plotly.graph_objects as go

DEFAULT_TOTAL_CAPITAL = 1400000  # Default capital for % allocation

def show_dashboard():
    st.header("📊 Trading Dashboard — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    try:
        # --- Step 1: Fetch holdings ---
        holdings_resp = client.get_holdings()
        if not holdings_resp or holdings_resp.get("status") != "SUCCESS":
            st.warning("⚠️ No holdings found or API error.")
            return

        holdings = holdings_resp.get("data", [])
        if not holdings:
            st.info("✅ No holdings found.")
            return

        # --- Step 2: Flatten holdings & filter NSE only ---
        rows = []
        for item in holdings:
            tradingsymbols = item.get("tradingsymbol", [])
            avg_buy_price = float(item.get("avg_buy_price", 0))
            dp_qty = float(item.get("dp_qty", 0))
            t1_qty = float(item.get("t1_qty", 0))
            holding_used = float(item.get("holding_used", 0))
            total_qty = dp_qty + t1_qty + holding_used
            for sym in tradingsymbols:
                if sym.get("exchange") != "NSE":
                    continue
                rows.append({
                    "symbol": sym.get("tradingsymbol"),
                    "token": sym.get("token"),
                    "avg_buy_price": avg_buy_price,
                    "quantity": total_qty
                })

        if not rows:
            st.warning("⚠️ No NSE holdings found.")
            return

        df = pd.DataFrame(rows)

        # --- Step 3: Fetch LTP & Previous Close ---
        ltp_list, prev_close_list = [], []
        today = datetime.today()

        for idx, row in df.iterrows():
            token = row["token"]
            quote_resp = client.get_quotes(exchange="NSE", token=token)
            ltp = float(quote_resp.get("ltp", 0))
            ltp_list.append(ltp)

            # Historical for previous close
            from_date = (today - timedelta(days=10)).strftime("%d%m%Y%H%M")
            to_date = today.strftime("%d%m%Y%H%M")
            hist_csv = client.historical_csv(segment="NSE", token=token, timeframe="day", frm=from_date, to=to_date)
            hist_df = pd.read_csv(io.StringIO(hist_csv), header=None)

            if hist_df.shape[1] == 7:
                hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume", "OI"]
            elif hist_df.shape[1] == 6:
                hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume"]
            else:
                st.warning(f"Unexpected columns in historical for {row['symbol']}: {hist_df.shape[1]}")

            hist_df["DateTime"] = pd.to_datetime(hist_df["DateTime"])
            hist_df = hist_df.sort_values("DateTime")
            prev_close = hist_df.iloc[-2]["Close"] if len(hist_df) >= 2 else hist_df.iloc[-1]["Close"]
            prev_close_list.append(float(prev_close))

        df["ltp"] = ltp_list
        df["prev_close"] = prev_close_list

        # --- Step 4: Compute PnL ---
        df["invested_value"] = df["avg_buy_price"] * df["quantity"]
        df["current_value"] = df["ltp"] * df["quantity"]
        df["today_pnl"] = (df["ltp"] - df["prev_close"]) * df["quantity"]
        df["overall_pnl"] = df["current_value"] - df["invested_value"]
        df["capital_allocation_%"] = (df["invested_value"] / DEFAULT_TOTAL_CAPITAL) * 100

        # --- Step 5: Display overall summary ---
        st.subheader("💰 Overall Summary")
        st.metric("Total Invested Value", f"₹{df['invested_value'].sum():,.2f}")
        st.metric("Total Current Value", f"₹{df['current_value'].sum():,.2f}")
        st.metric("Overall PnL", f"₹{df['overall_pnl'].sum():,.2f}")
        st.metric("Today PnL", f"₹{df['today_pnl'].sum():,.2f}")

        # --- Step 6: Editable Remarks ---
        st.subheader("📝 Update Remarks")
        remarks_dict = {}
        for sym in df["symbol"]:
            remarks_dict[sym] = st.text_input(f"{sym} Remarks", "")

        # --- Step 7: Show table with individual stock details ---
        st.subheader("📋 Individual Holdings Summary")
        st.dataframe(df[["symbol", "quantity", "avg_buy_price", "ltp", "prev_close",
                         "invested_value", "current_value", "today_pnl", "overall_pnl",
                         "capital_allocation_%"]], use_container_width=True)

        # --- Step 8: Pie chart for capital allocation ---
        st.subheader("📊 Capital Allocation (%)")
        cash_percent = 100 - df["capital_allocation_%"].sum()
        pie_df = df[["symbol", "capital_allocation_%"]].copy()
        pie_df = pie_df.append({"symbol": "Cash", "capital_allocation_%": cash_percent}, ignore_index=True)
        fig = go.Figure(data=[go.Pie(labels=pie_df["symbol"], values=pie_df["capital_allocation_%"], hole=0.3)])
        fig.update_traces(textinfo='label+percent', pull=[0.05]*len(pie_df))
        st.plotly_chart(fig, use_container_width=True)

        # --- Step 9: Candlestick chart with EMAs, Volume, RS ---
        st.subheader("📈 Candlestick Chart")
        selected_symbol = st.selectbox("Select Symbol for Chart", df["symbol"].tolist())
        token = df[df["symbol"] == selected_symbol]["token"].values[0]

        # User options
        days_options = st.selectbox("Select Chart Range (Days)", [30, 60, 90, 120, 180, 365], index=3)
        show_ema20 = st.checkbox("EMA 20", value=True)
        show_ema50 = st.checkbox("EMA 50", value=True)
        show_ema100 = st.checkbox("EMA 100", value=False)
        show_ema200 = st.checkbox("EMA 200", value=False)

        from_date = (today - timedelta(days=days_options)).strftime("%d%m%Y%H%M")
        to_date = today.strftime("%d%m%Y%H%M")
        hist_csv = client.historical_csv(segment="NSE", token=token, timeframe="day", frm=from_date, to=to_date)
        hist_df = pd.read_csv(io.StringIO(hist_csv), header=None)
        if hist_df.shape[1] == 7:
            hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume", "OI"]
        elif hist_df.shape[1] == 6:
            hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume"]
        hist_df["DateTime"] = pd.to_datetime(hist_df["DateTime"])
        hist_df = hist_df.sort_values("DateTime")

        fig_candle = go.Figure()

        # Candlestick
        fig_candle.add_trace(go.Candlestick(x=hist_df["DateTime"],
                                            open=hist_df["Open"],
                                            high=hist_df["High"],
                                            low=hist_df["Low"],
                                            close=hist_df["Close"],
                                            name=selected_symbol))
        # EMAs
        if show_ema20:
            hist_df["EMA20"] = hist_df["Close"].ewm(span=20, adjust=False).mean()
            fig_candle.add_trace(go.Scatter(x=hist_df["DateTime"], y=hist_df["EMA20"], line=dict(color='blue', width=1), name="EMA20"))
        if show_ema50:
            hist_df["EMA50"] = hist_df["Close"].ewm(span=50, adjust=False).mean()
            fig_candle.add_trace(go.Scatter(x=hist_df["DateTime"], y=hist_df["EMA50"], line=dict(color='green', width=1), name="EMA50"))
        if show_ema100:
            hist_df["EMA100"] = hist_df["Close"].ewm(span=100, adjust=False).mean()
            fig_candle.add_trace(go.Scatter(x=hist_df["DateTime"], y=hist_df["EMA100"], line=dict(color='orange', width=1), name="EMA100"))
        if show_ema200:
            hist_df["EMA200"] = hist_df["Close"].ewm(span=200, adjust=False).mean()
            fig_candle.add_trace(go.Scatter(x=hist_df["DateTime"], y=hist_df["EMA200"], line=dict(color='red', width=1), name="EMA200"))

        # Volume as bar chart secondary y-axis
        fig_candle.add_trace(go.Bar(x=hist_df["DateTime"], y=hist_df["Volume"], marker_color='lightgray', name="Volume", yaxis="y2"))

        fig_candle.update_layout(
            xaxis=dict(title='Date'),
            yaxis=dict(title='Price'),
            yaxis2=dict(title='Volume', overlaying='y', side='right', showgrid=False, position=0.15),
            legend=dict(x=0, y=1.15, orientation="h"),
            margin=dict(l=40, r=40, t=40, b=40),
            height=600,
            title=f"{selected_symbol} Candlestick Chart with Volume & EMAs"
        )
        st.plotly_chart(fig_candle, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Dashboard fetch failed: {e}")
        st.text(e)
