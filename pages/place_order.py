# pages/place_order.py
import streamlit as st
import pandas as pd
import io
import requests
from datetime import datetime
import threading
import time

MASTER_ZIP_URL = "https://app.definedgesecurities.com/public/allmaster.zip"

# -------------------- Helper Functions --------------------
def download_and_load_master():
    """Download master zip and return dataframe."""
    try:
        resp = requests.get(MASTER_ZIP_URL, timeout=30)
        resp.raise_for_status()
        from zipfile import ZipFile
        from io import BytesIO

        zipfile = ZipFile(BytesIO(resp.content))
        # allmaster.csv should be inside zip
        for name in zipfile.namelist():
            if name.endswith(".csv"):
                with zipfile.open(name) as f:
                    df = pd.read_csv(f, header=None)
                    df.columns = [
                        "SEGMENT", "TOKEN", "SYMBOL", "TRADINGSYM", "INSTRUMENT_TYPE",
                        "EXPIRY", "TICKSIZE", "LOTSIZE", "OPTIONTYPE", "STRIKE",
                        "PRICEPREC", "MULTIPLIER", "ISIN", "PRICEMULT", "COMPANY"
                    ]
                    return df
    except Exception as e:
        st.error(f"Failed to download/load master file: {e}")
        return pd.DataFrame()

def fetch_ltp(client, exchange, token):
    """Fetch LTP for given symbol."""
    try:
        resp = client.get_quotes(exchange, str(token))
        return float(resp.get("ltp", 0.0))
    except:
        return 0.0

def fetch_limits(client):
    """Fetch available cash from /limits API."""
    try:
        resp = client.api_get("/limits")
        cash = float(resp.get("cash", 0.0))
        return cash
    except:
        return 0.0

def fetch_margin(client, basket_list):
    """Fetch required margin for order."""
    try:
        payload = {"basketlists": basket_list}
        resp = client.api_post("/margin", payload)
        total_margin = resp.get("newMarginUsedAfterTrade", 0.0)
        margin_used = resp.get("marginUsed", 0.0)
        # safe conversion
        try:
            total_margin = float(total_margin) if total_margin else 0.0
        except:
            total_margin = 0.0
        try:
            margin_used = float(margin_used) if margin_used else 0.0
        except:
            margin_used = 0.0
        return total_margin, margin_used
    except:
        return 0.0, 0.0

# -------------------- Main Function --------------------
def show_place_order():
    st.header("🛒 Place Order — Definedge")
    
    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    # Download/load master
    df_symbols = download_and_load_master()
    if df_symbols.empty:
        st.warning("Master file not loaded yet. Retry after some time.")
        return

    # -------------------- Exchange Selection --------------------
    exchange = st.radio("Exchange", ["NSE", "BSE", "NFO", "MCX"], index=0)

    # Filter symbols by exchange
    df_exch = df_symbols[df_symbols["SEGMENT"] == exchange]
    trading_symbols = df_exch["TRADINGSYM"].tolist()

    # -------------------- Symbol Selection --------------------
    selected_symbol = st.selectbox("Trading Symbol", trading_symbols)

    # Get token for LTP
    token_row = df_exch[df_exch["TRADINGSYM"] == selected_symbol]
    token = token_row["TOKEN"].values[0] if not token_row.empty else None

    # -------------------- LTP Display --------------------
    ltp_container = st.empty()
    price_val = token_row["PRICEMULT"].values[0] if not token_row.empty else 0.0

    def refresh_ltp():
        while True:
            if token:
                ltp = fetch_ltp(client, exchange, token)
                ltp_container.metric("LTP", f"{ltp:.2f}")
            time.sleep(5)  # refresh every 5 seconds

    threading.Thread(target=refresh_ltp, daemon=True).start()

    # -------------------- Order Details --------------------
    st.subheader("Order Details")
    order_type = st.radio("Order Type", ["BUY", "SELL"], index=0)
    price_type = st.radio("Price Type", ["MARKET", "LIMIT", "SL-LIMIT", "SL-MARKET"], index=0)
    product_type = st.radio("Product Type", ["NORMAL", "CNC", "INTRADAY"], index=0)

    place_by = st.radio("Place by", ["Quantity", "Amount"], index=0)
    qty_val = st.number_input("Quantity", min_value=1, step=1, value=1)
    amt_val = st.number_input("Amount", min_value=0.0, step=0.01, value=0.0)
    price_input = st.number_input("Price", min_value=0.0, step=0.05, value=0.0)
    trigger_price = st.number_input("Trigger Price (for SL orders)", min_value=0.0, step=0.05, value=0.0)
    remarks = st.text_input("Remarks (optional)", "")

    # -------------------- Cash & Margin --------------------
    cash_available = fetch_limits(client)
    cash_container = st.empty()
    cash_container.info(f"💰 Cash Available: ₹{cash_available:,.2f}")

    # Estimate required margin
    basket_list = [{
        "exchange": exchange,
        "tradingsymbol": selected_symbol,
        "quantity": qty_val,
        "price": str(price_input if price_input > 0 else price_val),
        "product_type": product_type,
        "order_type": order_type,
        "price_type": price_type,
        "trigger_price": str(trigger_price) if trigger_price > 0 else None
    }]
    total_margin, margin_used = fetch_margin(client, basket_list)
    margin_container = st.empty()
    margin_container.info(f"📊 Required Margin: ₹{total_margin:,.2f}")

    # -------------------- Submit Button --------------------
    if st.button("🚀 Place Order"):
        payload = {
            "exchange": exchange,
            "tradingsymbol": selected_symbol,
            "order_type": order_type,
            "price": str(price_input if price_input > 0 else price_val),
            "price_type": price_type,
            "product_type": product_type,
            "quantity": str(qty_val),
        }
        if trigger_price > 0:
            payload["trigger_price"] = str(trigger_price)
        if remarks:
            payload["remarks"] = remarks

        st.write("📦 Sending payload:")
        st.json(payload)

        try:
            resp = client.place_order(payload)
            st.write("📬 API Response:")
            st.json(resp)
            if resp.get("status") == "SUCCESS":
                st.success(f"✅ Order placed successfully. Order ID: {resp.get('order_id')}")
            else:
                st.error(f"❌ Order placement failed. Response: {resp}")
        except Exception as e:
            st.error(f"Order placement failed: {e}")
    
