import streamlit as st
import pandas as pd
import io
from utils.cyberark_client import CyberArkClient

st.set_page_config(page_title="CyberArk Dashboard", page_icon="🔐", layout="wide")

# Initialize distinct tracking properties for standard vs privilege cloud environments
if 'client' not in st.session_state: st.session_state.client = None
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'pcloud_client' not in st.session_state: st.session_state.pcloud_client = None
if 'pcloud_authenticated' not in st.session_state: st.session_state.pcloud_authenticated = False

st.sidebar.title("🔐 CyberArk Unified Console")
page = st.sidebar.radio(
    "Navigate Workspace", 
    ["Dashboard Overview", "Account Management", "Safe Explorer", "Privilege Cloud Portal"]
)

# ---------- Core Dashboard Overview ----------
if page == "Dashboard Overview":
    st.title("📊 CyberArk Dashboard Overview")
    st.info("Navigate through the sidebar panels to inspect system safe metrics, account schemas, and vault states.")

# ---------- Standard Account Management ----------
elif page == "Account Management":
    st.title("👤 Account Management (Standard Vault)")
    
    if not st.session_state.authenticated:
        st.subheader("Login to Standard Vault")
        with st.form("login_form"):
            url_input = st.text_input("CyberArk PVWA URL", placeholder="https://vault.yourdomain.com")
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Connect")

            if submit_button and url_input and user_input and pass_input:
                with st.spinner("Authenticating..."):
                    client = CyberArkClient(url_input, user_input, pass_input)
                    if client.authenticate():
                        st.session_state.client = client
                        st.session_state.authenticated = True
                        st.success("Successfully authenticated!")
                        st.rerun()
                    else:
                        st.error("Authentication failed. Check your URL or credentials.")
    else:
        st.sidebar.success(f"✅ Vault Session: {st.session_state.client.username}")
        if st.sidebar.button("Logout Standard Vault"):
            st.session_state.authenticated = False
            st.session_state.client = None
            st.rerun()

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
                    potential_cols = ['id', 'name', 'userName', 'address', 'safeName', 'platformId', 'secretType']
                    display_cols = [c for c in potential_cols if c in df.columns]
                    st.dataframe(df[display_cols] if display_cols else df, use_container_width=True)
                else:
                    st.warning("No accounts found matching search parameter structures.")

# ---------- Standard Safe Explorer ----------
elif page == "Safe Explorer":
    st.title("📁 Safe Explorer (Standard Vault)")
    if not st.session_state.authenticated:
        st.warning("Please log into the Standard Vault via the 'Account Management' tab first.")
    else:
        if st.button("Load Safes Directory", type="primary"):
            with st.spinner("Processing Safes Inventory..."):
                safes = st.session_state.client.get_safes()
                if safes:
                    df = pd.json_normalize(safes)
                    potential_safe_cols = ['safeNumber', 'safeName', 'description', 'managingCPM', 'numberOfDaysRetention']
                    display_cols = [c for c in potential_safe_cols if c in df.columns]
                    st.dataframe(df[display_cols] if display_cols else df, use_container_width=True)
                else:
                    st.error("Unable to map raw records to target pandas frame.")

# =============================================================================
# Privilege Cloud Portal
# =============================================================================
elif page == "Privilege Cloud Portal":
    st.title("☁️ CyberArk Privilege Cloud Environment")
    st.markdown("Dedicated interface for Service User Identity validation and flat Safe-to-Member compliance tracking.")

    # Show PCloud Authentication form if not already logged in
    if not st.session_state.pcloud_authenticated:
        st.subheader("🔑 Service Account Identity Authentication")
        
        with st.form("pcloud_login_form"):
            pcloud_url = st.text_input("Privilege Cloud URL", placeholder="https://acme.privilegecloud.cyberark.cloud")
            identity_url = st.text_input("Identity Tenant URL", placeholder="https://ack4931.id.cyberark.cloud")
            client_id = st.text_input("Service Account Client ID", placeholder="api_service_user@cyberark.cloud.xxxxx")
            client_secret = st.text_input("Client Secret Key", type="password")
            
            submit_pcloud = st.form_submit_button("Authenticate Service Session", type="primary")

            if submit_pcloud:
                if pcloud_url and identity_url and client_id and client_secret:
                    with st.spinner("Exchanging OAuth2 Token claims with Identity directory..."):
                        # FIXED: This call will no longer raise a TypeError because parameters are now optional
                        p_client = CyberArkClient() 
                        auth_res = p_client.authenticate_pcloud(pcloud_url, identity_url, client_id, client_secret)
                        
                        if auth_res["success"]:
                            st.session_state.pcloud_client = p_client
                            st.session_state.pcloud_authenticated = True
                            st.success("🔒 OAuth Token established successfully! Privilege Cloud Session initialized.")
                            st.rerun()
                        else:
                            st.error(f"Authentication Failed: {auth_res['error']}")
                else:
                    st.warning("All 4 parameters are required to generate a Service User token.")

    # Show Report Generation & Safe Utilities once logged into PCloud
    else:
        st.sidebar.success("✅ PCloud Session Active")
        if st.sidebar.button("Disconnect PCloud"):
            st.session_state.pcloud_authenticated = False
            st.session_state.pcloud_client = None
            st.rerun()

        st.subheader("📋 Safe Membership Permissions Matrix")
        st.info("Extracts and flattens all 22 default safe authorization permissions for audit reporting.")

        permission_keys = [
            "useAccounts", "retrieveAccounts", "listAccounts", "addAccounts",
            "updateAccountContent", "updateAccountProperties", "initiateCPMAccountManagementOperations",
            "specifyNextAccountContent", "renameAccounts", "deleteAccounts", "unlockAccounts",
            "manageSafe", "manageSafeMembers", "backupSafe", "viewAuditLog", "viewSafeMembers",
            "accessWithoutConfirmation", "createFolders", "deleteFolders", "moveAccountsAndFolders",
            "requestsAuthorizationLevel1", "requestsAuthorizationLevel2"
        ]

        if st.button("Generate Matrix Audit Report", type="primary"):
            with st.spinner("Discovering PCloud safe structures..."):
                safes = st.session_state.pcloud_client.get_pcloud_safes()
                
            if not safes:
                st.error("Could not fetch target safes or index is empty. Check service user permissions.")
            else:
                report_data = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                total_safes = len(safes)
                
                for index, safe in enumerate(safes):
                    safe_name = safe.get("safeName")
                    safe_desc = safe.get("description", "")
                    cpm_name = safe.get("managingCPM", "")
                    
                    status_text.text(f"Auditing PCloud memberships: {safe_name} ({index + 1}/{total_safes})")
                    progress_bar.progress((index + 1) / total_safes)
                    
                    members = st.session_state.pcloud_client.get_pcloud_safe_members(safe_name)
                    
                    if members is None:
                        error_row = {
                            "SafeName": safe_name, "SafeDescription": safe_desc, "ManagingCPM": cpm_name,
                            "MemberName": "ERROR RETRIEVING MEMBERS", "MemberType": "N/A"
                        }
                        for k in permission_keys: error_row[k.capitalize()] = None
                        report_data.append(error_row)
                        
                    elif len(members) == 0:
                        empty_row = {
                            "SafeName": safe_name, "SafeDescription": safe_desc, "ManagingCPM": cpm_name,
                            "MemberName": "NO MEMBERS FOUND", "MemberType": "N/A"
                        }
                        for k in permission_keys: empty_row[k.capitalize()] = None
                        report_data.append(empty_row)
                        
                    else:
                        for m in members:
                            m_name = m.get("memberName", "Unknown")
                            m_perms = m.get("permissions", {})
                            m_type = "User" if "@" in m_name else "Group"
                            
                            row = {
                                "SafeName": safe_name, "SafeDescription": safe_desc, "ManagingCPM": cpm_name,
                                "MemberName": m_name, "MemberType": m_type
                            }
                            for key in permission_keys:
                                row[key.capitalize()] = True if m_perms.get(key) is True else False
                                
                            report_data.append(row)
                
                status_text.text("Audit processing pipeline completed!")
                df_report = pd.DataFrame(report_data)
                st.success(f"Successfully processed matrix definitions! Total assignment lines: {len(df_report)}")
                
                # Setup Download Buffer
                csv_buffer = io.StringIO()
                df_report.to_csv(csv_buffer, index=False, encoding='utf-8')
                csv_bytes = csv_buffer.getvalue()
                
                st.download_button(
                    label="📥 Download PCloud Compliance Report (CSV)",
                    data=csv_bytes,
                    file_name="PCloud_Flattened_Permissions_Report.csv",
                    mime="text/csv"
                )
                
                st.dataframe(df_report, use_container_width=True)
