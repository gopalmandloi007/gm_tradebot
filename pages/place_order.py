# pages/place_order.py
import streamlit as st
import pandas as pd
import io
import zipfile
import requests
import time

MASTER_URL = "https://app.definedgesecurities.com/public/allmaster.zip"
MASTER_FILE = "data/master/allmaster.csv"

# ---- Load or update master file ----
def show_place_order():
    st.header("🛒 Place Order — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from Login page.")
        return

    df_symbols = load_master_symbols()

    # Use columns for a more compact, single-page feel
    col1, col2 = st.columns(2)

    with col1:
        exchange = st.radio("Exchange", ["NSE", "BSE", "NFO", "MCX"], index=0)
        df_exch = df_symbols[df_symbols["SEGMENT"] == exchange]
        selected_symbol = st.selectbox("Trading Symbol", df_exch["TRADINGSYM"].tolist())
        token_row = df_exch[df_exch["TRADINGSYM"] == selected_symbol]
        token = int(token_row["TOKEN"].values[0]) if not token_row.empty else None
        initial_ltp = fetch_ltp(client, exchange, token) if token else 0.0
        price_input = st.number_input("Price", min_value=0.0, step=0.05, value=initial_ltp)

    with col2:
        limits = client.api_get("/limits")
        cash_available = float(limits.get("cash", 0.0))
        st.info(f"💰 Cash Available: ₹{cash_available:,.2f}")

        if token:
            current_ltp = fetch_ltp(client, exchange, token)
            st.metric("📈 LTP", f"{current_ltp:.2f}")

    with st.form("place_order_form"):
        st.subheader("Order Details")
        order_type = st.radio("Order Type", ["BUY", "SELL"])
        price_type = st.radio("Price Type", ["LIMIT", "MARKET", "SL-LIMIT", "SL-MARKET"])
        product_type = st.selectbox("Product Type", ["NORMAL", "INTRADAY", "CNC"], index=2)
        place_by = st.radio("Place by", ["Quantity", "Amount"])
        quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
        amount = st.number_input("Amount", min_value=0.0, step=0.05, value=0.0)
        trigger_price = st.number_input("Trigger Price (for SL orders)", min_value=0.0, step=0.05, value=0.0)
        validity = st.selectbox("Validity", ["DAY", "IOC", "EOS"], index=0)
        remarks = st.text_input("Remarks (optional)", "")
        submitted = st.form_submit_button("🚀 Place Order")

    if submitted:
        if place_by == "Amount" and amount > 0 and initial_ltp > 0:
            quantity = int(amount // initial_ltp)

        payload = {
            "exchange": exchange,
            "tradingsymbol": selected_symbol,
            "order_type": order_type,
            "price": str(price_input),
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
