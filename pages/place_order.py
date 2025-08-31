# pages/place_order.py
import streamlit as st
import pandas as pd
import io, os, zipfile
import requests
import traceback

from definedge_api import DefinedgeClient

MASTER_FILE = "data/master/allmaster.csv"

# --- Load master symbols ---
def load_master_symbols():
    os.makedirs("data/master", exist_ok=True)
    if not os.path.exists(MASTER_FILE):
        url = "https://app.definedgesecurities.com/public/allmaster.zip"
        zip_path = "data/master/allmaster.zip"
        r = requests.get(url, stream=True)
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(1024*32):
                f.write(chunk)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("data/master")
        os.remove(zip_path)
    df = pd.read_csv(MASTER_FILE)
    return df

def show_place_order():
    st.header("🛒 Place Order — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    # Load master symbols
    try:
        df_symbols = load_master_symbols()
    except Exception as e:
        st.error(f"Failed to load master symbols: {e}")
        return

    # Filter only NSE by default
    df_nse = df_symbols[df_symbols['SEGMENT'] == "NSE"]

    with st.form("place_order_form"):
        st.subheader("Order Details")

        exchange = st.radio("Exchange", ["NSE", "BSE", "NFO", "MCX"], index=0)
        
        # Symbol input with search by Trading Symbol
        trading_symbol_input = st.text_input("Trading Symbol", value="")
        df_filtered = df_nse[df_nse["TRADINGSYM"].str.contains(trading_symbol_input.upper(), na=False)]
        symbol_options = df_filtered["TRADINGSYM"].tolist()
        tradingsymbol = st.selectbox("Select Symbol", symbol_options) if symbol_options else st.text_input("Enter Symbol", "")

        # Get LTP from Definedge API for selected symbol
        ltp = 0.0
        try:
            token_row = df_nse[df_nse["TRADINGSYM"] == tradingsymbol].iloc[0]
            token = str(token_row["TOKEN"])
            quote = client.get_quotes(exchange=exchange, token=token)
            ltp = float(quote.get("ltp", 0))
        except Exception:
            ltp = 0.0

        price_type = st.radio("Price Type", ["MARKET", "LIMIT", "SL-LIMIT", "SL-MARKET"], index=0)
        price = st.number_input("Price", min_value=0.0, step=0.05, value=ltp)

        order_type = st.radio("Order Type", ["BUY", "SELL"], index=0)
        product_type = st.radio("Product Type", ["CNC", "INTRADAY", "NORMAL"], index=2)

        # Quantity or Amount input
        qty_or_amt = st.radio("Order by", ["Quantity", "Amount"], index=0)
        if qty_or_amt == "Quantity":
            quantity = st.number_input("Quantity", min_value=1, step=1, value=50)
            amount = 0
        else:
            amount = st.number_input("Amount", min_value=1.0, step=0.05, value=10000.0)
            quantity = int(amount / price) if price > 0 else 0

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
        
