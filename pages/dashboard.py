# pages/dashboard.py
import streamlit as st
import pandas as pd
import datetime
import io
import plotly.graph_objects as go

DEFAULT_TOTAL_CAPITAL = 1_400_000  # Default capital for % allocation

def show_dashboard():
    st.header("📊 Trading Dashboard — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    try:
        # --- Fetch Holdings ---
        resp = client.get_holdings()
        if not resp or resp.get("status") != "SUCCESS":
            st.warning("⚠️ No holdings found or API error.")
            return

        holdings_data = resp.get("data", [])
        nse_holdings = []

        for item in holdings_data:
            for ts in item.get("tradingsymbol", []):
                if ts.get("exchange") == "NSE":
                    nse_holdings.append({
                        "tradingsymbol": ts.get("tradingsymbol"),
                        "token": ts.get("token"),
                        "avg_buy_price": float(item.get("avg_buy_price", 0)),
                        "total_qty": int(item.get("t1_qty", 0)) + int(item.get("dp_qty", 0)),
                        "remarks": ""
                    })

        if not nse_holdings:
            st.info("✅ No NSE holdings found.")
            return

        # --- Fetch LTP and previous close ---
        for h in nse_holdings:
            quote = client.get_quotes(exchange="NSE", token=h["token"])
            if quote.get("status") == "SUCCESS":
                h["ltp"] = float(quote.get("ltp", 0))
                h["previous_close"] = float(quote.get("day_open", 0))  # Using day_open as previous close approximation
            else:
                h["ltp"] = 0
                h["previous_close"] = 0

            h["invested_value"] = h["avg_buy_price"] * h["total_qty"]
            h["current_value"] = h["ltp"] * h["total_qty"]
            h["today_pnl"] = (h["ltp"] - h["previous_close"]) * h["total_qty"]
            h["overall_pnl"] = h["current_value"] - h["invested_value"]
            h["capital_pct"] = (h["invested_value"] / DEFAULT_TOTAL_CAPITAL) * 100

        df = pd.DataFrame(nse_holdings)

        # --- Overall Summary ---
        overall_invested = df["invested_value"].sum()
        overall_current = df["current_value"].sum()
        overall_today_pnl = df["today_pnl"].sum()
        overall_pnl = df["overall_pnl"].sum()

        st.subheader("💰 Overall Summary")
        st.metric("Total Invested Value", f"₹{overall_invested:,.2f}")
        st.metric("Total Current Value", f"₹{overall_current:,.2f}")
        st.metric("Today P&L", f"₹{overall_today_pnl:,.2f}")
        st.metric("Overall P&L", f"₹{overall_pnl:,.2f}")

        # --- Editable Table for Holdings ---
        st.subheader("📝 Holdings Details")
        edited_df = st.data_editor(
            df[["tradingsymbol", "total_qty", "avg_buy_price", "ltp",
                "previous_close", "invested_value", "current_value",
                "today_pnl", "overall_pnl", "capital_pct", "remarks"]],
            num_rows="dynamic",
            use_container_width=True
        )

        # --- Pie Chart for Capital Allocation ---
        st.subheader("📊 Capital Allocation")
        fig_pie = go.Figure(go.Pie(
            labels=edited_df["tradingsymbol"],
            values=edited_df["capital_pct"],
            hoverinfo="label+percent+value",
            textinfo="label+percent"
        ))
        st.plotly_chart(fig_pie, use_container_width=True)

        # --- Candlestick Chart ---
        st.subheader("📈 Candlestick Chart")
        symbol_selected = st.selectbox("Select Symbol for Chart", edited_df["tradingsymbol"])
        token_selected = edited_df.loc[edited_df["tradingsymbol"]==symbol_selected, "token"].values[0]

        # Historical Data
        to_date = datetime.datetime.now()
        from_date = to_date - datetime.timedelta(days=60)  # Last 60 days
        frm = from_date.strftime("%d%m%Y") + "0000"
        to = to_date.strftime("%d%m%Y") + "2359"

        hist_csv = client.historical_csv(segment="NSE", token=token_selected, timeframe="day", frm=frm, to=to)
        hist_df = pd.read_csv(io.StringIO(hist_csv), header=None)
        if hist_df.shape[1] == 7:  # Expected columns: Dateandtime, Open, High, Low, Close, Volume, OI
            hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume", "OI"]
            hist_df["DateTime"] = pd.to_datetime(hist_df["DateTime"])
            fig_candle = go.Figure(data=[go.Candlestick(
                x=hist_df["DateTime"],
                open=hist_df["Open"],
                high=hist_df["High"],
                low=hist_df["Low"],
                close=hist_df["Close"],
                name=symbol_selected
            )])
            fig_candle.update_layout(xaxis_rangeslider_visible=True)
            st.plotly_chart(fig_candle, use_container_width=True)
        else:
            st.warning("⚠️ Historical data format unexpected, cannot plot candlestick chart.")

    except Exception as e:
        st.error(f"⚠️ Dashboard fetch failed: {e}")
        st.stop()
        
