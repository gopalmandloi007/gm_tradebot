# pages/place_order.py
import streamlit as st
import pandas as pd
from definedge_api import DefinedgeClient

MASTER_FILE = "data/master/allmaster.csv"  # path where master CSV is stored

def load_master_symbols():
    df = pd.read_csv(MASTER_FILE)
    if 'TRADINGSYM' not in df.columns:
        st.error("Master file missing TRADINGSYM column")
        return pd.DataFrame()
    return df

def show_place_order():
    st.header("🛒 Place Order — Definedge")

    client: DefinedgeClient = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from Login page.")
        return

    # --- Load master symbols ---
    df_symbols = load_master_symbols()
    if df_symbols.empty:
        st.warning("⚠️ Master symbols not loaded or empty.")
        return

    # --- Exchange selection (default NSE) ---
    exchange = st.radio("Select Exchange", ["NSE", "BSE", "NFO", "MCX"], index=0)

    # --- Symbol selection filtered by selected exchange ---
    df_filtered = df_symbols[df_symbols['SEGMENT'] == exchange]
    tradingsymbol_list = df_filtered['TRADINGSYM'].unique().tolist()
    selected_symbol = st.selectbox("Select Trading Symbol", tradingsymbol_list)

    # --- Fetch LTP only for selected symbol ---
    token_row = df_filtered[df_filtered['TRADINGSYM'] == selected_symbol].iloc[0]
    token = str(token_row['TOKEN'])

    try:
        quote = client.get_quotes(exchange=exchange, token=token)
        ltp = float(quote.get("ltp", 0))
    except:
        ltp = 0

    # --- Order form ---
    with st.form("place_order_form"):
        st.subheader("Order Details")

        order_type = st.selectbox("Order Type", ["BUY", "SELL"])
        product_type = st.selectbox("Product Type", ["CNC", "INTRADAY", "NORMAL"], index=2)
        price_type = st.radio("Price Type", ["MARKET", "LIMIT", "SL-LIMIT", "SL-MARKET"])
        quantity = st.number_input("Quantity", min_value=1, step=1, value=50)
        price = st.number_input("Price", min_value=0.0, step=0.05, value=ltp)
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
                "price_type": price_type,
                "product_type": product_type,
                "quantity": str(quantity),
                "price": str(price),
                "validity": validity
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
                
