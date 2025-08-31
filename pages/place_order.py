import streamlit as st
import traceback
import pandas as pd
import os
from definedge_api import DefinedgeClient
import time

MASTER_FILE_DIR = "data/master/"
MASTER_FILE = None

# Automatically detect master CSV file in data/master/
for f in os.listdir(MASTER_FILE_DIR):
    if f.lower().endswith(".csv"):
        MASTER_FILE = os.path.join(MASTER_FILE_DIR, f)
        break

def load_master_symbols(exchange_filter="NSE"):
    if not MASTER_FILE:
        return []
    df = pd.read_csv(MASTER_FILE, header=None)
    df.columns = ["SEGMENT", "TOKEN", "SYMBOL", "TRADINGSYM", "INST_TYPE",
                  "EXPIRY", "TICKSIZE", "LOTSIZE", "OPTIONTYPE", "STRIKE",
                  "PRICEPREC", "MULTIPLIER", "ISIN", "PRICEMULT", "COMPANY"]
    df = df[df["SEGMENT"] == exchange_filter]
    return df

def show():
    st.header("🛒 Place Order — Definedge")

    client: DefinedgeClient = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    # Load symbols
    df_symbols = load_master_symbols()
    if df_symbols.empty:
        st.warning("⚠️ Master file not found or empty. Please update master file first.")
        return

    symbols = df_symbols["TRADINGSYM"].tolist()

    with st.form("place_order_form"):
        st.subheader("Order Details")

        exchange = st.selectbox("Exchange", ["NSE", "BSE", "NFO", "MCX"], index=0)
        tradingsymbol = st.selectbox("Trading Symbol", symbols)

        # Default LTP fetch
        token = int(df_symbols[df_symbols["TRADINGSYM"]==tradingsymbol]["TOKEN"].values[0])
        try:
            quote_resp = client.get_quotes(exchange="NSE", token=str(token))
            ltp_default = float(quote_resp.get("ltp", 0))
        except:
            ltp_default = 0.0

        price = st.number_input("Price", min_value=0.0, step=0.05, value=ltp_default)

        order_type = st.selectbox("Order Type", ["BUY", "SELL"])
        product_type = st.selectbox("Product Type", ["CNC", "INTRADAY", "NORMAL"], index=2)
        price_type = st.selectbox("Price Type", ["MARKET", "LIMIT", "SL-LIMIT", "SL-MARKET"], index=0)
        quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
        trigger_price = st.number_input("Trigger Price (for SL orders)", min_value=0.0, step=0.05, value=0.0)
        validity = st.selectbox("Validity", ["DAY", "IOC", "EOS"], index=0)
        remarks = st.text_input("Remarks (optional)", "")

        submitted = st.form_submit_button("🚀 Place Order")

    if submitted:
        try:
            payload = {
                "exchange": exchange,
                "tradingsymbol": tradingsymbol.strip(),
                "order_type": order_type,
                "price": str(price),  # user's input
                "price_type": price_type,
                "product_type": product_type,
                "quantity": str(quantity),
                "validity": validity,
            }
            if trigger_price > 0:
                payload["trigger_price"] = str(trigger_price)
            if remarks:
                payload["remarks"] = remarks

            st.write("📦 Sending payload:")
            st.json(payload)

            resp = client.place_order(payload)
            st.write("📬 API Response:")
            st.json(resp)

            if resp.get("status") == "SUCCESS":
                st.success(f"✅ Order placed successfully. Order ID: {resp.get('order_id')}")
            else:
                st.error(f"❌ Order placement failed. Response: {resp}")

        except Exception as e:
            st.error(f"Order placement failed: {e}")
            st.text(traceback.format_exc())
