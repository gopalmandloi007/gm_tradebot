# pages/dashboard.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import traceback
import plotly.graph_objects as go

def show_dashboard():
    st.header("📊 Trading Dashboard — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from Login page.")
        st.stop()

    debug = st.checkbox("Show debug info", value=False)

    try:
        # 1️⃣ Fetch Holdings
        holdings_resp = client.get_holdings()
        if holdings_resp.get("status") != "SUCCESS":
            st.error(f"Failed to fetch holdings: {holdings_resp}")
            return

        holdings_data = holdings_resp.get("data", [])
        if not holdings_data:
            st.info("✅ No holdings found.")
            return

        # Flatten holdings (multiple tradingsymbol per holding)
        flat_rows = []
        for h in holdings_data:
            for ts in h.get("tradingsymbol", []):
                row = {
                    "Symbol": ts.get("tradingsymbol"),
                    "Exchange": ts.get("exchange"),
                    "Token": ts.get("token"),
                    "Qty": int(h.get("t1_qty", 0)) + int(h.get("dp_qty", 0)),
                    "Avg_Buy_Price": float(h.get("avg_buy_price", 0)),
                    "Lotsize": int(ts.get("lotsize", 1)),
                    "Remarks": ""
                }
                flat_rows.append(row)
        df = pd.DataFrame(flat_rows)

        if df.empty:
            st.info("✅ No valid holdings found.")
            return

        # 2️⃣ Fetch LTP for each symbol
        ltps = []
        prev_closes = []
        for idx, row in df.iterrows():
            try:
                quote = client.get_quote(row["Exchange"], row["Token"])
                ltp = float(quote.get("ltp", 0))
                ltps.append(ltp)

                # 3️⃣ Fetch Previous Close using Historical API (last available day)
                today = datetime.today()
                from_date = (today - timedelta(days=10)).strftime("%d%m%Y%H%M")
                to_date = today.strftime("%d%m%Y%H%M")
                hist_csv = client.get_historical(
                    segment=row["Exchange"],
                    token=row["Token"],
                    timeframe="day",
                    from_dt=from_date,
                    to_dt=to_date
                )
                hist_df = pd.read_csv(io.StringIO(hist_csv), header=None,
                                      names=["Date","Open","High","Low","Close","Volume","OI"])
                prev_close = hist_df["Close"].iloc[-2] if len(hist_df) > 1 else hist_df["Close"].iloc[-1]
                prev_closes.append(prev_close)

            except Exception as e:
                if debug:
                    st.warning(f"Failed fetching quote/historical for {row['Symbol']}: {e}")
                ltps.append(0)
                prev_closes.append(0)

        df["LTP"] = ltps
        df["Prev_Close"] = prev_closes

        # 4️⃣ Calculate PnL
        df["Today_PnL"] = (df["LTP"] - df["Prev_Close"]) * df["Qty"] * df["Lotsize"]
        df["Overall_PnL"] = (df["LTP"] - df["Avg_Buy_Price"]) * df["Qty"] * df["Lotsize"]

        # 5️⃣ Editable table for Remarks
        st.subheader("📋 Holdings Table")
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Remarks": st.column_config.TextColumn("Remarks", default=""),
            }
        )

        # 6️⃣ Show overall summary
        st.subheader("💰 Portfolio Summary")
        st.metric("Total Invested", f"₹{(df['Avg_Buy_Price']*df['Qty']*df['Lotsize']).sum():.2f}")
        st.metric("Current Value", f"₹{(df['LTP']*df['Qty']*df['Lotsize']).sum():.2f}")
        st.metric("Overall PnL", f"₹{df['Overall_PnL'].sum():.2f}")
        st.metric("Today's PnL", f"₹{df['Today_PnL'].sum():.2f}")

        # 7️⃣ Stock selection for charts
        st.subheader("📈 Stock Charts")
        selected_symbols = st.multiselect(
            "Select stocks to view charts",
            df["Symbol"].tolist()
        )
        for sym in selected_symbols:
            s_row = df[df["Symbol"]==sym].iloc[0]
            try:
                # Fetch last 100 days historical
                today = datetime.today()
                from_date = (today - timedelta(days=150)).strftime("%d%m%Y%H%M")
                to_date = today.strftime("%d%m%Y%H%M")
                hist_csv = client.get_historical(
                    segment=s_row["Exchange"],
                    token=s_row["Token"],
                    timeframe="day",
                    from_dt=from_date,
                    to_dt=to_date
                )
                hist_df = pd.read_csv(io.StringIO(hist_csv), header=None,
                                      names=["Date","Open","High","Low","Close","Volume","OI"])
                hist_df["Date"] = pd.to_datetime(hist_df["Date"])
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=hist_df["Date"],
                    open=hist_df["Open"],
                    high=hist_df["High"],
                    low=hist_df["Low"],
                    close=hist_df["Close"],
                    name=sym
                ))
                fig.add_trace(go.Scatter(
                    x=hist_df["Date"],
                    y=[s_row["Avg_Buy_Price"]]*len(hist_df),
                    mode="lines",
                    line=dict(color="blue", dash="dash"),
                    name="Avg Buy Price"
                ))
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                if debug:
                    st.warning(f"Failed chart for {sym}: {e}")

    except Exception as e:
        st.error(f"🚨 Dashboard failed: {e}")
        st.text(traceback.format_exc())
        
