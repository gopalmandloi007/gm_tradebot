# pages/dashboard.py
import streamlit as st
import pandas as pd
import datetime
from io import StringIO
import plotly.express as px
import plotly.graph_objects as go

def show_dashboard():
    st.header("📊 Trading Dashboard — Definedge")
    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    try:
        # --- Fetch Holdings ---
        holdings_resp = client.get_holdings()
        if not holdings_resp or holdings_resp.get("status") != "SUCCESS":
            st.warning("⚠️ No holdings found or API error.")
            return

        holdings_data = holdings_resp.get("data", [])

        # Only NSE tradingsymbols
        nse_holdings = []
        for item in holdings_data:
            for sym in item.get("tradingsymbol", []):
                if sym.get("exchange") == "NSE":
                    qty = (
                        int(item.get("t1_qty", "0")) +
                        int(item.get("dp_qty", "0")) +
                        int(item.get("unpledged_qty", "0"))
                    )
                    if qty > 0:
                        nse_holdings.append({
                            "symbol": sym.get("tradingsymbol"),
                            "token": sym.get("token"),
                            "avg_buy_price": float(item.get("avg_buy_price", 0)),
                            "qty": qty
                        })

        if not nse_holdings:
            st.info("✅ No NSE holdings found.")
            return

        # --- Fetch LTP and Previous Close ---
        for h in nse_holdings:
            token = h["token"]
            quote_resp = client.get_quotes(exchange="NSE", token=token)
            if quote_resp.get("status") == "SUCCESS":
                h["ltp"] = float(quote_resp.get("ltp", 0))
                h["previous_close"] = float(quote_resp.get("day_close", quote_resp.get("ltp", 0)))  # fallback
            else:
                h["ltp"] = 0
                h["previous_close"] = 0

        df = pd.DataFrame(nse_holdings)

        # --- Compute Values ---
        df["current_value"] = df["ltp"] * df["qty"]
        df["invested_value"] = df["avg_buy_price"] * df["qty"]
        df["today_pnl"] = (df["ltp"] - df["previous_close"]) * df["qty"]
        df["overall_pnl"] = df["current_value"] - df["invested_value"]

        # Overall summary
        total_invested = df["invested_value"].sum()
        total_current = df["current_value"].sum()
        total_today_pnl = df["today_pnl"].sum()
        total_overall_pnl = df["overall_pnl"].sum()

        st.subheader("💰 Overall Summary")
        st.metric("Total Invested Value", f"₹{total_invested:,.2f}")
        st.metric("Total Current Value", f"₹{total_current:,.2f}")
        st.metric("Today P&L", f"₹{total_today_pnl:,.2f}")
        st.metric("Overall P&L", f"₹{total_overall_pnl:,.2f}")

        # --- Editable Remarks ---
        st.subheader("📝 Update Remarks")
        for index, row in df.iterrows():
            remark = st.text_input(f"{row['symbol']} Remarks", key=f"remark_{row['symbol']}")

        # --- Capital Allocation Pie Chart ---
        st.subheader("📊 Capital Allocation")
        total_capital = 1400000  # default capital
        df["capital_pct"] = df["invested_value"] / total_capital * 100
        fig = px.pie(df, names="symbol", values="capital_pct",
                     title="Capital Allocation % (Based on Total Capital ₹1,400,000)")
        st.plotly_chart(fig, use_container_width=True)

        # --- Holdings Table ---
        st.subheader("📝 Holdings Details")
        display_cols = ["symbol", "qty", "avg_buy_price", "ltp", "previous_close",
                        "invested_value", "current_value", "today_pnl", "overall_pnl", "capital_pct"]
        st.dataframe(df[display_cols].round(2), use_container_width=True)

        # --- Candlestick Chart ---
        st.subheader("📈 Candlestick Chart")
        selected_symbol = st.selectbox("Select Symbol for Chart", df["symbol"].tolist())
        token = df.loc[df["symbol"]==selected_symbol, "token"].values[0]

        # Fetch historical daily data for last 60 days
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=90)
        frm = start_date.strftime("%d%m%Y0000")
        to = end_date.strftime("%d%m%Y2359")
        hist_csv = client.historical_csv(segment="NSE", token=token, timeframe="day", frm=frm, to=to)
        hist_df = pd.read_csv(StringIO(hist_csv), header=None)
        # Columns: Dateandtime, Open, High, Low, Close, Volume, OI
        if hist_df.shape[1] == 7:
            hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume", "OI"]
            hist_df["DateTime"] = pd.to_datetime(hist_df["DateTime"], format="%d-%m-%Y")
            fig2 = go.Figure(data=[go.Candlestick(
                x=hist_df["DateTime"],
                open=hist_df["Open"],
                high=hist_df["High"],
                low=hist_df["Low"],
                close=hist_df["Close"],
                name=selected_symbol
            )])
            fig2.update_layout(title=f"Candlestick Chart: {selected_symbol}",
                               xaxis_title="Date", yaxis_title="Price")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("⚠️ Historical data format incorrect or insufficient for candlestick chart.")

    except Exception as e:
        st.error(f"⚠️ Dashboard fetch failed: {e}")
        import traceback
        st.text(traceback.format_exc())
