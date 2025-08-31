# pages/place_oco_order.py
import streamlit as st
import traceback
from typing import Any, Dict

def show_place_oco_order():
    """
    Streamlit page to place an OCO order via your DefinedgeClient in st.session_state["client"].
    Preferred call: client.oco_place(payload)
    Fallbacks: client.place_oco(...) or client.api_post("/ocoplaceorder", payload)
    """
    st.header("🟢 Place OCO Order — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login from the Login page first.")
        st.stop()

    debug = st.checkbox("Show debug info", value=False)

    with st.form("oco_order_form"):
        st.subheader("📋 Order Details")
        remarks = st.text_input("Remarks (optional)", value="")
        tradingsymbol = st.text_input("Trading Symbol (e.g. NIFTY29MAR23F)", value="")
        exchange = st.selectbox("Exchange", ["NSE", "BSE", "NFO", "MCX"], index=2)
        order_type = st.selectbox("Order Type", ["BUY", "SELL"], index=1)
        target_quantity = st.number_input("Target Quantity", min_value=1, step=1, value=50)
        stoploss_quantity = st.number_input("Stoploss Quantity", min_value=1, step=1, value=50)
        target_price = st.number_input("Target Price", min_value=0.0, format="%.2f", value=17000.00)
        stoploss_price = st.number_input("Stoploss Price", min_value=0.0, format="%.2f", value=17300.00)
        product_type = st.selectbox("Product Type (optional)", ["", "CNC", "INTRADAY", "NORMAL"], index=0)

        submitted = st.form_submit_button("🚀 Place OCO Order")

    if not submitted:
        return

    # --- Validation ---
    if not tradingsymbol.strip():
        st.error("Please provide trading symbol.")
        return
    if int(target_quantity) <= 0 or int(stoploss_quantity) <= 0:
        st.error("Quantities must be greater than 0.")
        return
    if float(target_price) <= 0 or float(stoploss_price) <= 0:
        st.error("Prices must be greater than 0.")
        return

    # Build payload exactly as per your docs
    payload: Dict[str, Any] = {
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
        st.write("🔎 Debug: payload")
        st.json(payload)

    # --- Send request using client ---
    resp = None
    exc = None
    try:
        # Preferred API name you requested
        if hasattr(client, "oco_place"):
            resp = client.oco_place(payload)
            method_used = "client.oco_place(payload)"
        elif hasattr(client, "place_oco"):
            resp = client.place_oco(payload)
            method_used = "client.place_oco(payload)"
        elif hasattr(client, "place_oco_order"):
            resp = client.place_oco_order(payload)
            method_used = "client.place_oco_order(payload)"
        elif hasattr(client, "api_post"):
            # Generic fallback to api_post for /ocoplaceorder
            resp = client.api_post("/ocoplaceorder", payload)
            method_used = "client.api_post('/ocoplaceorder', payload)"
        else:
            st.error("❌ Your DefinedgeClient does not expose a known OCO method (oco_place/place_oco/api_post).")
            st.info("Add a method named `oco_place(payload)` or ensure client.api_post() is available.")
            return
    except Exception as e:
        exc = e
        if debug:
            st.error(f"🚨 Exception while calling OCO API: {e}")
            st.text(traceback.format_exc())
        else:
            st.error("🚨 Exception while placing OCO order (enable debug to see traceback).")

    # --- Handle result ---
    if exc is not None:
        return

    if debug:
        st.write(f"🔎 Debug: method used: {method_used}")
        st.write("🔎 Debug: raw response:")
        st.write(resp)

    if not isinstance(resp, dict):
        st.error("⚠️ Unexpected API response format (expected JSON object).")
        if debug:
            st.write(resp)
        return

    # Expected success response per API docs
    if resp.get("status") == "SUCCESS":
        alert_id = resp.get("alert_id")
        msg = resp.get("message") or "OCO order placed successfully."
        st.success(f"✅ {msg} — Alert ID: {alert_id}")
        st.json(resp)
    else:
        # show friendlier message if available
        user_msg = resp.get("message") or "Failed to place OCO order."
        st.error(f"❌ {user_msg}")
        if debug:
            st.write(resp)

    st.markdown(
        "Tip: After placement, open **GTT Order Book** / **Order Book** to verify the alert. "
        "If it does not appear immediately, refresh that page."
    )
    
