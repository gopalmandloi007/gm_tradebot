import streamlit as st
from backend.holdings import HoldingsService
import pandas as pd

def show_portfolio():
    st.header('📊 Portfolio (Holdings)')
    client = st.session_state.get('client')
    if not client:
        st.warning('Please login first.')
        return
    hs = HoldingsService(client)
    try:
        df, totals = hs.enriched_table()
    except Exception as e:
        st.error(f'Failed to fetch holdings: {e}')
        return
    if df.empty:
        st.info('No holdings found.')
        return
    st.dataframe(df, use_container_width=True)
    st.markdown('---')
    st.write('Totals:', totals)
