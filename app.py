import streamlit as st
import pandas as pd
from utils.cyberark_client import CyberArkClient

st.set_page_config(page_title="CyberArk Dashboard", page_icon="🔐", layout="wide")

if 'client' not in st.session_state:
    st.session_state.client = CyberArkClient()

st.sidebar.title("🔐 CyberArk Dashboard")
page = st.sidebar.radio("Navigate", ["Dashboard Overview", "Account Management", "Safe Explorer"])

if st.sidebar.button("Test Connection"):
    with st.spinner("Connecting..."):
        if st.session_state.client.authenticate():
            st.sidebar.success("✅ Connected")
        else:
            st.sidebar.error("❌ Failed")

# ---------- Dashboard Overview ----------
if page == "Dashboard Overview":
    st.title("📊 CyberArk Dashboard Overview")
    st.info("Use the sidebar to test connection, then navigate to Account Management or Safe Explorer.")

# ---------- Account Management ----------
elif page == "Account Management":
    st.title("👤 Account Management")
    col1, col2 = st.columns(2)
    with col1:
        safe_filter = st.text_input("Filter by Safe (optional)")
    with col2:
        limit = st.number_input("Max results", min_value=10, max_value=500, value=50)

    if st.button("Fetch Accounts"):
        with st.spinner("Loading accounts..."):
            accounts = st.session_state.client.get_accounts(
                safe=safe_filter if safe_filter else None,
                limit=limit
            )
            if accounts and len(accounts) > 0:
                df = pd.DataFrame(accounts)
                # Select common columns (rename if needed)
                display_cols = ['name', 'userName', 'address', 'safeName', 'platformId', 'secretType', 'id']
                display_cols = [c for c in display_cols if c in df.columns]
                st.dataframe(df[display_cols], use_container_width=True)
                st.success(f"Found {len(accounts)} accounts")
            else:
                st.warning("No accounts found or connection failed")

# ---------- Safe Explorer ----------
elif page == "Safe Explorer":
    st.title("📁 Safe Explorer")
    if st.button("Load Safes"):
        with st.spinner("Loading safes..."):
            safes = st.session_state.client.get_safes()
            if safes and len(safes) > 0:
                df = pd.DataFrame(safes)
                st.dataframe(df, use_container_width=True)
                st.success(f"Found {len(safes)} safes")
            else:
                st.warning("No safes found")
