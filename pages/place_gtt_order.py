import streamlit as st
import requests

def show():
    st.subheader("📌 Place GTT Order")

    if "client" not in st.session_state:
        st.warning("⚠️ Please login first.")
        st.stop()

    # ---- Form for GTT order ----
    with st.form("gtt_order_form"):
        exchange = st.selectbox("Exchange", ["NSE", "BSE"])
        tradingsymbol = st.text_input("Trading Symbol", "TCS-EQ")
        condition = st.selectbox("Condition", ["LTP_ABOVE", "LTP_BELOW"])
        alert_price = st.number_input("Alert Price", min_value=0.0, value=3100.0, step=0.05)
        order_type = st.selectbox("Order Type", ["BUY", "SELL"])
        price = st.number_input("Order Price", min_value=0.0, value=3100.0, step=0.05)
        quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
        product_type = st.selectbox("Product Type", ["CNC", "INTRADAY", "NORMAL"])

        submitted = st.form_submit_button("🚀 Place GTT Order")

    if submitted:
        headers = {
            "Authorization": st.session_state["client"].access_token,  # Token from login
            "Content-Type": "application/json"
        }

        payload = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "condition": condition,
            "alert_price": str(alert_price),
            "order_type": order_type,
            "price": str(price),
            "quantity": str(quantity),
            "product_type": product_type
        }

        try:
            url = st.session_state["client"].base_url + "/gttplaceorder"
            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "SUCCESS":
                    st.success(f"✅ {data.get('message')} (Alert ID: {data.get('alert_id')})")
                else:
                    st.error(f"⚠️ {data.get('message')}")
            else:
                st.error(f"❌ API Error: {response.text}")

        except Exception as e:
            st.error(f"🚨 Exception: {e}")
