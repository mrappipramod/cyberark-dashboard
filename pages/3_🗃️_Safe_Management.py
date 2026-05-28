import streamlit as st
import pandas as pd
import datetime
import time

# --- STANDALONE API HELPERS (Keeping cyberark_client.py untouched) ---

def create_safe_api(client, payload):
    url = f"{client.url}/PasswordVault/api/Safes"
    try:
        resp = client.session.post(url, json=payload, timeout=10, verify=False)
        return (True, "Created") if resp.status_code in [200, 201] else (False, resp.text)
    except Exception as e:
        return False, str(e)

def delete_safe_api(client, safe_name):
    url = f"{client.url}/PasswordVault/api/Safes/{safe_name}"
    try:
        resp = client.session.delete(url, timeout=10, verify=False)
        return (True, "Deleted") if resp.status_code in [200, 204] else (False, resp.text)
    except Exception as e:
        return False, str(e)

def get_safe_members_api(client, safe_name):
    url = f"{client.url}/PasswordVault/api/Safes/{safe_name}/Members"
    try:
        resp = client.session.get(url, timeout=10, verify=False)
        return resp.json().get("value", []) if resp.status_code == 200 else []
    except Exception:
        return []

def add_safe_member_api(client, safe_name, member_name, permissions, expiry=None):
    url = f"{client.url}/PasswordVault/api/Safes/{safe_name}/Members"
    payload = {"memberName": member_name, "searchIn": "Vault", "permissions": permissions}
    if expiry:
        payload["membershipExpirationDate"] = expiry
    try:
        resp = client.session.post(url, json=payload, timeout=10, verify=False)
        return (True, "Added") if resp.status_code in [200, 201] else (False, resp.text)
    except Exception as e:
        return False, str(e)

def remove_safe_member_api(client, safe_name, member_name):
    url = f"{client.url}/PasswordVault/api/Safes/{safe_name}/Members/{member_name}"
    try:
        resp = client.session.delete(url, timeout=10, verify=False)
        return (True, "Removed") if resp.status_code in [200, 204] else (False, resp.text)
    except Exception as e:
        return False, str(e)

def update_member_expiry_api(client, safe_name, member_name, expiry):
    url = f"{client.url}/PasswordVault/api/Safes/{safe_name}/Members/{member_name}"
    try:
        resp = client.session.put(url, json={"membershipExpirationDate": expiry}, timeout=10, verify=False)
        return (True, "Updated") if resp.status_code in [200, 204] else (False, resp.text)
    except Exception as e:
        return False, str(e)


# --- STREAMLIT PAGE INTERFACE UI ---

st.title("🗃️ Safe Lifecycle & Membership Management")
client = st.session_state.get('client')

# Fallback auth verification check
if not client or (not client.token and not client.authenticate()):
    st.warning("Please configure your secrets or verify Vault connection connectivity on the main application dashboard page.")
    st.stop()

tab_view, tab_bulk_create, tab_membership = st.tabs([
    "🔍 Directory Index & Deletion", 
    "📊 Bulk Safe Upload (Excel)", 
    "👥 Membership & Granular Permissions"
])

# ---------------------------------------------------------
# TAB 1: DIRECTORY INDEX & TARGET DELETION
# ---------------------------------------------------------
with tab_view:
    if st.button("🔄 Sync Safe Inventories", type="secondary") or 'cached_safes' not in st.session_state:
        st.session_state.cached_safes = client.get_safes()
        
    safes = st.session_state.cached_safes
    if safes:
        df = pd.json_normalize(safes)
        cols = [c for c in ['safeName', 'description', 'managingCPM', 'numberOfDaysRetention'] if c in df.columns]
        st.dataframe(df[cols], use_container_width=True)
        
        st.markdown("### ⚠️ Destructive Administrative Actions")
        target_del = st.selectbox("Select a target Safe to permanently drop:", [""] + list(df['safeName'].unique()))
        if target_del:
            st.error(f"CRITICAL: Deleting '{target_del}' destroys all secrets inside it.")
            confirm = st.checkbox(f"Confirm absolute deletion of {target_del}")
            if st.button("💥 Execute Safe Erasure", type="primary", disabled=not confirm):
                ok, err = delete_safe_api(client, target_del)
                if ok:
                    st.success(f"Safe '{target_del}' dropped.")
                    st.session_state.cached_safes = client.get_safes()
                    st.rerun()
                else:
                    st.error(err)

# ---------------------------------------------------------
# TAB 2: BULK SAFE CREATION VIA EXCEL UPLOAD
# ---------------------------------------------------------
with tab_bulk_create:
    st.subheader("Excel Spreadsheet Ingestion Portal")
    st.markdown("""
    Upload an Excel file (`.xlsx` or `.xls`) to provision safes in bulk. 
    Your spreadsheet layout should include the following exact header names:
    * **`Safe Name`** (Required)
    * **`Description`** (Optional)
    * **`Managing CPM`** (Optional, defaults to `PasswordManager1`)
    * **`Retention Days`** (Optional, defaults to `30`)
    """)

    uploaded_file = st.file_uploader("Choose your provisioning Excel document", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            # Read spreadsheet directly into Pandas
            excel_df = pd.read_excel(uploaded_file)
            
            # Map variations or trim whitespaces from header keys
            excel_df.columns = [str(c).strip() for c in excel_df.columns]
            
            # Form validation checking for key attributes
            if "Safe Name" not in excel_df.columns:
                st.error("❌ Invalid Sheet Structure: Missing mandatory 'Safe Name' column header allocation.")
            else:
                st.markdown("### 📋 Staged Records Preview")
                st.dataframe(excel_df, use_container_width=True)
                
                if st.button("🚀 Process Bulk Safe Ingestion", type="primary"):
                    success_count = 0
                    records = excel_df.to_dict(orient="records")
                    
                    progress_bar = st.progress(0)
                    total_rows = len(records)
                    
                    for idx, row in enumerate(records):
                        s_name = str(row.get("Safe Name", "")).strip()
                        if not s_name or pd.isna(row.get("Safe Name")): 
                            continue
                            
                        # Extract row parameters with secure default stand-ins
                        desc = str(row.get("Description", "")) if not pd.isna(row.get("Description")) else ""
                        cpm = str(row.get("Managing CPM", "PasswordManager1")) if not pd.isna(row.get("Managing CPM")) else "PasswordManager1"
                        retention = int(row.get("Retention Days", 30)) if not pd.isna(row.get("Retention Days")) else 30
                        
                        payload = {
                            "safeName": s_name, 
                            "description": desc,
                            "managingCPM": cpm,
                            "numberOfDaysRetention": retention
                        }
                        
                        ok, err = create_safe_api(client, payload)
                        if ok: 
                            success_count += 1
                        else: 
                            st.error(f"Failed to create safe '{s_name}': {err}")
                            
                        progress_bar.progress((idx + 1) / total_rows)
                        
                    if success_count > 0:
                        st.success(f"🎉 Created {success_count} / {total_rows} safes successfully from file!")
                        st.session_state.cached_safes = client.get_safes()
        except Exception as e:
            st.error(f"Error parsing file: {str(e)}")

# ---------------------------------------------------------
# TAB 3: MEMBERSHIPS & GRANULAR PERMISSIONS
# ---------------------------------------------------------
with tab_membership:
    safe_names = [s.get('safeName') for s in safes] if safes else []
    selected_safe = st.selectbox("Target Safe Workspace:", [""] + safe_names)
    
    if selected_safe:
        members = get_safe_members_api(client, selected_safe)
        c1, c2 = st.columns([3, 2])
        
        with c1:
            st.markdown("#### Active Member Assignments")
            if members:
                df_m = pd.json_normalize(members)
                m_cols = [c for c in ['memberName', 'memberType', 'membershipExpirationDate'] if c in df_m.columns]
                st.dataframe(df_m[m_cols], use_container_width=True)
            else:
                st.info("No custom users mapped to this safe.")
                
        with c2:
            st.markdown("#### Access Control Configuration")
            mode = st.radio("Action:", ["Add / Modify Member", "Update Expiry Only", "Remove Member"])
            identity = st.text_input("User or Group Target Name:", placeholder="e.g. AD_Domain_Admins")
            
            # Lease Validation Handling
            use_expiry = st.checkbox("Set Permission Expiration Lease Window")
            epoch = None
            if use_expiry:
                d = st.date_input("Expiry Date", datetime.date.today() + datetime.timedelta(days=7))
                t = st.time_input("Expiry Time", datetime.time(23, 59))
                epoch = int(time.mktime(datetime.datetime.combine(d, t).timetuple()))
                
            if mode == "Add / Modify Member":
                # Granular role selector matrix requested by user
                role_preset = st.selectbox(
                    "Select Vault Permission Profile:", 
                    [
                        "Connect Only (PSM Connection Without Password Visibility)",
                        "Read-Only / Consumer (View & Copy Secrets)",
                        "Object Manager / Operator (Add & Edit Passwords)",
                        "Full Admin / Safe Manager (Full Access & Membership Delegation)",
                        "Custom (Manual Checkbox Overrides)"
                    ]
                )
                
                # Base structure assignments declaration
                perms = {
                    "useAccounts": False, "retrieveAccounts": False, "listAccounts": False,
                    "addAccounts": False, "updateAccountContent": False, "updateAccountProperties": False,
                    "initiateCPMAccountManagementOperations": False, "manageSafeMembers": False, "manageSafe": False
                }
                
                # Apply explicit permissions maps to presets
                if role_preset.startswith("Connect Only"):
                    perms["useAccounts"] = True
                    perms["listAccounts"] = True
                    perms["retrieveAccounts"] = False  # Blocks target password extraction
                elif role_preset.startswith("Read-Only"):
                    perms["useAccounts"] = True
                    perms["listAccounts"] = True
                    perms["retrieveAccounts"] = True
                elif role_preset.startswith("Object Manager"):
                    perms["useAccounts"] = True; perms["listAccounts"] = True; perms["retrieveAccounts"] = True
                    perms["addAccounts"] = True; perms["updateAccountContent"] = True; perms["updateAccountProperties"] = True
                    perms["initiateCPMAccountManagementOperations"] = True
                elif role_preset.startswith("Full Admin"):
                    for key in perms:
                        perms[key] = True
                        
                # Expose specific check overrides if user requires manual adjustment
                if role_preset.startswith("Custom"):
                    st.markdown("##### 🛠️ Fine-Grained Permissions Overrides:")
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        perms["useAccounts"] = st.checkbox("Use Accounts (Trigger PSM)")
                        perms["retrieveAccounts"] = st.checkbox("Retrieve Accounts (Show Password)")
                        perms["listAccounts"] = st.checkbox("List Accounts")
                        perms["addAccounts"] = st.checkbox("Add Accounts")
                    with col_p2:
                        perms["updateAccountContent"] = st.checkbox("Update Account Content")
                        perms["updateAccountProperties"] = st.checkbox("Update Account Properties")
                        perms["initiateCPMAccountManagementOperations"] = st.checkbox("Trigger CPM Rotations")
                        perms["manageSafeMembers"] = st.checkbox("Manage Safe Membership Permissions")
                        perms["manageSafe"] = st.checkbox("Modify Safe Infrastructure Parameters")

            if st.button("Apply Security Directive", type="primary") and identity:
                if mode == "Add / Modify Member":
                    ok, err = add_safe_member_api(client, selected_safe, identity, perms, epoch)
                elif mode == "Update Expiry Only":
                    if not epoch:
                        st.error("Please enable and select an expiration deadline date profile.")
                        st.stop()
                    ok, err = update_member_expiry_api(client, selected_safe, identity, epoch)
                else:
                    ok, err = remove_safe_member_api(client, selected_safe, identity)
                
                if ok: 
                    st.success("CyberArk Operation Completed Successfully!")
                    st.rerun()
                else: 
                    st.error(f"API Execution Failure: {err}")
