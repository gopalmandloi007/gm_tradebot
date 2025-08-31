# pages/orderbook.py
import streamlit as st
import traceback
import pandas as pd

def show():
    st.header("📑 Orderbook — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        return

    if st.button("🔄 Fetch Orderbook"):
        try:
            resp = client.get_orders()   # calls /orders
            if not resp:
                st.warning("⚠️ API returned empty response")
                return

            status = resp.get("status")
            orders = resp.get("orders", [])

            if status != "SUCCESS":
                st.error(f"❌ API returned error. Response: {resp}")
                return

            if not orders:
                st.info("No orders found in orderbook today.")
                return

            # Convert to dataframe
            df = pd.DataFrame(orders)
            st.success(f"✅ Orderbook fetched ({len(df)} orders)")

            # show dataframe in a compact form
            st.dataframe(df, use_container_width=True)

            # --- Action Area: Cancel / Modify ---
            st.subheader("⚙️ Manage Orders")

            order_ids = df["order_id"].tolist() if "order_id" in df.columns else []

            if not order_ids:
                st.info("⚠️ No order_id found in response to manage.")
                return

            selected_order = st.selectbox("Select an order to manage:", order_ids)

            col1, col2 = st.columns(2)

            # Cancel Button
            with col1:
                if st.button("❌ Cancel Selected Order"):
                    try:
                        cancel_resp = client.cancel_order(order_id=selected_order)
                        st.write("🔎 Cancel API Response:", cancel_resp)
                        if cancel_resp.get("status") == "SUCCESS":
                            st.success(f"Order {selected_order} cancelled successfully ✅")
                        else:
                            st.error(f"Cancel failed: {cancel_resp}")
                    except Exception as e:
                        st.error(f"Cancel API failed: {e}")
                        st.text(traceback.format_exc())

            # Modify Form
            with col2:
                with st.form("modify_order_form"):
                    st.write("✏️ Modify Order")
                    new_price = st.text_input("New Price", "")
                    new_qty = st.text_input("New Quantity", "")
                    submitted = st.form_submit_button("Update Order")

                    if submitted:
                        try:
                            payload = {
                                "order_id": selected_order,
                                "price": float(new_price) if new_price else None,
                                "quantity": int(new_qty) if new_qty else None,
                            }
                            modify_resp = client.modify_order(payload)
                            st.write("🔎 Modify API Response:", modify_resp)
                            if modify_resp.get("status") == "SUCCESS":
                                st.success(f"Order {selected_order} modified successfully ✅")
                            else:
                                st.error(f"Modify failed: {modify_resp}")
                        except Exception as e:
                            st.error(f"Modify API failed: {e}")
                            st.text(traceback.format_exc())

        except Exception as e:
            st.error(f"Fetching orderbook failed: {e}")
            st.text(traceback.format_exc())
                    
