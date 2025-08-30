# frontend/streamlit_app.py
import streamlit as st

st.set_page_config(page_title="GM Tradebot", layout="wide")
st.title("GM Tradebot — Demo (Backend-heavy)")

menu = st.sidebar.radio("Go to", ["Login", "Portfolio", "Orders"])

if menu == "Login":
    from pages.login import show_login
    show_login()
elif menu == "Portfolio":
    from backend.session import SessionManager
    from backend.holdings import HoldingsService
    from backend.market_data import MarketDataService
    from backend.historical import HistoricalService
    st.header("📊 Portfolio")

    # require login first
    if "client" not in st.session_state or not st.session_state.client:
        st.warning("Please login first from the Login page.")
    else:
        client = st.session_state.client
        # build services
        mkt = MarketDataService(client)
        hist = HistoricalService(client)
        hs = HoldingsService(client, market=mkt, hist=hist)
        try:
            df, totals = hs.enriched_table()
            if df.empty:
                st.info("No holdings found.")
            else:
                st.dataframe(df, use_container_width=True)
                st.markdown("---")
                st.write("Totals:", totals)
        except Exception as e:
            st.error(f"Failed to fetch holdings: {e}")

elif menu == "Orders":
    from frontend.pages.login import show_login  # provide login UI if needed
    from backend.session import SessionManager
    from backend.holdings import HoldingsService
    from backend.orders import OrdersService
    st.header("🧾 Orders")

    if "client" not in st.session_state or not st.session_state.client:
        st.warning("Please login first from the Login page.")
    else:
        client = st.session_state.client
        hs = HoldingsService(client)
        try:
            df, totals = hs.enriched_table()
        except Exception:
            df = None
        osvc = OrdersService(client)
        st.subheader("Place GTT orders from holdings")
        if df is None or df.empty:
            st.info("No holdings found to build orders.")
        else:
            st.dataframe(df[["symbol", "token", "qty", "avg_price"]], use_container_width=True)
            token = st.text_input("Token (copy exact token from table)")
            qty = st.number_input("Quantity", min_value=1, value=1)
            sl = st.number_input("Stop loss % (negative value)", value=-2.0)
            targets = st.text_input("Targets % (comma separated, e.g. 10,20,30,40)", value="10,20,30,40")
            if st.button("Build & Place GTTs"):
                try:
                    tlist = [float(x.strip()) for x in targets.split(",") if x.strip()]
                    # find holding row for avg price & symbol
                    holding_row = None
                    if df is not None:
                        for _, r in df.iterrows():
                            if str(r["token"]) == str(token) or str(r["symbol"]) == token:
                                holding_row = r
                                break
                    avg_price = float(holding_row["avg_price"]) if holding_row is not None else 0.0
                    tradingsymbol = holding_row["symbol"] if holding_row is not None else token
                    payloads = osvc.build_gtt_oco_payloads_from_holding(
                        exchange="NSE",
                        tradingsymbol=tradingsymbol,
                        token=token,
                        qty=int(qty),
                        avg_price=avg_price,
                        sl_pct=float(sl),
                        target_pcts=tlist
                    )
                    results = osvc.place_gtt_bulk(payloads)
                    st.write(results)
                except Exception as e:
                    st.error(f"Failed to build/place GTTs: {e}")
