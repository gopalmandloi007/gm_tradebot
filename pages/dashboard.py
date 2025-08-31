# pages/dashboard.py
import streamlit as st
import pandas as pd
import datetime
from datetime import timedelta
import traceback
from io import StringIO  # for reading CSV from historical_csv

def show_dashboard():
    st.header("📊 Trading Dashboard — Definedge (NSE Only)")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    debug = st.checkbox("Show Debug Info", value=False)

    try:
        # 1️⃣ Fetch Holdings
        resp = client.get_holdings()
        if resp.get("status") != "SUCCESS":
            st.error(f"❌ Holdings API error: {resp.get('message', 'Unknown error')}")
            return

        holdings_data = resp.get("data", [])
        if not holdings_data:
            st.info("✅ No holdings found.")
            return

        # 2️⃣ Flatten holdings into tradingsymbol level (NSE only)
        flat_rows = []
        for h in holdings_data:
            qty_total = int(h.get("t1_qty", 0)) + int(h.get("dp_qty", 0))
            if qty_total == 0:
                continue
            for ts in h.get("tradingsymbol", []):
                if ts.get("exchange") != "NSE":
                    continue
                flat_rows.append({
                    "Symbol": ts.get("tradingsymbol"),
                    "Exchange": ts.get("exchange"),
                    "Token": ts.get("token"),
                    "Qty": qty_total,
                    "Avg_Buy_Price": float(h.get("avg_buy_price",0)),
                    "Lotsize": int(ts.get("lotsize",1)),
                    "Remarks": ""
                })

        if not flat_rows:
            st.info("✅ No NSE holdings with non-zero quantity found.")
            return

        df = pd.DataFrame(flat_rows)

        # 3️⃣ Fetch LTP and Previous Close
        ltp_list, prev_close_list = [], []

        for idx, row in df.iterrows():
            exchange = row["Exchange"]
            token = row["Token"]
            symbol = row["Symbol"]

            # --- Fetch LTP ---
            try:
                quote_resp = client.get_quotes(exchange, token)
                ltp = float(quote_resp.get("ltp", 0))
                ltp_list.append(ltp)
            except:
                ltp_list.append(None)

            # --- Fetch Previous Close from historical_csv ---
            try:
                today = datetime.datetime.now()
                frm = (today - timedelta(days=7)).strftime("%d%m%Y0000")
                to = today.strftime("%d%m%Y2359")

                hist_csv = client.historical_csv(
                    segment=exchange,
                    token=token,
                    timeframe="day",
                    frm=frm,
                    to=to
                )
                hist_df = pd.read_csv(StringIO(hist_csv),
                                      names=["DateTime","Open","High","Low","Close","Volume","OI"])
                # Use last available close before today as previous close
                prev_close = hist_df["Close"].iloc[-2] if len(hist_df)>=2 else hist_df["Close"].iloc[-1]
                prev_close_list.append(prev_close)
            except:
                prev_close_list.append(None)

        df["LTP"] = ltp_list
        df["Prev_Close"] = prev_close_list

        # 4️⃣ Calculate PnL
        df["Today_PnL"] = (df["LTP"] - df["Prev_Close"]) * df["Qty"]
        df["Overall_PnL"] = (df["LTP"] - df["Avg_Buy_Price"]) * df["Qty"]

        # 5️⃣ Show Dashboard Table
        st.subheader("📋 Holdings Overview")
        st.dataframe(df, use_container_width=True)
        st.markdown(f"**Overall PnL:** ₹{df['Overall_PnL'].sum():,.2f}")

        # 6️⃣ Editable Remarks Table
        st.subheader("📝 Update Remarks")
        for i, row in df.iterrows():
            remark = st.text_input(f"{row['Symbol']} Remarks", value=row.get("Remarks", ""), key=f"remark_{i}")
            df.at[i, "Remarks"] = remark

        # 7️⃣ Charts for selected stock
        st.subheader("📈 Stock Charts")
        selected_symbol = st.selectbox("Select Symbol for Chart", df["Symbol"].tolist())
        if selected_symbol:
            sel_row = df[df["Symbol"]==selected_symbol].iloc[0]
            try:
                token = sel_row["Token"]
                exchange = sel_row["Exchange"]
                today = datetime.datetime.now()
                frm = (today - timedelta(days=60)).strftime("%d%m%Y0000")
                to = today.strftime("%d%m%Y2359")
                hist_csv = client.historical_csv(
                    segment=exchange,
                    token=token,
                    timeframe="day",
                    frm=frm,
                    to=to
                )
                hist_df = pd.read_csv(StringIO(hist_csv),
                                      names=["DateTime","Open","High","Low","Close","Volume","OI"])
                hist_df["DateTime"] = pd.to_datetime(hist_df["DateTime"])
                st.line_chart(hist_df.set_index("DateTime")[["Close","High","Low"]])
            except Exception as e:
                st.error(f"Chart fetch failed: {e}")
                st.text(traceback.format_exc())

        # 8️⃣ CSV Export
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Dashboard CSV", csv, "dashboard.csv", "text/csv")

        if debug:
            st.write("🔎 Debug: Full Dashboard DataFrame")
            st.dataframe(df)

    except Exception as e:
        st.error(f"Dashboard generation failed: {e}")
        st.text(traceback.format_exc())
