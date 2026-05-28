import streamlit as st
import requests
import json
import re

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
        except Exception as e:
            st.error(f"❌ Connection error: {str(e)}")
            return False

    def _parse_response(self, data):
        """
        Extracts and parses valid JSON maps from malformed responses, stream chunks,
        or raw text lines prefixed/suffixed with transit tracking indicators.
        """
        if isinstance(data, dict):
            return [data]
            
        # Convert any input list structures or raw streaming text into a uniform string
        if isinstance(data, list):
            if not data:
                return []
            if isinstance(data[0], dict):
                return data
            raw_string = "".join([str(item) for item in data])
        elif isinstance(data, str):
            raw_string = data
        else:
            return []

        parsed_items = []
        
        # Regex captures balanced brackets {} to safely extract complete objects
        # while stripping tracking numbers (e.g. 0{...}171{...}172)
        json_blocks = re.findall(r'\{[^{}]*\}', raw_string)
        
        for block in json_blocks:
            try:
                cleaned_block = block.strip()
                parsed_items.append(json.loads(cleaned_block))
            except (json.JSONDecodeError, ValueError):
                continue  # Skip any broken or partial JSON remnants
                
        return parsed_items

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
                # Fallback check if response content is plaintext chunking stream
                try:
                    data = resp.json()
                except json.JSONDecodeError:
                    data = resp.text

                with st.expander("🔍 Debug: Raw API Response (Accounts)", expanded=False):
                    if isinstance(data, dict):
                        st.json({k: data[k] for k in list(data.keys())[:3]})
                    else:
                        st.text(str(data)[:1000])

                if isinstance(data, dict) and "value" in data:
                    data = data["value"]

                return self._parse_response(data)
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
                try:
                    data = resp.json()
                except json.JSONDecodeError:
                    data = resp.text

                with st.expander("🔍 Debug: Raw API Response (Safes)", expanded=False):
                    if isinstance(data, dict):
                        st.json({k: data[k] for k in list(data.keys())[:3]})
                    else:
                        st.text(str(data)[:1000])

                if isinstance(data, dict) and "value" in data:
                    data = data["value"]

                return self._parse_response(data)
            else:
                st.error(f"Failed to fetch safes: HTTP {resp.status_code}")
                return []
        except Exception as e:
            st.error(f"Error fetching safes: {str(e)}")
            return []
