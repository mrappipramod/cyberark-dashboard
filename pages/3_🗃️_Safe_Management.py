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
    st.warning("Please configure your secrets or verify Vault connection connectivity in the entry point dashboard page.")
    st.stop()

tab_view, tab_bulk_create, tab_membership = st.tabs([
    "🔍 Directory Index & Deletion", 
    "➕ Bulk Safe Creation", 
    "👥 Membership & Lease Controls"
])

# TAB 1: INDEX & DELETION
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

# TAB 2: BULK DATA EDITOR CREATION
with tab_bulk_create:
    st.subheader("Batch Safe Provisioning Grid")
    initial_template = [{"Safe Name": "", "Description": "", "Managing CPM": "PasswordManager1", "Retention Days": 30}]
    grid = st.data_editor(pd.DataFrame(initial_template), num_rows="dynamic", use_container_width=True)
    
    if st.button("🚀 Process Bulk Safe Ingestion", type="primary"):
        success_count = 0
        for idx, row in enumerate(grid.to_dict(orient="records")):
            s_name = str(row.get("Safe Name", "")).strip()
            if not s_name: continue
            payload = {
                "safeName": s_name, 
                "description": str(row.get("Description", "")),
                "managingCPM": str(row.get("Managing CPM", "PasswordManager1")),
                "numberOfDaysRetention": int(row.get("Retention Days", 30))
            }
            ok, err = create_safe_api(client, payload)
            if ok: success_count += 1
            else: st.error(f"Failed '{s_name}': {err}")
        if success_count > 0:
            st.success(f"Created {success_count} safes successfully!")
            st.session_state.cached_safes = client.get_safes()

# TAB 3: MEMBERSHIPS & LEASES
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
                st.info("No custom users mapped.")
                
        with c2:
            st.markdown("#### Modify Governance Map")
            mode = st.radio("Action:", ["Add", "Update Expiry", "Remove"])
            identity = st.text_input("User/Group Target Name:")
            
            use_expiry = st.checkbox("Set Permission Expiration Date")
            epoch = None
            if use_expiry:
                d = st.date_input("Expiry Date", datetime.date.today() + datetime.timedelta(days=7))
                t = st.time_input("Expiry Time", datetime.time(23, 59))
                epoch = int(time.mktime(datetime.datetime.combine(d, t).timetuple()))
                
            if st.button("Apply Operation", type="primary") and identity:
                if mode == "Add":
                    role = st.selectbox("Role Model Preset:", ["Read-Only", "Admin"])
                    perms = {"useAccounts": True, "retrieveAccounts": True, "listAccounts": True, "manageSafe": role == "Admin"}
                    ok, err = add_safe_member_api(client, selected_safe, identity, perms, epoch)
                elif mode == "Update Expiry":
                    ok, err = update_member_expiry_api(client, selected_safe, identity, epoch)
                else:
                    ok, err = remove_safe_member_api(client, selected_safe, identity)
                
                if ok: st.success("Success!"); st.rerun()
                else: st.error(err)
