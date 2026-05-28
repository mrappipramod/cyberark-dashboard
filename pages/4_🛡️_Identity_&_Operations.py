import streamlit as st
import pandas as pd

st.set_page_config(page_title="Identity & Operations Portal", page_icon="🛡️", layout="wide")
st.title("🛡️ Identity Security & Vault Operations Dashboard")

client = st.session_state.get('client')

if not client or (not client.token and not client.authenticate()):
    st.warning("Please verify your global connection settings on the main home dashboard page.")
    st.stop()

# Segment operational boundaries logically into distinct workspaces
tab_health, tab_users, tab_requests = st.tabs([
    "🖥️ System Health (Get-PASComponentSummary)", 
    "👥 Identity Management (Users & Groups)", 
    "📥 Dual-Control Approvals (Requests)"
])

# ---------------------------------------------------------
# WORKSPACE 1: SYSTEM HEALTH MONITORING
# ---------------------------------------------------------
with tab_health:
    st.subheader("CyberArk Infrastructure Component Health Matrix")
    
    if st.button("📊 Query Component Status Summary", type="primary"):
        with st.spinner("Retrieving structural component reports..."):
            # Hits /PasswordVault/api/ComponentsMonitoringSummary
            data, err = client.generic_request("GET", "PasswordVault/api/ComponentsMonitoringSummary")
            
            if data and "Components" in data:
                components_list = data["Components"]
                df_health = pd.json_normalize(components_list)
                st.success("Infrastructure health summary parsed successfully.")
                st.dataframe(df_health, use_container_width=True)
            else:
                st.error(f"Could not retrieve system summary metadata: {err}")

# ---------------------------------------------------------
# WORKSPACE 2: USERS & GROUPS LIFECYCLE
# ---------------------------------------------------------
with tab_users:
    st.subheader("Directory Vault Identity Management Engine")
    
    action_mode = st.radio("Select Action Focus Profile:", ["List Users (Get-PASUser)", "Provision User (New-PASUser)"], horizontal=True)
    
    if action_mode == "List Users (Get-PASUser)":
        search_filter = st.text_input("Filter directory namespace search parameters (Optional):")
        if st.button("🔍 Pull Directory Records", type="secondary"):
            params = {"search": search_filter} if search_filter else None
            data, err = client.generic_request("GET", "PasswordVault/api/Users", params=params)
            
            if data:
                users_raw = data.get("Users", data.get("value", data))
                if users_raw:
                    st.dataframe(pd.json_normalize(users_raw), use_container_width=True)
                else:
                    st.info("No explicit identities found matching criteria.")
            else:
                st.error(f"Directory API error: {err}")
                
    elif action_mode == "Provision User (New-PASUser)":
        with st.form("new_user_form"):
            st.markdown("##### Identity Generation Profiles")
            col1, col2 = st.columns(2)
            with col1:
                u_name = st.text_input("Username*")
                u_type = st.selectbox("User Licensing Type Role:", ["EPVUser", "BasicUser", "ExternalUser"])
            with col2:
                u_pass = st.text_input("Initial Password Assignment*", type="password")
                u_email = st.text_input("Email Contact Binding Address")
                
            if st.form_submit_button("🚀 Commit Target User to Vault"):
                if not u_name or not u_pass:
                    st.error("Missing mandatory data parameters.")
                else:
                    user_payload = {
                        "username": u_name,
                        "initialPassword": u_pass,
                        "userType": u_type,
                        "email": u_email,
                        "enableUser": True
                    }
                    res, err = client.generic_request("POST", "PasswordVault/api/Users", payload=user_payload)
                    if res:
                        st.success(f"Identity entity '{u_name}' successfully provisioned to Directory Store.")
                    else:
                        st.error(f"Provisioning run broken: {err}")

# ---------------------------------------------------------
# WORKSPACE 3: DUAL-CONTROL WORKFLOWS (REQUESTS)
# ---------------------------------------------------------
with tab_requests:
    st.subheader("Incoming Authorization Approvals Ledger Matrix")
    st.markdown("Track and sign off on safe access approvals via Dual Control.")

    if st.button("📥 Load Active Action Requests Ledger", type="secondary"):
        with st.spinner("Fetching open requests map..."):
            # Hits /PasswordVault/api/IncomingRequests
            data, err = client.generic_request("GET", "PasswordVault/api/IncomingRequests")
            if data:
                req_list = data.get("IncomingRequests", [])
                if req_list:
                    df_req = pd.json_normalize(req_list)
                    st.dataframe(df_req, use_container_width=True)
                else:
                    st.info("Clear ledger. No actions are currently waiting execution approval.")
            else:
                st.error(f"Requests error: {err}")

    # Interactive Action Execution Layout Framework Template
    st.markdown("---")
    st.markdown("#### ⚡ Quick Decision Routing Matrix")
    c_id, c_action = st.columns([2, 2])
    with c_id:
        target_req_id = st.text_input("Enter Target Request ID:", placeholder="e.g. 23_4")
    with c_action:
        decision = st.selectbox("Assign Resolution State Rule:", ["Confirm/Approve", "Deny/Reject"])
    
    if st.button("✍️ Sign and Commit Verification State", type="primary"):
        if not target_req_id:
            st.error("Please supply a valid validation path indexing identifier.")
        else:
            action_path = "Approve" if decision.startswith("Confirm") else "Deny"
            # Dynamic construction mapping down into REST framework endpoint targets
            endpoint_url = f"PasswordVault/api/IncomingRequests/{target_req_id}/{action_path}"
            
            res, err = client.generic_request("POST", endpoint_url, payload={})
            if res:
                st.success(f"Request state index '{target_req_id}' updated to {action_path}ed!")
            else:
                st.error(f"Failed to apply routing transformation rule: {err}")
