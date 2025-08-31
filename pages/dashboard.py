# pages/dashboard.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import traceback

def show_dashboard():
    st.header("📊 Trading Dashboard — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        st.stop()

    debug = st.checkbox("Show debug info", value=False)

    try:
        # --- Step 1: Fetch Holdings ---
        holdings_resp = client.get_holdings()
        if not holdings_resp or holdings_resp.get("status") != "SUCCESS":
            st.error(f"Failed to fetch holdings. Response: {holdings_resp}")
            return

        holdings = holdings_resp.get("holdings", [])
        if not holdings:
            st.info("✅ No holdings found.")
            return

        # --- Step 2: Prepare DataFrame ---
        df = pd.DataFrame(holdings)
        # Ensure numeric fields
        df["quantity"] = df["quantity"].astype(float)
        df["average_price"] = df["average_price"].astype(float)

        # --- Step 3: Fetch LTP & Previous Close ---
        ltp_list = []
        prev_close_list = []
        today_pnl_list = []
        overall_pnl_list = []

        for idx, row in df.iterrows():
            exchange = row.get("exchange")
            token = row.get("token")
            quantity = row.get("quantity")
            avg_price = row.get("average_price")

            # Get latest quote
            quote_resp = client.get_quotes(exchange, token)
            ltp = float(quote_resp.get("ltp") or 0)
            ltp_list.append(ltp)

            # Previous close: use historical daily data
            today_date = datetime.now().strftime("%d%m%Y%H%M")
            prev_date = (datetime.now() - timedelta(days=1)).strftime("%d%m%Y%H%M")
            hist_csv = client.historical_csv(
                segment=exchange,
                token=token,
                timeframe="day",
                frm=prev_date,
                to=today_date
            )
            hist_df = pd.read_csv(pd.compat.StringIO(hist_csv), header=None,
                                  names=["datetime","open","high","low","close","volume","oi"])
            prev_close = float(hist_df["close"].iloc[-2]) if len(hist_df) > 1 else float(hist_df["close"].iloc[-1])
            prev_close_list.append(prev_close)

            # Today PnL = (ltp - prev_close) * quantity
            today_pnl = (ltp - prev_close) * quantity
            today_pnl_list.append(today_pnl)

            # Overall PnL = (ltp - avg_price) * quantity
            overall_pnl = (ltp - avg_price) * quantity
            overall_pnl_list.append(overall_pnl)

        df["ltp"] = ltp_list
        df["prev_close"] = prev_close_list
        df["today_pnl"] = today_pnl_list
        df["overall_pnl"] = overall_pnl_list

        # --- Step 4: Top Summary ---
        total_investment = (df["average_price"] * df["quantity"]).sum()
        total_current_value = (df["ltp"] * df["quantity"]).sum()
        total_today_pnl = df["today_pnl"].sum()
        total_overall_pnl = df["overall_pnl"].sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Total Investment", f"{total_investment:.2f}")
        col2.metric("📈 Current Value", f"{total_current_value:.2f}")
        col3.metric("📊 Today PnL", f"{total_today_pnl:.2f}")
        col4.metric("🏦 Overall PnL", f"{total_overall_pnl:.2f}")

        # --- Step 5: Display Holdings Table ---
        st.subheader("🔹 Individual Holdings")
        display_cols = ["tradingsymbol", "exchange", "quantity", "average_price",
                        "ltp", "prev_close", "today_pnl", "overall_pnl"]
        st.dataframe(df[display_cols].sort_values(by="overall_pnl", ascending=False), use_container_width=True)

        # CSV Export
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Holdings CSV", csv, "holdings_dashboard.csv", "text/csv")

        if debug:
            st.write("🔎 Debug: Raw holdings with quotes and PnL")
            st.dataframe(df)

    except Exception as e:
        st.error(f"🚨 Dashboard generation failed: {e}")
        st.text(traceback.format_exc())
