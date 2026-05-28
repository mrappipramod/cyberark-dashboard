import streamlit as st
import requests

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
            resp = requests.post(
                auth_url,
                json={"username": self.username, "password": self.password},
                verify=False,
                timeout=10
            )
            if resp.status_code == 200:
                self.token = resp.json().get("CyberArkToken")
                self.session = requests.Session()
                self.session.headers.update({"Authorization": self.token, "Content-Type": "application/json"})
                return True
            else:
                st.error(f"Auth error {resp.status_code}: {resp.text[:200]}")
                return False
        except requests.exceptions.Timeout:
            st.error("Connection timeout. Is your CyberArk URL publicly accessible?")
            return False
        except Exception as e:
            st.error(f"Connection failed: {e}")
            return False

    def get_accounts(self, safe=None, limit=50):
        if not self.token and not self.authenticate():
            return []
        url = f"{self.url}/PasswordVault/api/Accounts"
        params = {"limit": limit}
        if safe:
            params["safe"] = safe
        try:
            resp = self.session.get(url, params=params, timeout=10, verify=False)
            if resp.status_code == 200:
                return resp.json()
            else:
                st.error(f"Failed accounts: {resp.status_code}")
                return []
        except Exception as e:
            st.error(f"Error: {e}")
            return []
