# pages/place_order.py
import streamlit as st
import pandas as pd
import requests, os, zipfile, io, time
from definedge_api import DefinedgeClient
import traceback

MASTER_FILE = "data/master/allmaster.csv"

# ---- Load master CSV ----
def load_master_symbols():
    os.makedirs("data/master", exist_ok=True)
    if not os.path.exists(MASTER_FILE):
        url = "https://app.definedgesecurities.com/public/allmaster.zip"
        r = requests.get(url, stream=True)
        zip_path = "data/master/allmaster.zip"
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(1024*32):
                f.write(chunk)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("data/master")
        os.remove(zip_path)

    columns = [
        "SEGMENT", "TOKEN", "SYMBOL", "TRADINGSYM", "INSTRUMENT_TYPE",
        "EXPIRY", "TICKSIZE", "LOTSIZE", "OPTIONTYPE", "STRIKE",
        "PRICEPREC", "MULTIPLIER", "ISIN", "PRICEMULT", "COMPANY"
    ]
    df = pd.read_csv(MASTER_FILE, header=None, names=columns)
    return df

# ---- Fetch LTP ----
def fetch_ltp(client, exchange, token):
    try:
        resp = client.get_quotes(exchange, token)
        return float(resp.get("ltp", 0))
    except:
        return 0.0

# ---- Fetch limits ----
def fetch_limits(client):
    try:
        limits = client.api_get("/limits")
        cash_available = float(limits.get("cash", 0))
        return cash_available
    except:
        return 0.0

# ---- Fetch required margin ----
def fetch_margin(client, basket_list):
    try:
        payload = {"basketlists": basket_list}
        resp = client.api_post("/margin", payload)
        return resp.get("newMarginUsedAfterTrade", 0.0), resp.get("marginUsed", 0.0)
    except:
        return 0.0, 0.0

# ---- Place Order page ----
def show_place_order():
    st.header("🛒 Place Order — Definedge")

    client: DefinedgeClient = st.session_state.get("client")
    if not client:
        st.error("⚠️ Please login first via Login page.")
        return

    # --- Load symbols ---
    df_symbols = load_master_symbols()
    df_nse = df_symbols[df_symbols['SEGMENT'] == "NSE"]

    # --- Exchange ---
    exchange = st.radio("Exchange", ["NSE", "BSE", "NFO", "MCX"], index=0)

    # --- Trading Symbol ---
    symbol_list = df_nse['TRADINGSYM'].unique().tolist()
    selected_symbol = st.selectbox("Trading Symbol", symbol_list)
    token_row = df_nse[df_nse['TRADINGSYM'] == selected_symbol].iloc[0]
    token = str(token_row["TOKEN"])

    # --- LTP refresh container ---
    ltp_container = st.empty()
    price_input = st.empty()

    # --- Limits info container ---
    cash_container = st.empty()
    margin_container = st.empty()

    # --- Form ---
    with st.form("place_order_form"):
        st.subheader("Order Details")

        order_type = st.radio("Order Type", ["BUY", "SELL"], index=0)
        price_type = st.radio("Price Type", ["MARKET", "LIMIT", "SL-LIMIT", "SL-MARKET"], index=0)
        product_type = st.selectbox("Product Type", ["CNC", "INTRADAY", "NORMAL"], index=2)

        qty_or_amt = st.radio("Place by", ["Quantity", "Amount"], index=0)
        quantity = 0
        price_val = 0.0

        submitted = st.form_submit_button("🚀 Place Order")

    # --- Auto-refresh LTP ---
    for _ in range(1):  # run once at page load
        ltp = fetch_ltp(client, exchange, token)
        ltp_container.metric("LTP", ltp)
        if price_input:
            price_val = price_input.number_input("Price", min_value=0.0, step=0.05, value=ltp)
        cash_available = fetch_limits(client)
        cash_container.info(f"💰 Cash Available: ₹{cash_available:,.2f}")

        # Calculate margin for single order
        basket_list = [{
            "exchange": exchange,
            "tradingsymbol": selected_symbol,
            "quantity": 1,
            "price": str(price_val),
            "product_type": product_type,
            "order_type": order_type,
            "price_type": price_type
        }]
        total_margin, margin_used = fetch_margin(client, basket_list)
        margin_container.info(f"📊 Required Margin: ₹{total_margin:.2f}")

    # --- Calculate quantity if amount chosen ---
    if qty_or_amt == "Quantity":
        quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
    else:
        amount = st.number_input("Amount", min_value=0.0, step=1.0, value=price_val)
        quantity = int(amount // price_val) if price_val > 0 else 1

    # --- Place order ---
    if submitted:
        try:
            payload = {
                "exchange": exchange,
                "tradingsymbol": selected_symbol.strip(),
                "order_type": order_type,
                "price": str(price_val),
                "price_type": price_type,
                "product_type": product_type,
                "quantity": str(quantity),
                "validity": "DAY",
            }
            if price_type in ["SL-LIMIT", "SL-MARKET"]:
                trigger_price = st.number_input("Trigger Price (SL orders)", min_value=0.0, step=0.05, value=0.0)
                payload["trigger_price"] = str(trigger_price)

            st.json(payload)
            resp = client.place_order(payload)
            st.json(resp)
            if resp.get("status") == "SUCCESS":
                st.success(f"✅ Order placed successfully. Order ID: {resp.get('order_id')}")
            else:
                st.error(f"❌ Order placement failed. Response: {resp}")

        except Exception as e:
            st.error(f"Order placement failed: {e}")
            st.text(traceback.format_exc())
                
