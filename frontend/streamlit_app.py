# frontend/streamlit_app.py
import streamlit as st

st.set_page_config(
    page_title="GM TradeBot",
    page_icon="📈",
    layout="wide"
)

st.sidebar.success("Select a page above.")

st.title("🚀 GM TradeBot Dashboard")
st.write("""
Welcome to your personal trading assistant.  
Use the sidebar to:
- 🔑 Login
- 📊 View Portfolio
- 📝 Place Orders
""")
