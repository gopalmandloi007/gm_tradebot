import streamlit as st
from backend.orders import OrdersService
from backend.holdings import HoldingsService

def show_orders():
    st.header('🧾 Orders')
    client = st.session_state.get('client')
    if not client:
        st.warning('Please login first.')
        return
    osvc = OrdersService(client)
    hsvc = HoldingsService(client)
    df, totals = hsvc.enriched_table()
    st.subheader('Holdings (to choose symbol)')
    if not df.empty:
        st.dataframe(df[['symbol','token','qty','avg_price']], use_container_width=True)
    st.markdown('---')
    st.subheader('Place GTT orders from a holding')
    token = st.text_input('Token (from holdings token column)')
    qty = st.number_input('Quantity', min_value=1, value=1)
    sl = st.number_input('Stop loss % (negative value)', value=-2.0)
    targets = st.text_input('Targets % (comma separated, e.g. 10,20,30,40)', value='10,20,30,40')
    if st.button('Build and place GTTs'):
        try:
            tlist = [float(x.strip()) for x in targets.split(',') if x.strip()]
            # find holding
            holding = None
            if not df.empty:
                for _, r in df.iterrows():
                    if str(r.get('token')) == str(token) or str(r.get('symbol')) == token:
                        holding = r
                        break
            avg_price = holding['avg_price'] if holding is not None else None
            tradingsymbol = holding['symbol'] if holding is not None else token
            payloads = osvc.build_gtt_oco_payloads_from_holding(
                exchange='NSE', tradingsymbol=tradingsymbol, token=token, qty=int(qty),
                avg_price=float(avg_price) if avg_price is not None else 0.0,
                sl_pct=float(sl), target_pcts=tlist
            )
            results = osvc.place_gtt_bulk(payloads)
            st.write(results)
        except Exception as e:
            st.error(f'Failed to place GTTs: {e}')
