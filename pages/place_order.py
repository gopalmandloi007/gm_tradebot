# pages/place_order.py
import streamlit as st
import pandas as pd
import io
import requests
import zipfile
from definedge_api import DefinedgeClient

def load_master_symbols():
    if "master_df" not in st.session_state:
        try:
            r = requests.get("https://app.definedgesecurities.com/public/allmaster.zip", timeout=20)
            z = zipfile.ZipFile(io.BytesIO(r.content))
            csv_name = [f for f in z.namelist() if f.endswith(".csv")][0]
            df = pd.read_csv(z.open(csv_name), header=None)
            df.columns = ["SEGMENT","TOKEN","SYMBOL","TRADINGSYM","INSTRUMENT_TYPE","EXPIRY",
                          "TICKSIZE","LOTSIZE","OPTIONTYPE","STRIKE","PRICEPREC","MULTIPLIER","ISIN","PRICEMULT","COMPANY"]
            st.session_state["master_df"] = df
        except Exception as e:
            st.error(f"Failed to load master file: {e}")
            return pd.DataFrame()
    return st.session_state["master_df"]

def show_place_order():
    st.header("🛒 Place Order — Definedge")
    client: DefinedgeClient = st.session_state.get("client")
    if not client:
        st.error("⚠️ Please login first from the Login page.")
        return

    df_symbols = load_master_symbols()
    if df_symbols.empty:
        st.warning("Master file not loaded")
        return

    with st.form("place_order_form"):
        st.subheader("Order Details")

        # Exchange selection
        exchange = st.radio("Exchange", ["NSE","BSE","NFO","MCX"], index=0)

        df_seg = df_symbols[df_symbols["SEGMENT"]==exchange]
        tradingsymbol = st.selectbox("Trading Symbol", df_seg["TRADINGSYM"].tolist())
        token = df_seg[df_seg["TRADINGSYM"]==tradingsymbol]["TOKEN"].values[0]

        # Fetch LTP once for default price
        if "price_input" not in st.session_state or st.session_state.get("symbol_selected") != tradingsymbol:
            try:
                ltp_initial = float(client.get_quotes(exchange, token).get("ltp",0.0))
            except:
                ltp_initial = 0.0
            st.session_state["price_input"] = ltp_initial
            st.session_state["symbol_selected"] = tradingsymbol

        # Editable price
        price_input = st.number_input("Price (editable)", min_value=0.0, step=0.05, value=float(st.session_state["price_input"]))

        # Auto-refresh LTP in separate container
        ltp_container = st.empty()
        try:
            ltp_live = float(client.get_quotes(exchange, token).get("ltp",0.0))
            ltp_container.markdown(f"**Live LTP:** {ltp_live}")
        except:
            ltp_container.markdown("**Live LTP:** --")

        # Cash limits
        try:
            limits = client.api_get("/limits")
            cash_avail = float(limits.get("cash",0))
        except:
            cash_avail = 0.0
        st.info(f"💰 Cash Available: ₹{cash_avail:,.2f}")

        # Place by qty or amount
        place_by = st.radio("Place by", ["Quantity","Amount"])
        if place_by=="Quantity":
            quantity = st.number_input("Quantity", min_value=1, step=1, value=1)
            amount = quantity*price_input
            st.metric("Amount", f"₹{amount:,.2f}")
        else:
            amount = st.number_input("Amount", min_value=0.0, step=0.05, value=0.0)
            quantity = int(amount // price_input) if price_input>0 else 0
            st.metric("Calculated Quantity", quantity)

        order_type = st.radio("Order Type", ["BUY","SELL"])
        price_type = st.radio("Price Type", ["MARKET","LIMIT","SL-LIMIT","SL-MARKET"])
        product_type = st.radio("Product Type", ["CNC","INTRADAY","NORMAL"], index=2)
        trigger_price = st.number_input("Trigger Price (for SL orders)", min_value=0.0, step=0.05, value=0.0)
        validity = st.selectbox("Validity", ["DAY","IOC","EOS"], index=0)
        remarks = st.text_input("Remarks (optional)","")

        # Get required margin
        margin_required = 0.0
        try:
            basket = [{"exchange": exchange,"tradingsymbol": tradingsymbol,"quantity":str(quantity),
                       "price":str(price_input),"product_type":product_type,"order_type":order_type,"price_type":price_type}]
            margin_resp = client.api_post("/margin", {"basketlists":basket})
            if margin_resp.get("status")=="SUCCESS":
                margin_required = float(margin_resp.get("marginUsed",0))
            st.info(f"📊 Required Margin: ₹{margin_required:,.2f}")
            if margin_required>cash_avail:
                st.warning("⚠️ Margin exceeds available cash!")
        except:
            st.warning("Unable to fetch required margin")

        # ---- Submit button ----
        submitted = st.form_submit_button("🚀 Place Order")

    if submitted:
        try:
            payload = {
                "exchange": exchange,
                "tradingsymbol": tradingsymbol,
                "order_type": order_type,
                "price_type": price_type,
                "product_type": product_type,
                "quantity": str(quantity),
                "price": str(price_input),
                "validity": validity
            }
            if trigger_price>0:
                payload["trigger_price"] = str(trigger_price)
            if remarks:
                payload["remarks"] = remarks

            st.write("📦 Sending payload:")
            st.json(payload)

            resp = client.place_order(payload)
            st.write("📬 API Response:")
            st.json(resp)

            if resp.get("status")=="SUCCESS":
                st.success(f"✅ Order placed successfully. Order ID: {resp.get('order_id')}")
            else:
                st.error(f"❌ Order placement failed. Response: {resp}")

        except Exception as e:
            st.error(f"Order placement failed: {e}")
        
