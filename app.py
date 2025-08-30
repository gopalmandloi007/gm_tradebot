import streamlit as st

st.set_page_config(
    page_title="GM TradeBot",
    page_icon="🤖",
    layout="wide"
)

# Agar session set nahi hai to default false rakho
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "session_key" not in st.session_state:
    st.session_state["session_key"] = None

st.title("🚀 GM TradeBot Dashboard")
st.sidebar.success("Select a page")

if not st.session_state["logged_in"]:
    st.warning("🔑 Please login first from the Login Page.")
else:
    st.success(f"✅ You are logged in with session: {st.session_state['session_key']}")
