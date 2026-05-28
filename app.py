import streamlit as st
import pandas as pd
from utils.cyberark_client import CyberArkClient

st.set_page_config(page_title="CyberArk Dashboard", page_icon="🔐", layout="wide")

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
    st.info("Navigate through the sidebar panels to inspect system safe metrics, account schemas, and vault states.")

# ---------- Account Management ----------
elif page == "Account Management":
    st.title("👤 Account Management")
    col1, col2 = st.columns(2)
    with col1:
        safe_filter = st.text_input("Filter by Safe (optional)", placeholder="e.g. DOM-ADM-WIN-ACCOUNTS")
    with col2:
        limit = st.number_input("Max results", min_value=10, max_value=500, value=50, step=10)

    if st.button("Fetch Accounts", type="primary"):
        with st.spinner("Processing Accounts Data..."):
            accounts = st.session_state.client.get_accounts(
                safe=safe_filter.strip() if safe_filter else None,
                limit=limit
            )
            if accounts:
                df = pd.json_normalize(accounts)
                potential_cols = [
                    'id', 'name', 'userName', 'address', 
                    'safeName', 'platformId', 'secretType', 'creator.name'
                ]
                display_cols = [c for c in potential_cols if c in df.columns]
                if not display_cols:
                    display_cols = list(df.columns)
                    
                st.success(f"Displaying {len(accounts)} Accounts")
                st.dataframe(df[display_cols], use_container_width=True)
            else:
                st.error("Unable to render accounts layout.")

# ---------- Safe Explorer ----------
elif page == "Safe Explorer":
    st.title("📁 Safe Explorer")
    if st.button("Load Safes", type="primary"):
        with st.spinner("Processing Safes Inventory..."):
            safes = st.session_state.client.get_safes()
            if safes:
                df = pd.json_normalize(safes)
                potential_safe_cols = [
                    'safeNumber', 'safeName', 'description', 
                    'managingCPM', 'numberOfDaysRetention', 'creator.name'
                ]
                display_cols = [c for c in potential_safe_cols if c in df.columns]
                if not display_cols:
                    display_cols = list(df.columns)
                    
                st.success(f"Displaying {len(safes)} Safes")
                st.dataframe(df[display_cols], use_container_width=True)
            else:
                st.error("Unable to render safes layout.")
