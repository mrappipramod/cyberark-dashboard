import streamlit as st
import pandas as pd
from utils.cyberark_client import CyberArkClient

st.set_page_config(page_title="CyberArk Dashboard", page_icon="🔐", layout="wide")

# Initialize CyberArk Client in state
if 'client' not in st.session_state:
    st.session_state.client = CyberArkClient()

st.sidebar.title("🔐 CyberArk Dashboard")
page = st.sidebar.radio("Navigate", ["Dashboard Overview", "Account Management", "Safe Explorer"])

# Sidebar Connection Test
if st.sidebar.button("Test Connection"):
    with st.spinner("Connecting to CyberArk..."):
        if st.session_state.client.authenticate():
            st.sidebar.success("✅ Connected Successfully!")
        else:
            st.sidebar.error("❌ Connection Failed. Check your Secrets configuration.")

# ---------- Dashboard Overview ----------
if page == "Dashboard Overview":
    st.title("📊 CyberArk Dashboard Overview")
    st.info("💡 Use the sidebar to test your credentials, then navigate to Account Management or Safe Explorer.")
    
    # Quick status indicator
    if st.session_state.client.token:
        st.success("Session Status: Authenticated")
    else:
        st.warning("Session Status: Disconnected (Will auto-connect when data is requested)")

# ---------- Account Management ----------
elif page == "Account Management":
    st.title("👤 Account Management")
    
    col1, col2 = st.columns(2)
    with col1:
        safe_filter = st.text_input("Filter by Safe Name (Optional)", placeholder="e.g. MY-SAFE-01")
    with col2:
        limit = st.number_input("Max Results", min_value=10, max_value=500, value=50, step=10)

    if st.button("Fetch Accounts", type="primary"):
        with st.spinner("Querying CyberArk Accounts Vault..."):
            accounts = st.session_state.client.get_accounts(
                safe=safe_filter.strip() if safe_filter else None,
                limit=limit
            )
            
            if accounts and len(accounts) > 0:
                df = pd.DataFrame(accounts)
                
                # Flexible matching to capture dynamic CyberArk field variations
                potential_cols = ['id', 'name', 'userName', 'username', 'address', 'safeName', 'safe', 'platformId', 'secretType']
                display_cols = [c for c in potential_cols if c in df.columns]
                
                # If filtering cleaned up too many columns, fallback to showing all available data
                if not display_cols:
                    display_cols = list(df.columns)
                
                st.success(f"🎉 Successfully found {len(accounts)} accounts")
                st.dataframe(df[display_cols], use_container_width=True)
            else:
                st.warning("No accounts found. Toggle open the 'Debug: Raw API Response' tool at the bottom of the page to inspect.")

# ---------- Safe Explorer ----------
elif page == "Safe Explorer":
    st.title("📁 Safe Explorer")
    
    if st.button("Load All Safes", type="primary"):
        with st.spinner("Querying CyberArk Safes Inventory..."):
            safes = st.session_state.client.get_safes()
            
            if safes and len(safes) > 0:
                df = pd.DataFrame(safes)
                
                # Flexible column matching for Safe schemas
                potential_safe_cols = ['safeName', 'name', 'safeUrlId', 'description', 'managingCPM', 'numberOfDaysRetention', 'location']
                display_cols = [c for c in potential_safe_cols if c in df.columns]
                
                if not display_cols:
                    display_cols = list(df.columns)
                
                st.success(f"🎉 Successfully found {len(safes)} safes")
                st.dataframe(df[display_cols], use_container_width=True)
            else:
                st.warning("No safes found. Check permissions or inspect the raw expander logs.")
