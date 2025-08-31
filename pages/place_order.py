# pages/place_order.py
import streamlit as st
import pandas as pd
import io
import requests
import os
import traceback
from definedge_api import DefinedgeClient

# --- Constants ---
MASTER_FOLDER = "data/master"
MASTER_FILE = os.path.join(MASTER_FOLDER, "nsecash.csv")

# --- Helper: Download master file ---
def download_master_file():
    os.makedirs(MASTER_FOLDER, exist_ok=True)
    url = "https://app.definedgesecurities.com/public/nsecash.zip"
    zip_path = os.path.join(MASTER_FOLDER, "nsecash.zip")

    try:
        # Download zip
        r = requests.get(url, stream=True, timeout=25)
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(1024 * 32):
                f.write(chunk)

        # Extract CSV
        import zipfile
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for file in zip_ref.namelist():
                if file.endswith(".csv"):
                    zip_ref.extract(file, MASTER_FOLDER)
                    os.rename(os.path.join(MASTER_FOLDER, file), MASTER_FILE)

        return True, f"Master file saved at {MASTER_FILE}"

    except Exception as e:
        return False, str(e)

# --- Helper: Load master symbols ---
def load_master_symbols():
    if not os.path.exists(MASTER_FILE):
        st.warning("Master file not found. Downloading...")
        success, msg = download_master_file()
        if not success:
            st.error(f"Failed to download master file: {msg}")
            return pd.DataFrame()
        else:
            st.success(msg)

    try:
        df = pd.read_csv(MASTER_FILE, header=None)
        # Ensure expected columns (adjust if needed)
        if df.shape[1] < 3:
            st.error("Master CSV format not correct!")
            return pd.DataFrame()
        df.columns = ["segment", "token", "symbol"] + [f"col{i}" for i in range(4, df.shape[1]+1)]
        df = df[df["segment"] == "NSE"]
        return df
    except Exception as e:
        st.error(f"Failed to read master CSV: {e}")
        return pd.DataFrame()

# --- Main place order function ---
def show_place_order():
    st.header("🛒 Place Order — Definedge")

    client: DefinedgeClient = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    # --- Load master symbols ---
    df_symbols = load_master_symbols()
    if df_symbols.empty:
        st.stop()

    with st.form("place_order_form"):
        st.subheader("Order Details")

        exchange = st.selectbox("Exchange", ["NSE", "BSE", "NFO", "MCX"], index=0)
        tradingsymbol = st.selectbox("Trading Symbol", df_symbols["symbol"].tolist())

        # Auto fetch LTP for selected symbol
        ltp = 0.0
        token = df_symbols[df_symbols["symbol"] == tradingsymbol]["token"].values[0]
        try:
            quote = client.get_quotes(exchange="NSE", token=str(token))
            ltp = float(quote.get("ltp", 0))
        except:
            ltp = 0.0

        price = st.number_input("Price", min_value=0.0, step=0.05, value=ltp)

        order_type = st.selectbox("Order Type", ["BUY", "SELL"])
        product_type = st.selectbox("Product Type", ["CNC", "INTRADAY", "NORMAL"], index=2)
        price_type = st.selectbox("Price Type", ["MARKET", "LIMIT", "SL-LIMIT", "SL-MARKET"], index=0)
        quantity = st.number_input("Quantity", min_value=1, step=1, value=50)
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
        
