import streamlit as st
import pandas as pd
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

# ---------- Page: Dashboard Overview ----------
if page == "Dashboard Overview":
    st.title("📊 CyberArk Dashboard Overview")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Accounts", "Click 'Fetch Accounts'")
    with col2:
        st.metric("Active Safes", "Click 'Load Safes'")
    with col3:
        st.metric("Status", "Ready")
    
    st.subheader("Quick Actions")
    st.info("Use the sidebar to test connection, then navigate to Account Management or Safe Explorer.")

# ---------- Page: Account Management ----------
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
            if accounts and isinstance(accounts, list) and len(accounts) > 0:
                # Convert to pandas DataFrame for clean display
                df = pd.DataFrame(accounts)
                
                # Select most relevant columns (adjust as needed)
                preferred_cols = ['name', 'userName', 'address', 'safeName', 'platformId', 'secretType', 'id']
                display_cols = [col for col in preferred_cols if col in df.columns]
                
                st.dataframe(df[display_cols], use_container_width=True)
                st.success(f"Found {len(accounts)} accounts")
            elif accounts:
                # Fallback: show raw if not a list of dicts
                st.json(accounts)
                st.success("Data retrieved (raw format shown)")
            else:
                st.warning("No accounts found or connection failed")

# ---------- Page: Safe Explorer ----------
elif page == "Safe Explorer":
    st.title("📁 Safe Explorer")
    
    if st.button("Load Safes"):
        with st.spinner("Loading safes..."):
            safes = st.session_state.client.get_safes()
            if safes and isinstance(safes, list) and len(safes) > 0:
                df = pd.DataFrame(safes)
                st.dataframe(df, use_container_width=True)
                st.success(f"Found {len(safes)} safes")
            elif safes:
                st.json(safes)
            else:
                st.warning("No safes found or connection failed")
