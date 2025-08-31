# pages/place_order.py
import streamlit as st
import pandas as pd
import os
import requests
import io
import traceback
from definedge_api import DefinedgeClient

# --- Path to store master file locally ---
MASTER_FILE_PATH = "data/master/allmaster.csv"
MASTER_FOLDER = "data/master/"

# --- Function to download master file ---
def download_master_file():
    os.makedirs(MASTER_FOLDER, exist_ok=True)
    url = "https://app.definedgesecurities.com/public/allmaster.zip"
    r = requests.get(url)
    r.raise_for_status()
    import zipfile, tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        tmpfile.write(r.content)
        tmpfile.flush()
        with zipfile.ZipFile(tmpfile.name, 'r') as zip_ref:
            zip_ref.extractall(MASTER_FOLDER)
    # The extracted file is usually named allmaster.csv
    return os.path.join(MASTER_FOLDER, "allmaster.csv")

# --- Load master symbols ---
@st.cache_data
def load_master_symbols():
    if not os.path.exists(MASTER_FILE_PATH):
        MASTER_FILE = download_master_file()
    else:
        MASTER_FILE = MASTER_FILE_PATH
    df = pd.read_csv(MASTER_FILE, header=None)
    # Definedge master columns
    df.columns = ["segment", "token", "symbol", "tradingsym", "instrument_type",
                  "expiry", "ticksize", "lotsize", "optiontype", "strike",
                  "priceprec", "multiplier", "isin", "pricemult", "company"]
    # Keep only NSE/BSE cash or FNO if needed
    df = df[df["segment"].isin(["NSE", "BSE", "NFO"])]
    return df

# --- Streamlit page ---
def show():
    st.header("🛒 Place Order — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    # Load master file
    try:
        df_symbols = load_master_symbols()
    except Exception as e:
        st.error(f"Failed to load master symbols: {e}")
        return

    with st.form("place_order_form"):
        st.subheader("Order Details")

        exchange = st.selectbox("Exchange", ["NSE", "BSE", "NFO", "MCX"], index=2)  # default NFO

        # Show trading symbol + company
        tradingsym_option = df_symbols.apply(lambda x: f"{x['tradingsym']} ({x['company']})", axis=1)
        selected_option = st.selectbox("Trading Symbol", tradingsym_option)
        selected_tradingsym = selected_option.split(" ")[0]
        token = df_symbols[df_symbols["tradingsym"] == selected_tradingsym]["token"].values[0]

        # Fetch LTP automatically
        ltp = 0.0
        try:
            quote = client.get_quotes(exchange=exchange, token=str(token))
            ltp = float(quote.get("ltp", 0))
        except Exception as e:
            st.warning(f"Failed to fetch LTP: {e}")

        # Price type radio
        price_type = st.radio("Price Type", ["MARKET", "LIMIT", "SL-LIMIT", "SL-MARKET"], index=0)
        price = st.number_input("Price", value=ltp if ltp>0 else 0.0, step=0.05, format="%.2f")

        # Quantity or Amount
        order_mode = st.radio("Order Mode", ["Quantity", "Amount"])
        if order_mode == "Quantity":
            quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
            amount = 0.0
        else:
            amount = st.number_input("Amount (₹)", min_value=1.0, step=0.05, value=ltp*1 if ltp>0 else 0.0)
            quantity = int(amount/price) if price>0 else 0

        order_type = st.selectbox("Order Type", ["BUY", "SELL"])
        product_type = st.selectbox("Product Type", ["CNC", "INTRADAY", "NORMAL"], index=2)
        trigger_price = st.number_input("Trigger Price (for SL orders)", min_value=0.0, step=0.05, value=0.0)
        validity = st.selectbox("Validity", ["DAY", "IOC", "EOS"], index=0)
        remarks = st.text_input("Remarks (optional)", "")

        submitted = st.form_submit_button("🚀 Place Order")

    if submitted:
        try:
            payload = {
                "exchange": exchange,
                "tradingsymbol": selected_tradingsym,
                "token": str(token),
                "order_type": order_type,
                "price": str(price),
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
        
