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
            st.error("Missing credentials in Secrets configuration.")
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
                # Handle variations in token response format
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
            return False
        except Exception as e:
            st.error(f"Authentication Error: {str(e)}")
            return False

    def generic_request(self, method, endpoint, payload=None, params=None):
        """
        The Ultimate Integration Engine.
        Executes any CyberArk REST API path, mapping directly to your psPAS features.
        """
        if not self.token and not self.authenticate():
            return None, "Authentication failure"

        # Standardize endpoint path structure
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

    # Maintain your original explicit hooks for safety 
    def get_safes(self):
        data, err = self.generic_request("GET", "PasswordVault/api/Safes")
        if data:
            return data.get("value", data) if isinstance(data, dict) else data
        return []
