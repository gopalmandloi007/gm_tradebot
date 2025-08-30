# app.py
import streamlit as st
import os, sys

# ensure repo root is on sys.path when running from Streamlit Cloud
repo_root = os.path.abspath(os.path.dirname(__file__))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

st.set_page_config(page_title="GM TradeBot", layout="wide")
st.title("🚀 GM TradeBot")

# session defaults
if "api_session_key" not in st.session_state:
    st.session_state["api_session_key"] = None
if "susertoken" not in st.session_state:
    st.session_state["susertoken"] = None
if "uid" not in st.session_state:
    st.session_state["uid"] = None
if "client" not in st.session_state:
    st.session_state["client"] = None

pages = {
    "Login": "pages.login",
    "Holdings": "pages.holdings",
    "Positions": "pages.positions",
    "Orderbook & Tradebook": "pages.orderbook_tradebook",
    "Place Orders": "pages.place_orders",
    "Place GTT Orders": "pages.place_gtt_orders",
    "GTT Orderbook": "pages.gtt_orderbook",
    "Cancel/Modify Orders": "pages.cancel_modify_orders",
}

choice = st.sidebar.selectbox("Pages", list(pages.keys()))

# dynamic import and run
module = __import__(pages[choice], fromlist=["*"])
# each page module exposes `show()` function
module.show()
