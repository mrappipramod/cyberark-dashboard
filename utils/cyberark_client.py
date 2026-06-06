import streamlit as st
import requests
import json

# Suppress insecure request warnings if you are using verify=False
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CyberArkClient:
    def __init__(self, url, username, password):
        # Taking inputs directly from instantiation rather than st.secrets
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.session = None
        self.token = None

    def authenticate(self):
        if not self.url or not self.username or not self.password:
            st.error("Missing credentials. Please fill in all fields.")
            return False

        auth_url = f"{self.url}/PasswordVault/api/auth/CyberArk/Logon"
        try:
            response = requests.post(
                auth_url,
                json={"username": self.username, "password": self.password},
                verify=False, # Note: Set to True in production if you have valid certs
                timeout=10
            )
            if response.status_code == 200:
                data = response.json() if hasattr(response, "json") else response.text
                if isinstance(data, dict):
                    self.token = data.get("CyberArkToken") or data.get("token") or data.get("access_token")
                else:
                    self.token = response.text.strip('"')

                self.session = requests.Session()
                self.session.headers.update({
                    "Authorization": self.token,
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                })
                return True
            else:
                st.error(f"Login failed: HTTP {response.status_code} - {response.text}")
                return False
        except Exception as e:
            st.error(f"Authentication Error: {str(e)}")
            return False

    def generic_request(self, method, endpoint, payload=None, params=None):
        if not self.token and not self.authenticate():
            return None, "Authentication failure"

        clean_endpoint = endpoint.lstrip('/')
        full_url = f"{self.url}/{clean_endpoint}"
        
        try:
            resp = self.session.request(
                method=method.upper(),
                url=full_url,
                json=payload,
                params=params,
                verify=False,
                timeout=12
            )
            
            if resp.status_code in [200, 201]:
                try:
                    return resp.json(), None
                except json.JSONDecodeError:
                    return {"status": "Success", "message": resp.text}, None
            elif resp.status_code in [204]:
                return {"status": "Success", "message": "Operation completed without content response"}, None
            else:
                return None, f"HTTP {resp.status_code}: {resp.text}"
        except Exception as e:
            return None, str(e)

    def get_accounts(self, *args, **kwargs):
        params = {}
        
        if kwargs.get("limit"):
            params["limit"] = kwargs["limit"]
        if kwargs.get("search"):
            params["search"] = kwargs["search"]
            
        if kwargs.get("safe"):
            params["filter"] = f"safeName eq '{kwargs['safe']}'"
            
        data, err = self.generic_request("GET", "PasswordVault/api/Accounts", params=params)
        
        if data:
            return data.get("value", []) if isinstance(data, dict) else data
        
        if err:
            st.error(f"Vault API rejection: {err}")
            
        return []

    def get_safes(self):
        data, err = self.generic_request("GET", "PasswordVault/api/Safes")
        if data:
            return data.get("value", []) if isinstance(data, dict) else data
        return []


# --- 🖥️ STREAMLIT PUBLIC UI & SESSION MANAGEMENT ---

def main():
    st.set_page_config(page_title="CyberArk Portal", page_icon="🔐")
    st.title("🔐 CyberArk Access Portal")

    # Initialize session state to track login status
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.client = None

    # Show Login Form if not authenticated
    if not st.session_state.authenticated:
        with st.form("login_form"):
            st.subheader("Login to Vault")
            url_input = st.text_input("CyberArk PVWA URL", placeholder="https://vault.yourdomain.com")
            user_input = st.text_input("Username")
            pass_input = st.text_input("Password", type="password")
            
            submit_button = st.form_submit_button("Connect")

            if submit_button:
                if url_input and user_input and pass_input:
                    with st.spinner("Authenticating..."):
                        # Instantiate the client with user-provided credentials
                        client = CyberArkClient(url_input, user_input, pass_input)
                        success = client.authenticate()
                        
                        if success:
                            # Save state
                            st.session_state.authenticated = True
                            st.session_state.client = client
                            st.success("Successfully authenticated!")
                            st.rerun() # Refresh page to show dashboard
                else:
                    st.warning("Please fill out all fields.")

    # Show Dashboard if authenticated
    else:
        client = st.session_state.client
        st.success(f"Connected to {client.url} as **{client.username}**")
        
        # Sidebar for logout
        with st.sidebar:
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.client = None
                st.rerun()

        # Demo Functionality
        tab1, tab2 = st.tabs(["Get Safes", "Get Accounts"])
        
        with tab1:
            if st.button("Fetch All Safes"):
                with st.spinner("Fetching safes..."):
                    safes = client.get_safes()
                    if safes:
                        st.dataframe(safes)
                    else:
                        st.info("No safes found or permission denied.")
                        
        with tab2:
            search_term = st.text_input("Search Accounts (optional)")
            if st.button("Fetch Accounts"):
                with st.spinner("Fetching accounts..."):
                    # Pass kwargs directly to get_accounts
                    accounts = client.get_accounts(search=search_term) if search_term else client.get_accounts()
                    if accounts:
                        st.dataframe(accounts)
                    else:
                        st.info("No accounts found.")

if __name__ == "__main__":
    main()
