# pages/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def show_dashboard():
    st.header("📊 Trading Dashboard — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    try:
        # Fetch Holdings
        holdings_resp = client.get_holdings()
        if not holdings_resp or holdings_resp.get("status") != "SUCCESS":
            st.error(f"⚠️ Holdings fetch failed: {holdings_resp.get('message')}")
            return

        holdings_data = holdings_resp.get("data", [])
        nse_holdings = []

        # Filter NSE holdings and flatten tradingsymbols
        for item in holdings_data:
            for ts in item.get("tradingsymbol", []):
                if ts.get("exchange") == "NSE":
                    nse_holdings.append({
                        "tradingsymbol": ts.get("tradingsymbol"),
                        "token": ts.get("token"),
                        "avg_buy_price": float(item.get("avg_buy_price", 0)),
                        "total_qty": int(item.get("t1_qty", 0) or 0),
                        "remarks": ""
                    })

        if not nse_holdings:
            st.info("✅ No NSE holdings found.")
            return

        df = pd.DataFrame(nse_holdings)

        # Fetch LTP and previous close
        ltp_list = []
        prev_close_list = []
        for idx, row in df.iterrows():
            try:
                quote_resp = client.get_quotes(exchange="NSE", token=row["token"])
                ltp = float(quote_resp.get("ltp", 0))
                ltp_list.append(ltp)

                # Historical previous day close (handle weekends/holidays)
                to_date = datetime.today()
                from_date = to_date - timedelta(days=7)  # last 7 days
                frm = from_date.strftime("%d%m%Y0000")
                to = to_date.strftime("%d%m%Y2359")
                hist_csv = client.historical_csv(segment="NSE", token=row["token"], timeframe="day", frm=frm, to=to)
                hist_df = pd.read_csv(pd.compat.StringIO(hist_csv), header=None)
                hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume"]
                hist_df["DateTime"] = pd.to_datetime(hist_df["DateTime"], errors='coerce')
                hist_df = hist_df.sort_values("DateTime")
                prev_close = hist_df["Close"].iloc[-2] if len(hist_df) > 1 else hist_df["Close"].iloc[-1]
                prev_close_list.append(prev_close)
            except Exception:
                ltp_list.append(0)
                prev_close_list.append(0)

        df["ltp"] = ltp_list
        df["previous_close"] = prev_close_list
        df["invested_value"] = df["avg_buy_price"] * df["total_qty"]
        df["current_value"] = df["ltp"] * df["total_qty"]
        df["today_pnl"] = (df["ltp"] - df["previous_close"]) * df["total_qty"]
        df["overall_pnl"] = (df["ltp"] - df["avg_buy_price"]) * df["total_qty"]

        TOTAL_CAPITAL = 1400000
        df["capital_pct"] = df["invested_value"] / TOTAL_CAPITAL * 100

        # Overall Summary
        st.subheader("💰 Overall Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Invested Value", f"₹{df['invested_value'].sum():,.2f}")
        col2.metric("Total Current Value", f"₹{df['current_value'].sum():,.2f}")
        col3.metric("Today P&L", f"₹{df['today_pnl'].sum():,.2f}")
        col4.metric("Overall P&L", f"₹{df['overall_pnl'].sum():,.2f}")

        # Holdings Table
        st.subheader("📝 Holdings Details")
        st.dataframe(df[["tradingsymbol", "total_qty", "avg_buy_price", "ltp", "previous_close",
                         "invested_value", "current_value", "today_pnl", "overall_pnl",
                         "capital_pct", "remarks"]], use_container_width=True)

        # Capital Allocation Pie Chart
        st.subheader("📊 Capital Allocation")
        fig_pie = px.pie(df, values="capital_pct", names="tradingsymbol",
                         title=f"Capital Allocation (% of ₹{TOTAL_CAPITAL:,})")
        st.plotly_chart(fig_pie, use_container_width=True)

        # Candlestick Chart
        st.subheader("📈 Candlestick Chart")
        symbol_selected = st.selectbox("Select Symbol for Chart", df["tradingsymbol"])
        token_row = df[df["tradingsymbol"] == symbol_selected]
        if not token_row.empty:
            token_selected = token_row["token"].values[0]
            try:
                to_date = datetime.today()
                from_date = to_date - timedelta(days=30)
                frm = from_date.strftime("%d%m%Y0000")
                to = to_date.strftime("%d%m%Y2359")
                hist_csv = client.historical_csv(segment="NSE", token=token_selected, timeframe="day", frm=frm, to=to)
                hist_df = pd.read_csv(pd.compat.StringIO(hist_csv), header=None)
                hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume"]
                hist_df["DateTime"] = pd.to_datetime(hist_df["DateTime"], errors='coerce')
                hist_df = hist_df.sort_values("DateTime")
                fig_candle = px.candlestick(hist_df, x="DateTime", open="Open", high="High", low="Low", close="Close",
                                            title=f"{symbol_selected} Candlestick Chart")
                st.plotly_chart(fig_candle, use_container_width=True)
            except Exception as e:
                st.warning(f"Chart fetch failed: {e}")
        else:
            st.warning(f"No token found for {symbol_selected}")

    except Exception as e:
        st.error(f"⚠️ Dashboard fetch failed: {e}")
        
