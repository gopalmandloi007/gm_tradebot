# pages/dashboard.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import matplotlib.pyplot as plt
import traceback

def show_dashboard():
    st.header("📊 Trading Dashboard — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        st.stop()

    TOTAL_CAPITAL = 1400000  # Default total capital for allocation pie chart

    try:
        # 1️⃣ Fetch Holdings
        holdings_resp = client.get_holdings()
        if holdings_resp.get("status") != "SUCCESS":
            st.error("❌ Failed to fetch holdings")
            return
        holdings_data = holdings_resp.get("data", [])

        # Filter only NSE holdings and flatten
        rows = []
        for item in holdings_data:
            for sym in item.get("tradingsymbol", []):
                if sym.get("exchange") != "NSE":
                    continue
                row = {
                    "Symbol": sym.get("tradingsymbol"),
                    "Token": sym.get("token"),
                    "Qty": float(item.get("t1_qty") or 0),
                    "Avg_Buy": float(item.get("avg_buy_price") or 0),
                    "Remarks": "",
                }
                rows.append(row)
        if not rows:
            st.info("✅ No NSE holdings found.")
            return

        df = pd.DataFrame(rows)

        # 2️⃣ Fetch LTP and Historical Previous Close
        ltp_list, prev_close_list = [], []

        today = datetime.now()
        prev_day = today - timedelta(days=1)

        for idx, row in df.iterrows():
            token = row["Token"]

            # a) Latest quote for LTP
            quote_resp = client.get_quote(exchange="NSE", token=token)
            ltp = float(quote_resp.get("ltp", 0))
            ltp_list.append(ltp)

            # b) Historical previous close (adjusting for weekends/holidays)
            # We'll fetch last 5 trading days and pick last close < today
            from_date = (today - timedelta(days=7)).strftime("%d%m%Y%H%M")
            to_date = today.strftime("%d%m%Y%H%M")
            hist_csv = client.historical_csv("NSE", token, "day", from_date, to_date)
            hist_df = pd.read_csv(io.StringIO(hist_csv), header=None)
            hist_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume", "OI"]
            # Sort descending and find most recent previous close before today
            hist_df["DateTime"] = pd.to_datetime(hist_df["DateTime"], format="%d-%m-%Y")
            hist_df = hist_df.sort_values("DateTime", ascending=False)
            prev_close = hist_df.iloc[0]["Close"] if not hist_df.empty else 0
            prev_close_list.append(prev_close)

        df["LTP"] = ltp_list
        df["Prev_Close"] = prev_close_list

        # 3️⃣ Calculate Values
        df["Invested_Value"] = df["Qty"] * df["Avg_Buy"]
        df["Current_Value"] = df["Qty"] * df["LTP"]
        df["Today_PnL"] = (df["LTP"] - df["Prev_Close"]) * df["Qty"]
        df["Overall_PnL"] = df["Current_Value"] - df["Invested_Value"]
        df["%_Capital_Alloc"] = (df["Invested_Value"] / TOTAL_CAPITAL) * 100

        # 4️⃣ Editable Remarks
        for idx, row in df.iterrows():
            remark = st.text_input(f"Remarks for {row['Symbol']}", value=row["Remarks"], key=row['Symbol'])
            df.at[idx, "Remarks"] = remark

        # 5️⃣ Overall Summary
        st.subheader("📋 Overall Summary")
        total_invested = df["Invested_Value"].sum()
        total_current = df["Current_Value"].sum()
        total_today_pnl = df["Today_PnL"].sum()
        total_overall_pnl = df["Overall_PnL"].sum()

        st.metric("Total Invested Value", f"₹{total_invested:,.2f}")
        st.metric("Total Current Value", f"₹{total_current:,.2f}")
        st.metric("Today's PnL", f"₹{total_today_pnl:,.2f}")
        st.metric("Overall PnL", f"₹{total_overall_pnl:,.2f}")

        # 6️⃣ Individual Stock Table
        st.subheader("📝 Individual Stock Summary")
        st.dataframe(df[[
            "Symbol","Qty","Avg_Buy","Prev_Close","LTP",
            "Invested_Value","Current_Value","Today_PnL","Overall_PnL","%_Capital_Alloc","Remarks"
        ]].round(2), use_container_width=True)

        # 7️⃣ Pie Chart for Capital Allocation
        st.subheader("📊 Capital Allocation Pie Chart")
        fig, ax = plt.subplots()
        ax.pie(df["%_Capital_Alloc"], labels=df["Symbol"], autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
        st.pyplot(fig)

        # 8️⃣ Select Stock for Chart
        st.subheader("📈 Stock Charts")
        selected_symbol = st.selectbox("Select Symbol for Chart", df["Symbol"].tolist())
        token = df.loc[df["Symbol"]==selected_symbol, "Token"].values[0]

        # Fetch last 60 days for chart
        from_date = (today - timedelta(days=90)).strftime("%d%m%Y%H%M")
        to_date = today.strftime("%d%m%Y%H%M")
        hist_csv = client.historical_csv("NSE", token, "day", from_date, to_date)
        chart_df = pd.read_csv(io.StringIO(hist_csv), header=None)
        chart_df.columns = ["DateTime", "Open", "High", "Low", "Close", "Volume", "OI"]
        chart_df["DateTime"] = pd.to_datetime(chart_df["DateTime"], format="%d-%m-%Y")

        st.line_chart(chart_df.set_index("DateTime")["Close"])

    except Exception as e:
        st.error(f"⚠️ Dashboard fetch failed: {e}")
        st.text(traceback.format_exc())
        
