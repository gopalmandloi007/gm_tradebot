# pages/place_order.py
import streamlit as st
import pandas as pd
import requests, os, zipfile, io
import traceback
from definedge_api import DefinedgeClient

MASTER_FILE = "data/master/allmaster.csv"

# --- Load master symbols with correct headers ---
def load_master_symbols():
    os.makedirs("data/master", exist_ok=True)
    if not os.path.exists(MASTER_FILE):
        # Download master zip
        url = "https://app.definedgesecurities.com/public/allmaster.zip"
        zip_path = "data/master/allmaster.zip"
        r = requests.get(url, stream=True)
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(1024*32):
                f.write(chunk)
        # Extract CSV
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

# --- Show Place Order page ---
def show_place_order():
    st.header("🛒 Place Order — Definedge")

    client: DefinedgeClient = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    # Load symbols
    df_symbols = load_master_symbols()
    df_nse = df_symbols[df_symbols['SEGMENT'] == "NSE"]

    # --- Sidebar: Exchange radio button ---
    exchange = st.radio("Exchange", ["NSE", "BSE", "NFO", "MCX"], index=0)

    # --- Symbol selection by trading symbol ---
    symbol_list = df_nse['TRADINGSYM'].unique().tolist()
    selected_symbol = st.selectbox("Select Trading Symbol", symbol_list)

    # Get TOKEN for selected symbol
    token_row = df_nse[df_nse['TRADINGSYM'] == selected_symbol].iloc[0]
    token = str(token_row["TOKEN"])

    # --- Fetch current LTP ---
    ltp = 0.0
    try:
        quote_resp = client.get_quotes(exchange=exchange, token=token)
        ltp = float(quote_resp.get("ltp", 0))
    except:
        pass

    # --- Order form ---
    with st.form("place_order_form"):
        st.subheader("Order Details")

        price_type = st.radio("Price Type", ["MARKET", "LIMIT", "SL-LIMIT", "SL-MARKET"], index=0)
        order_type = st.radio("Order Type", ["BUY", "SELL"], index=0)
        product_type = st.selectbox("Product Type", ["CNC", "INTRADAY", "NORMAL"], index=2)

        # Price input (default LTP, editable)
        price = st.number_input("Price", min_value=0.0, step=0.05, value=ltp)

        # Quantity or amount
        qty_or_amt = st.radio("Place by", ["Quantity", "Amount"], index=0)
        quantity = 0
        if qty_or_amt == "Quantity":
            quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
        else:
            amount = st.number_input("Amount", min_value=0.0, step=1.0, value=ltp)
            quantity = int(amount // price) if price > 0 else 1

        trigger_price = st.number_input("Trigger Price (for SL orders)", min_value=0.0, step=0.05, value=0.0)
        validity = st.selectbox("Validity", ["DAY", "IOC", "EOS"], index=0)
        remarks = st.text_input("Remarks (optional)", "")

        submitted = st.form_submit_button("🚀 Place Order")

    if submitted:
        try:
            payload = {
                "exchange": exchange,
                "tradingsymbol": selected_symbol.strip(),
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
        
