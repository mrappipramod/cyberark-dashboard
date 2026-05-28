import streamlit as st
from utils.cyberark_client import CyberArkClient

# Page configuration
st.set_page_config(
    page_title="CyberArk Dashboard",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize client in session state
if 'client' not in st.session_state:
    st.session_state.client = CyberArkClient()

# Sidebar navigation
st.sidebar.title("🔐 CyberArk Dashboard")
page = st.sidebar.radio(
    "Navigate",
    ["Dashboard Overview", "Account Management", "Safe Explorer"]
)

# Test connection button
if st.sidebar.button("Test Connection"):
    with st.spinner("Connecting to CyberArk..."):
        if st.session_state.client.authenticate():
            st.sidebar.success("✅ Connection successful")
        else:
            st.sidebar.error("❌ Connection failed")

# ---------- Page Content ----------
if page == "Dashboard Overview":
    st.title("📊 CyberArk Dashboard Overview")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Accounts", "Click Fetch", delta=None)
    with col2:
        st.metric("Active Safes", "Click Fetch", delta=None)
    with col3:
        st.metric("Status", "Not connected", delta=None)
    
    st.subheader("Quick Actions")
    st.info("Use the sidebar to test connection, then navigate to Account Management or Safe Explorer.")

elif page == "Account Management":
    st.title("👤 Account Management")
    
    col1, col2 = st.columns(2)
    with col1:
        safe_filter = st.text_input("Filter by Safe Name (optional)")
    with col2:
        limit = st.number_input("Max results", min_value=10, max_value=500, value=50)
    
    if st.button("Fetch Accounts"):
        with st.spinner("Loading accounts..."):
            accounts = st.session_state.client.get_accounts(
                safe=safe_filter if safe_filter else None,
                limit=limit
            )
            if accounts:
                st.dataframe(accounts)
                st.success(f"Found {len(accounts)} accounts")
            else:
                st.warning("No accounts found or connection failed")

elif page == "Safe Explorer":
    st.title("📁 Safe Explorer")
    
    if st.button("Load Safes"):
        with st.spinner("Loading safes..."):
            safes = st.session_state.client.get_safes()
            if safes:
                st.dataframe(safes)
                st.success(f"Found {len(safes)} safes")
            else:
                st.warning("No safes found or connection failed")
