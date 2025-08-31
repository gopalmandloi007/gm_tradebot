import streamlit as st
import requests

def show_place_oco_order():
    st.header("🟢 Place OCO Order")

    # Session check
    if "client" not in st.session_state:
        st.warning("⚠️ Please login first.")
        st.stop()

    # ---- Input Fields ----
    remarks = st.text_input("Remarks", value="admin")
    tradingsymbol = st.text_input("Trading Symbol", value="NIFTY29MAR23F")
    exchange = st.selectbox("Exchange", ["NSE", "BSE", "NFO"], index=2)
    order_type = st.selectbox("Order Type", ["BUY", "SELL"], index=1)
    target_quantity = st.number_input("Target Quantity", min_value=1, value=50)
    stoploss_quantity = st.number_input("Stoploss Quantity", min_value=1, value=50)
    target_price = st.number_input("Target Price", min_value=1, value=17000)
    stoploss_price = st.number_input("Stoploss Price", min_value=1, value=17300)
    product_type = st.selectbox("Product Type", ["CNC", "INTRADAY", "NORMAL"], index=2)

    if st.button("🚀 Place OCO Order"):
        try:
            # API endpoint
            url = st.session_state["client"]["base_url"] + "/ocoplaceorder"
            
            # Prepare headers
            headers = {
                "Authorization": st.session_state["client"]["access_token"],
                "Content-Type": "application/json"
            }

            # Prepare request payload
            payload = {
                "remarks": remarks,
                "tradingsymbol": tradingsymbol,
                "exchange": exchange,
                "order_type": order_type,
                "target_quantity": str(target_quantity),
                "stoploss_quantity": str(stoploss_quantity),
                "target_price": str(target_price),
                "stoploss_price": str(stoploss_price),
                "product_type": product_type
            }

            # API call
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()

            # Show response
            if response.status_code == 200:
                st.success("✅ Order Placed Successfully")
                st.json(data)
            else:
                st.error("❌ API returned non-success status")
                st.json(data)

        except Exception as e:
            st.error(f"Error: {e}")
