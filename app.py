import streamlit as st
import pandas as pd
from utils.cyberark_client import CyberArkClient

st.set_page_config(page_title="CyberArk Dashboard", page_icon="🔐", layout="wide")

# Persistent state mapping across Streamlit refresh iterations
if 'client' not in st.session_state:
    st.session_state.client = CyberArkClient()

st.sidebar.title("🔐 CyberArk Dashboard")
page = st.sidebar.radio("Navigate", ["Dashboard Overview", "Account Management", "Safe Explorer"])

if st.sidebar.button("Test Connection"):
    with st.spinner("Connecting to Vault..."):
        if st.session_state.client.authenticate():
            st.sidebar.success("✅ Connected")
        else:
            st.sidebar.error("❌ Connection Failed")

# ---------- Dashboard Overview ----------
if page == "Dashboard Overview":
    st.title("📊 CyberArk Dashboard Overview")
    st.info("Use the sidebar navigation choices to explore Active Directory Records, Safe configurations, and Asset distribution.")

# ---------- Account Management ----------
elif page == "Account Management":
    st.title("👤 Account Management")
    col1, col2 = st.columns(2)
    with col1:
        safe_filter = st.text_input("Filter by Safe (optional)", placeholder="e.g. PVWAReports")
    with col2:
        limit = st.number_input("Max results", min_value=10, max_value=500, value=50, step=10)

    if st.button("Fetch Accounts", type="primary"):
        with st.spinner("Loading accounts from CyberArk..."):
            accounts = st.session_state.client.get_accounts(
                safe=safe_filter.strip() if safe_filter else None,
                limit=limit
            )
            if accounts and len(accounts) > 0:
                # json_normalize flattens nested dictionaries automatically
                df = pd.json_normalize(accounts)
                
                # Dynamic matching accommodates both standard and flat-mapped column keys
                potential_cols = [
                    'id', 'name', 'userName', 'username', 'address', 
                    'safeName', 'platformId', 'secretType', 'creator.name'
                ]
                display_cols = [c for c in potential_cols if c in df.columns]
                
                if not display_cols:
                    display_cols = list(df.columns)
                    
                st.success(f"Found {len(accounts)} accounts")
                st.dataframe(df[display_cols], use_container_width=True)
            else:
                st.warning("No accounts parsed. Check the debug expander below for details.")

# ---------- Safe Explorer ----------
elif page == "Safe Explorer":
    st.title("📁 Safe Explorer")
    if st.button("Load Safes", type="primary"):
        with st.spinner("Loading safes inventory..."):
            safes = st.session_state.client.get_safes()
            if safes and len(safes) > 0:
                # Flatten schema objects to expose 'creator.name' cleanly in table columns
                df = pd.json_normalize(safes)
                
                potential_safe_cols = [
                    'safeNumber', 'safeName', 'description', 
                    'managingCPM', 'numberOfDaysRetention', 'creator.name', 'location'
                ]
                display_cols = [c for c in potential_safe_cols if c in df.columns]
                
                if not display_cols:
                    display_cols = list(df.columns)
                    
                st.success(f"Found {len(safes)} safes")
                st.dataframe(df[display_cols], use_container_width=True)
            else:
                st.warning("No safes parsed. Review permissions or check the debug engine logs.")
