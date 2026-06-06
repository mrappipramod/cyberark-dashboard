import streamlit as st
import pandas as pd
from utils.cyberark_client import CyberArkClient

st.set_page_config(page_title="CyberArk Dashboard", page_icon="🔐", layout="wide")

# 1. Initialize empty session states to prevent load crashes
if 'client' not in st.session_state:
    st.session_state.client = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# 2. Public Login Screen (Shows if not authenticated)
if not st.session_state.authenticated:
    st.title("🔐 CyberArk Access Portal")
    
    with st.form("login_form"):
        st.subheader("Login to Vault")
        url_input = st.text_input("CyberArk PVWA URL", placeholder="https://vault.yourdomain.com")
        user_input = st.text_input("Username")
        pass_input = st.text_input("Password", type="password")
        
        submit_button = st.form_submit_button("Connect")

        if submit_button:
            if url_input and user_input and pass_input:
                with st.spinner("Authenticating..."):
                    client = CyberArkClient(url_input, user_input, pass_input)
                    if client.authenticate():
                        st.session_state.client = client
                        st.session_state.authenticated = True
                        st.success("Successfully authenticated!")
                        st.rerun() # Refresh page to show the dashboard
            else:
                st.warning("Please fill out all fields.")

# 3. Main Dashboard (Shows only after login)
else:
    st.sidebar.title("🔐 CyberArk Dashboard")
    
    # Show connection status and provide a logout button
    st.sidebar.success(f"✅ Connected: {st.session_state.client.username}")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.client = None
        st.rerun()
        
    st.sidebar.divider()

    # Your original navigation
    page = st.sidebar.radio("Navigate", ["Dashboard Overview", "Account Management", "Safe Explorer"])

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
