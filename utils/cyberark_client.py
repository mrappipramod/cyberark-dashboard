import streamlit as st
import requests
import json

class CyberArkClient:
    def __init__(self):
        self.url = st.secrets.get("CYBERARK_URL", "").rstrip('/')
        self.username = st.secrets.get("CYBERARK_USERNAME", "")
        self.password = st.secrets.get("CYBERARK_PASSWORD", "")
        self.session = None
        self.token = None

    def authenticate(self):
        if not self.url or not self.username or not self.password:
            st.error("Missing CyberArk credentials in secrets.")
            return False

        auth_url = f"{self.url}/PasswordVault/api/auth/CyberArk/Logon"
        try:
            response = requests.post(
                auth_url,
                json={"username": self.username, "password": self.password},
                verify=False,
                timeout=10
            )
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        self.token = data.get("CyberArkToken") or data.get("token") or data.get("access_token")
                    else:
                        self.token = data
                except json.JSONDecodeError:
                    self.token = response.text.strip('"')

                if not self.token:
                    st.error("Authentication succeeded but no token found.")
                    return False

                self.session = requests.Session()
                self.session.headers.update({
                    "Authorization": self.token,
                    "Content-Type": "application/json"
                })
                st.success("✅ Connected to CyberArk")
                return True
            else:
                st.error(f"Auth failed (HTTP {response.status_code}): {response.text[:200]}")
                return False
        except requests.exceptions.Timeout:
            st.error("❌ Connection timed out. Is your CyberArk URL reachable?")
            return False
        except Exception as e:
            st.error(f"❌ Connection error: {str(e)}")
            return False

    def get_accounts(self, safe=None, limit=50, search=None):
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

                # --- Handle different response shapes ---
                # Case 1: {"value": [...]}   (most common)
                if isinstance(data, dict) and "value" in data:
                    data = data["value"]
                # Case 2: list of JSON strings with trailing tab (e.g., '{...}\t12')
                if isinstance(data, list) and data and isinstance(data[0], str):
                    parsed = []
                    for item in data:
                        try:
                            cleaned = item.split('\t')[0] if '\t' in item else item
                            parsed.append(json.loads(cleaned))
                        except:
                            parsed.append(item)
                    return parsed
                # Case 3: normal list of dicts
                return data if isinstance(data, list) else []
            else:
                st.error(f"Failed to fetch accounts: HTTP {resp.status_code}")
                return []
        except Exception as e:
            st.error(f"Error fetching accounts: {str(e)}")
            return []

    def get_safes(self):
        if not self.token and not self.authenticate():
            return []

        url = f"{self.url}/PasswordVault/api/Safes"
        try:
            resp = self.session.get(url, timeout=10, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and "value" in data:
                    data = data["value"]
                return data if isinstance(data, list) else []
            else:
                st.error(f"Failed to fetch safes: HTTP {resp.status_code}")
                return []
        except Exception as e:
            st.error(f"Error fetching safes: {str(e)}")
            return []
