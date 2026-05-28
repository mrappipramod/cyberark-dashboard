import streamlit as st
import requests
import json

class CyberArkClient:
    def __init__(self):
        # Load secrets (must be set in Streamlit Cloud or local .streamlit/secrets.toml)
        self.url = st.secrets.get("CYBERARK_URL", "").rstrip('/')
        self.username = st.secrets.get("CYBERARK_USERNAME", "")
        self.password = st.secrets.get("CYBERARK_PASSWORD", "")
        self.session = None
        self.token = None

    def authenticate(self):
        """Authenticate and obtain a token – handles both JSON and plain string responses."""
        if not self.url or not self.username or not self.password:
            st.error("Missing CyberArk credentials in secrets.")
            return False

        auth_url = f"{self.url}/PasswordVault/api/auth/CyberArk/Logon"
        
        try:
            response = requests.post(
                auth_url,
                json={"username": self.username, "password": self.password},
                verify=False,          # For self‑signed certificates
                timeout=10
            )

            if response.status_code == 200:
                # Try to parse JSON
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        # Look for common token keys
                        self.token = data.get("CyberArkToken") or data.get("token") or data.get("access_token")
                    else:
                        # Response is a plain string – use it directly
                        self.token = data
                except json.JSONDecodeError:
                    # Not JSON – treat raw text as token (strip quotes if present)
                    self.token = response.text.strip('"')

                if not self.token:
                    st.error("Authentication succeeded but no token found in response.")
                    return False

                # Create session with token
                self.session = requests.Session()
                self.session.headers.update({
                    "Authorization": self.token,
                    "Content-Type": "application/json"
                })
                st.success("✅ Connected to CyberArk")
                return True
            else:
                st.error(f"Authentication failed (HTTP {response.status_code}): {response.text[:200]}")
                return False

        except requests.exceptions.Timeout:
            st.error("❌ Connection timed out. Is your CyberArk URL reachable from the internet?")
            return False
        except requests.exceptions.ConnectionError as e:
            st.error(f"❌ Cannot connect to {self.url}: {str(e)[:200]}")
            return False
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            return False

    def get_accounts(self, safe=None, limit=50, search=None):
        """Retrieve accounts from CyberArk and parse them into a clean list of dicts."""
        if not self.token and not self.authenticate():
            return []

        url = f"{self.url}/PasswordVault/api/Accounts"
        params = {"limit": limit}
        if safe:
            params["safe"] = safe
        if search:
            params["search"] = search

        try:
            resp = self.session.get(url, params=params, timeout=10, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                
                # If data is a list of strings that look like JSON (e.g., with trailing "\t12")
                if isinstance(data, list) and data and isinstance(data[0], str):
                    parsed = []
                    for item in data:
                        try:
                            # Remove trailing tab and number if present (e.g., '..."\t12')
                            cleaned = item.split('\t')[0] if '\t' in item else item
                            parsed.append(json.loads(cleaned))
                        except:
                            parsed.append(item)
                    return parsed
                
                # Normal case: list of dicts
                return data
            else:
                st.error(f"Failed to fetch accounts: HTTP {resp.status_code}")
                return []
        except Exception as e:
            st.error(f"Error fetching accounts: {str(e)}")
            return []

    def get_safes(self):
        """Retrieve all safes"""
        if not self.token and not self.authenticate():
            return []

        url = f"{self.url}/PasswordVault/api/Safes"
        try:
            resp = self.session.get(url, timeout=10, verify=False)
            if resp.status_code == 200:
                return resp.json()
            else:
                st.error(f"Failed to fetch safes: HTTP {resp.status_code}")
                return []
        except Exception as e:
            st.error(f"Error fetching safes: {str(e)}")
            return []
