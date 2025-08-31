# pages/place_oco_order.py
import streamlit as st
import traceback

def show_place_oco_order():
    """
    Streamlit page to place an OCO order using DefinedgeClient stored in st.session_state["client"].
    Uses client.api_post('/ocoplaceorder', payload) so there's no direct base_url or token handling here.
    """
    st.header("🟢 Place OCO Order — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        st.stop()

    debug = st.checkbox("Show debug info", value=False)

    with st.form("oco_order_form"):
        st.subheader("📋 Order Details")
        remarks = st.text_input("Remarks (optional)", value="")
        tradingsymbol = st.text_input("Trading Symbol (e.g. NIFTY29MAR23F)", value="")
        exchange = st.selectbox("Exchange", ["NSE", "BSE", "NFO", "MCX"], index=0)
        order_type = st.selectbox("Order Type", ["BUY", "SELL"], index=1)
        target_quantity = st.number_input("Target Quantity", min_value=1, step=1, value=50)
        stoploss_quantity = st.number_input("Stoploss Quantity", min_value=1, step=1, value=50)
        target_price = st.number_input("Target Price", min_value=0.0, format="%.2f", value=17000.00)
        stoploss_price = st.number_input("Stoploss Price", min_value=0.0, format="%.2f", value=17300.00)
        product_type = st.selectbox("Product Type (optional)", ["", "CNC", "INTRADAY", "NORMAL"], index=0)

        submitted = st.form_submit_button("🚀 Place OCO Order")

    if not submitted:
        return

    # Basic validation
    if not tradingsymbol.strip():
        st.error("Please provide a trading symbol.")
        return
    if target_quantity <= 0 or stoploss_quantity <= 0:
        st.error("Quantities must be greater than 0.")
        return
    if target_price <= 0 or stoploss_price <= 0:
        st.error("Prices must be greater than 0.")
        return

    # Build payload exactly as per API docs
    payload = {
        "remarks": remarks or "",
        "tradingsymbol": tradingsymbol.strip(),
        "exchange": exchange,
        "order_type": order_type,
        "target_quantity": str(int(target_quantity)),
        "stoploss_quantity": str(int(stoploss_quantity)),
        "target_price": str(float(target_price)),
        "stoploss_price": str(float(stoploss_price)),
    }
    if product_type:
        payload["product_type"] = product_type

    if debug:
        st.write("🔎 Debug: payload to be sent")
        st.json(payload)

    # Call Definedge client's wrapper (no manual headers)
    try:
        resp = client.api_post("/ocoplaceorder", payload)
    except Exception as e:
        st.error(f"🚨 Error while calling OCO place API: {e}")
        if debug:
            st.text(traceback.format_exc())
        return

    # Validate/handle response
    if not isinstance(resp, dict):
        st.error("⚠️ Unexpected API response format (expected JSON object).")
        if debug:
            st.write(resp)
        return

    # Success case per docs
    if resp.get("status") == "SUCCESS":
        alert_id = resp.get("alert_id")
        msg = resp.get("message") or "OCO order placed successfully."
        st.success(f"✅ {msg} — Alert ID: {alert_id}")
        st.json(resp)
    else:
        # Show friendly error + full response when debugging
        user_msg = resp.get("message") or "Failed to place OCO order."
        st.error(f"❌ {user_msg}")
        if debug:
            st.write(resp)

    st.markdown(
        "Tip: After placement, open **GTT Order Book** / **Order Book** page to verify alerts/orders. "
        "If it doesn't appear immediately, refresh that page."
    )
    
