# pages/gtt_orderbook.py
import streamlit as st
import pandas as pd

def show():
    st.header("⏰ GTT Order Book — Definedge")

    client = st.session_state.get("client")
    if not client:
        st.error("⚠️ Not logged in. Please login first from the Login page.")
        st.stop()

    # Optional: quick peek at session keys while debugging
    st.write("🔎 Debug: session_state keys:", list(st.session_state.keys()))

    try:
        resp = client.gtt_orders()  # <-- uses your DefinedgeClient wrapper

        st.write("🔎 Debug: Raw GTT API response:", resp)

        if not isinstance(resp, dict):
            st.error("❌ Unexpected response format from API.")
            st.stop()

        if resp.get("status") != "SUCCESS":
            st.error(f"❌ API returned non-success status. Full response: {resp}")
            st.stop()

        # Per docs, list is under 'pendingGTTOrderBook'
        rows = resp.get("pendingGTTOrderBook") or []

        if not rows:
            st.info("✅ No pending GTT orders found.")
            return

        # Build DataFrame (keep a sensible column order if present)
        df = pd.DataFrame(rows)
        preferred_cols = [
            "alert_id", "order_time", "tradingsymbol", "exchange", "token",
            "order_type", "price_type", "product_type", "quantity", "lotsize",
            "trigger_price", "price", "condition", "remarks",
            "stoploss_quantity", "target_quantity",
            "stoploss_price", "target_price",
            "stoploss_trigger", "target_trigger",
        ]
        # Show preferred columns first (if they exist), then the rest
        cols = [c for c in preferred_cols if c in df.columns] + \
               [c for c in df.columns if c not in preferred_cols]
        df = df[cols]

        st.success(f"✅ Found {len(df)} GTT orders")
        st.dataframe(df, use_container_width=True)

        # Optional: quick CSV export
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download GTT orders (CSV)", csv, "gtt_orders.csv", "text/csv")

    except Exception as e:
        st.error(f"⚠️ GTT order fetch failed: {e}")
