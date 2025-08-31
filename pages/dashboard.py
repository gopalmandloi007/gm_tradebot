# pages/dashboard.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import plotly.express as px
import plotly.graph_objects as go

def show_dashboard():
    st.header("📊 Trading Dashboard — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    try:
        # Fetch Holdings
        holdings_resp = client.holdings()
        if holdings_resp.get("status") != "SUCCESS":
            st.error(f"⚠️ Holdings fetch failed: {holdings_resp.get('message')}")
            return

        holdings_data = holdings_resp.get("data", [])
        if not holdings_data:
            st.info("✅ No holdings found.")
            return

        # Prepare NSE holdings
        nse_holdings = []
        for item in holdings_data:
            for ts in item.get("tradingsymbol", []):
                if ts.get("exchange") == "NSE":
                    nse_holdings.append({
                        "symbol": ts["tradingsymbol"],
                        "token": ts["token"],
                        "lotsize": int(ts["lotsize"]),
                        "avg_buy_price": float(item["avg_buy_price"]),
                        "qty": int(item.get("t1_qty", 0) + item.get("dp_qty",0) + item.get("unpledged_qty",0))
                    })
        if not nse_holdings:
            st.info("✅ No NSE holdings found.")
            return

        df_holdings = pd.DataFrame(nse_holdings)

        # Fetch LTP & Previous Close using historical CSV
        ltp_list = []
        prev_close_list = []
        today_pnl_list = []
        overall_pnl_list = []
        current_value_list = []
        invested_value_list = []

        total_capital = 1_400_000  # default capital for pie chart
        total_invested = 0
        total_current = 0

        for idx, row in df_holdings.iterrows():
            token = row["token"]
            symbol = row["symbol"]
            qty = row["qty"]
            avg_buy = row["avg_buy_price"]

            # Current quote (LTP)
            quote_resp = client.get_quotes(exchange="NSE", token=token)
            if quote_resp.get("status") != "SUCCESS":
                ltp = 0
            else:
                ltp = float(quote_resp.get("ltp", 0))
            ltp_list.append(ltp)

            # Historical for previous close
            today = datetime.now()
            frm_date = (today - timedelta(days=7)).strftime("%d%m%Y0000")
            to_date = today.strftime("%d%m%Y2359")
            hist_csv = client.historical_csv(segment="NSE", token=token, timeframe="day", frm=frm_date, to=to_date)
            hist_df = pd.read_csv(io.StringIO(hist_csv), header=None)
            # daily CSV: Dateandtime, Open, High, Low, Close, Volume, OI(optional)
            hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume", "OI"] if hist_df.shape[1]>=6 else ["DateTime", "Open", "High", "Low", "Close", "Volume"]
            hist_df["DateTime"] = pd.to_datetime(hist_df["DateTime"])
            hist_df = hist_df.sort_values("DateTime")
            prev_close = float(hist_df["Close"].iloc[-2]) if len(hist_df) > 1 else float(hist_df["Close"].iloc[-1])
            prev_close_list.append(prev_close)

            invested = avg_buy * qty
            current_val = ltp * qty
            invested_value_list.append(invested)
            current_value_list.append(current_val)

            today_pnl_list.append((ltp - prev_close) * qty)
            overall_pnl_list.append((ltp - avg_buy) * qty)

            total_invested += invested
            total_current += current_val

        df_holdings["LTP"] = ltp_list
        df_holdings["Prev_Close"] = prev_close_list
        df_holdings["Invested_Value"] = invested_value_list
        df_holdings["Current_Value"] = current_value_list
        df_holdings["Today_PnL"] = today_pnl_list
        df_holdings["Overall_PnL"] = overall_pnl_list
        df_holdings["%Capital_Alloc"] = df_holdings["Invested_Value"] / total_capital * 100

        # Overall Summary
        st.subheader("💰 Overall Summary")
        st.write(f"**Total Invested Value:** ₹{total_invested:,.2f}")
        st.write(f"**Total Current Value:** ₹{total_current:,.2f}")
        st.write(f"**Today P&L:** ₹{sum(today_pnl_list):,.2f}")
        st.write(f"**Overall P&L:** ₹{sum(overall_pnl_list):,.2f}")

        # Holdings table
        st.subheader("📝 Holdings Details")
        st.dataframe(df_holdings[["symbol","qty","avg_buy_price","LTP","Prev_Close","Invested_Value","Current_Value","Today_PnL","Overall_PnL","%Capital_Alloc"]],
                     use_container_width=True)

        # Capital Allocation Pie Chart
        st.subheader("📊 Capital Allocation")
        fig_pie = px.pie(df_holdings, names="symbol", values="%Capital_Alloc", title="Capital Allocation %")
        st.plotly_chart(fig_pie, use_container_width=True)

        # Candlestick Chart for selected symbol
        st.subheader("📈 Candlestick Chart")
        selected_symbol = st.selectbox("Select Symbol for Chart", df_holdings["symbol"].tolist())
        chart_row = df_holdings[df_holdings["symbol"]==selected_symbol].iloc[0]
        token_chart = chart_row["token"]
        hist_csv_chart = client.historical_csv(segment="NSE", token=token_chart, timeframe="day", frm=frm_date, to=to_date)
        hist_df_chart = pd.read_csv(io.StringIO(hist_csv_chart), header=None)
        hist_df_chart.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume", "OI"] if hist_df_chart.shape[1]>=6 else ["DateTime", "Open", "High", "Low", "Close", "Volume"]
        hist_df_chart["DateTime"] = pd.to_datetime(hist_df_chart["DateTime"])
        hist_df_chart = hist_df_chart.sort_values("DateTime")

        fig_candle = go.Figure(data=[go.Candlestick(
            x=hist_df_chart["DateTime"],
            open=hist_df_chart["Open"],
            high=hist_df_chart["High"],
            low=hist_df_chart["Low"],
            close=hist_df_chart["Close"]
        )])
        fig_candle.update_layout(title=f"{selected_symbol} Candlestick Chart", xaxis_title="Date", yaxis_title="Price")
        st.plotly_chart(fig_candle, use_container_width=True)

    except Exception as e:
        st.error(f"⚠️ Dashboard fetch failed: {e}")
        import traceback
        st.text(traceback.format_exc())
        
