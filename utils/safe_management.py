import streamlit as st
import pandas as pd
import datetime
import time
from utils.cyberark_client import CyberArkClient

st.set_page_config(page_title="Vault Control Panel", page_icon="🗃️", layout="wide")

if 'client' not in st.session_state:
    st.session_state.client = CyberArkClient()

st.title("🗃️ CyberArk Safe Lifecycle & Membership Portal")
st.markdown("Administrative toolkit for structural environment provisioning, target isolation, and conditional authorization bounds.")
st.write("---")

# UI Segment Splitter Tabs
tab_inventory, tab_create, tab_members = st.tabs([
    "🔍 Safe Directory & Deletion", 
    "➕ Bulk Safe Creation", 
    "👥 Membership & Lease Administration"
])

# ---------------------------------------------------------
# TAB 1: SAFE INVENTORY & TARGET DELETION
# ---------------------------------------------------------
with tab_inventory:
    st.header("Vault Directory Index")
    if st.button("🔄 Sync Safe Inventories", type="secondary"):
        with st.spinner("Re-indexing safes..."):
            st.session_state.all_safes = st.session_state.client.get_safes()

    safes_list = st.session_state.get('all_safes', [])
    
    if safes_list:
        df_safes = pd.json_normalize(safes_list)
        clean_cols = ['safeName', 'description', 'managingCPM', 'numberOfDaysRetention']
        display_cols = [c for c in clean_cols if c in df_safes.columns]
        
        st.dataframe(df_safes[display_cols], use_container_width=True)
        
        st.markdown("### ⚠️ Destructive Safe Actions")
        target_del = st.selectbox("Select a target Safe to completely erase from Vault:", [""] + list(df_safes['safeName'].unique()))
        
        if target_del:
            st.warning(f"CRITICAL WARN: Deleting '{target_del}' instantly destroys all encrypted secrets located within it.")
            confirm_check = st.checkbox(f"I verify that I want to completely delete {target_del}")
            
            if st.button(f"💥 Execute Destruction of {target_del}", type="primary", disabled=not confirm_check):
                with st.spinner("Processing API execution..."):
                    success, msg = st.session_state.client.delete_safe(target_del)
                    if success:
                        st.success(f"Safe '{target_del}' has been dropped cleanly from the Vault architecture.")
                        st.session_state.all_safes = st.session_state.client.get_safes()
                    else:
                        st.error(f"Execution Failed: {msg}")
    else:
        st.info("No synced information found. Trigger the Sync operation button above.")

# ---------------------------------------------------------
# TAB 2: BULK SAFE CREATION
# ---------------------------------------------------------
with tab_create:
    st.header("Multi-Safe Provisioning")
    st.markdown("Build or paste multiple intended records. Use `+ Add row` to expand structural assignments simultaneously.")
    
    initial_template = [{"Safe Name": "", "Description": "", "Managing CPM": "PasswordManager1", "Retention Days": 30}]
    edited_grid = st.data_editor(
        pd.DataFrame(initial_template),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Safe Name": st.column_config.TextColumn("Safe Name*", required=True),
            "Description": st.column_config.TextColumn("Description Mapping"),
            "Managing CPM": st.column_config.TextColumn("Assigned CPM Engine", default="PasswordManager1"),
            "Retention Days": st.column_config.NumberColumn("History Lifecycle (Days)", default=30)
        }
    )

    if st.button("🚀 Push Provisioning Requests", type="primary"):
        records = edited_grid.to_dict(orient="records")
        success_ops = 0
        
        for idx, item in enumerate(records):
            s_name = str(item.get("Safe Name", "")).strip()
            if not s_name:
                continue
            
            payload = {
                "safeName": s_name,
                "description": str(item.get("Description", "")),
                "managingCPM": str(item.get("Managing CPM", "PasswordManager1")),
                "numberOfDaysRetention": int(item.get("Retention Days", 30))
            }
            
            ok, response_info = st.session_state.client.create_safe(payload)
            if ok:
                success_ops += 1
                st.toast(f"Created safe: {s_name} ✅")
            else:
                st.error(f"Row {idx+1} ({s_name}) Failure -> {response_info}")
                
        if success_ops > 0:
            st.success(f"Provisioning matrix run complete. Successfully built {success_ops} new safes.")
            st.session_state.all_safes = st.session_state.client.get_safes()

# ---------------------------------------------------------
# TAB 3: MEMBERSHIP & LEASE ADMINISTRATION
# ---------------------------------------------------------
with tab_members:
    st.header("Vault Authorization & Expiration Controls")
    
    # Safe Target Selector setup
    safe_names = [s.get('safeName') for s in safes_list] if safes_list else []
    selected_safe_m = st.selectbox("Select Target Safe Workspace:", [""] + safe_names)
    
    if selected_safe_m:
        # Fetch and view direct current memberships mapping
        with st.spinner("Querying safe account mappings..."):
            current_members = st.session_state.client.get_safe_members(selected_safe_m)
            
        col_view, col_actions = st.columns([3, 2])
        
        with col_view:
            st.markdown(f"#### Active Mappings on `{selected_safe_m}`")
            if current_members:
                df_m = pd.json_normalize(current_members)
                view_perms = ['memberName', 'memberType', 'membershipExpirationDate']
                existing_cols = [col for col in view_perms if col in df_m.columns]
                st.dataframe(df_m[existing_cols], use_container_width=True)
            else:
                st.info("No custom assigned membership mappings currently bind to this workspace.")
                
        with col_actions:
            st.markdown("#### Modify Authorization Map")
            op_mode = st.radio("Operation Focus:", ["Add Member", "Update Lease Expiration", "Evict Member"])
            
            m_identity = st.text_input("Identity Target Name (User/Group Namespace):", placeholder="e.g. AD_Eng_Group")
            
            # Lease Validation Handling
            use_expiry = st.checkbox("Enforce Permission Lease Window Expiration")
            epoch_val = None
            if use_expiry:
                tgt_date = st.date_input("Lease Termination Expiration Date", datetime.date.today() + datetime.timedelta(days=7))
                tgt_time = st.time_input("Termination Window Timestamp Lock", datetime.time(23, 59))
                combined_dt = datetime.datetime.combine(tgt_date, tgt_time)
                epoch_val = int(time.mktime(combined_dt.timetuple()))

            if op_mode == "Add Member":
                st.markdown("**Privilege Level Presets:**")
                preset = st.selectbox("Role Scope Assignment Matrix:", ["Read-Only (Consumer)", "Read-Write (Operator)", "Full Admin"])
                
                # Preset definitions mapping logic
                perm_map = {
                    "useAccounts": True, "retrieveAccounts": True, "listAccounts": True,
                    "addAccounts": preset in ["Read-Write (Operator)", "Full Admin"],
                    "updateAccountContent": preset in ["Read-Write (Operator)", "Full Admin"],
                    "updateAccountProperties": preset in ["Read-Write (Operator)", "Full Admin"],
                    "manageSafeMembers": preset == "Full Admin",
                    "manageSafe": preset == "Full Admin"
                }
                
                if st.button("➕ Confirm Provision Member", type="primary") and m_identity:
                    status, message = st.session_state.client.add_safe_member(selected_safe_m, m_identity, perm_map, epoch_val)
                    if status:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

            elif op_mode == "Update Lease Expiration":
                st.info("Modifies the active lease date envelope constraints without restructuring base account rights.")
                if st.button("⏳ Apply Adjust Lease Terms") and m_identity and epoch_val:
                    status, message = st.session_state.client.update_safe_member_expiration(selected_safe_m, m_identity, epoch_val)
                    if status:
                        st.success("Lease lifecycle criteria adjusted cleanly.")
                        st.rerun()
                    else:
                        st.error(message)

            elif op_mode == "Evict Member":
                st.warning("Warning: Removing rights instantly breaks dependent execution pipelines using this namespace context.")
                if st.button("❌ Remove Access Privileges", type="primary") and m_identity:
                    status, message = st.session_state.client.remove_safe_member(selected_safe_m, m_identity)
                    if status:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
