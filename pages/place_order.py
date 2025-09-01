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
def download_and_extract_master():
    try:
        r = requests.get(MASTER_URL)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            # Assuming first CSV in zip is the master
            csv_name = z.namelist()[0]
            with z.open(csv_name) as f:
                df = pd.read_csv(f, header=None)
        df.columns = ["SEGMENT","TOKEN","SYMBOL","TRADINGSYM","INSTRUMENT","EXPIRY",
                      "TICKSIZE","LOTSIZE","OPTIONTYPE","STRIKE","PRICEPREC","MULTIPLIER","ISIN","PRICEMULT","COMPANY"]
        # Save locally
        import os
        os.makedirs("data/master", exist_ok=True)
        df.to_csv(MASTER_FILE, index=False)
        return df
    except Exception as e:
        st.error(f"Failed to download master file: {e}")
        return pd.DataFrame()

def load_master_symbols():
    try:
        df = pd.read_csv(MASTER_FILE)
        return df
    except:
        return download_and_extract_master()

# ---- Fetch LTP ----
def fetch_ltp(client, exchange, token):
    try:
        quotes = client.get_quotes(exchange, str(token))
        return float(quotes.get("ltp", 0.0))
    except:
        return 0.0

# ---- Place order page ----
def show_place_order():
    st.header("🛒 Place Order — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from Login page.")
        return

    df_symbols = load_master_symbols()

    # ---- Exchange selection ----
    exchange = st.radio("Exchange", ["NSE", "BSE", "NFO", "MCX"], index=0)

    # Filter master for selected exchange
    df_exch = df_symbols[df_symbols["SEGMENT"] == exchange]

    # ---- Trading Symbol selection ----
    selected_symbol = st.selectbox(
        "Trading Symbol",
        df_exch["TRADINGSYM"].tolist()
    )

    # Get token for LTP
    token_row = df_exch[df_exch["TRADINGSYM"] == selected_symbol]
    token = int(token_row["TOKEN"].values[0]) if not token_row.empty else None

    # ---- Initial LTP fetch (set price once) ----
    initial_ltp = fetch_ltp(client, exchange, token) if token else 0.0
    price_input = st.number_input("Price", min_value=0.0, step=0.05, value=initial_ltp)

    # ---- LTP display container (auto-refresh) ----
    ltp_container = st.empty()
    cash_container = st.empty()
    margin_container = st.empty()

    # ---- Fetch user limits ----
    limits = client.api_get("/limits")
    cash_available = float(limits.get("cash", 0.0))
    cash_container.info(f"💰 Cash Available: ₹{cash_available:,.2f}")

    # ---- Order form ----
    with st.form("place_order_form"):
        st.subheader("Order Details")
        order_type = st.radio("Order Type", ["BUY", "SELL"])
        price_type = st.radio("Price Type", ["LIMIT", "MARKET", "SL-LIMIT", "SL-MARKET"], index=0)  # LIMIT default
        product_type = st.selectbox("Product Type", ["CNC", "INTRADAY", "NORMAL"], index=0)  # CNC default
        place_by = st.radio("Place by", ["Quantity", "Amount"])
        quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
        amount = st.number_input("Amount", min_value=0.0, step=0.05, value=0.0)
        trigger_price = st.number_input("Trigger Price (for SL orders)", min_value=0.0, step=0.05, value=0.0)
        validity = st.selectbox("Validity", ["DAY", "IOC", "EOS"], index=0)
        remarks = st.text_input("Remarks (optional)", "")
        review = st.form_submit_button("🔍 Review Order")

    if review:
        # Calculate quantity if placed by amount
        if place_by == "Amount" and amount > 0 and initial_ltp > 0:
            quantity = int(amount // initial_ltp)

        # Prepare payload
        st.session_state["pending_order"] = {
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
            st.session_state["pending_order"]["trigger_price"] = str(trigger_price)
        if remarks:
            st.session_state["pending_order"]["remarks"] = remarks

    # ---- Confirmation (only if order is reviewed) ----
    if "pending_order" in st.session_state:
        st.info("📋 Please confirm your order details:")
        st.json(st.session_state["pending_order"])

        if st.button("🚀 Confirm & Place Order"):
            resp = client.place_order(st.session_state["pending_order"])
            st.write("📬 API Response:")
            st.json(resp)

            if resp.get("status") == "SUCCESS":
                st.success(f"✅ Order placed successfully. Order ID: {resp.get('order_id')}")
                del st.session_state["pending_order"]  # clear after placing
            else:
                st.error(f"❌ Order placement failed. Response: {resp}")
    # ---- Place order ----
    if submitted:
        # Determine quantity if placed by amount
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
