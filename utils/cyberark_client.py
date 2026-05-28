import streamlit as st
import requests
from requests.auth import HTTPBasicAuth
import json

class CyberArkClient:
    def __init__(self):
        # Credentials from Streamlit secrets
        self.url = st.secrets["CYBERARK_URL"].rstrip('/')
        self.username = st.secrets["CYBERARK_USERNAME"]
        self.password = st.secrets["CYBERARK_PASSWORD"]
        self.session = None
        self.token = None

    def authenticate(self):
        """Authenticate and obtain a session token using CyberArk's REST API"""
        try:
            auth_url = f"{self.url}/PasswordVault/api/auth/CyberArk/Logon"
            response = requests.post(
                auth_url,
                json={
                    "username": self.username,
                    "password": self.password
                },
                verify=False  # Only for self-signed certs in your lab – remove in production!
            )
            if response.status_code == 200:
                self.token = response.json().get("CyberArkToken")
                self.session = requests.Session()
                self.session.headers.update({
                    "Authorization": self.token,
                    "Content-Type": "application/json"
                })
                return True
            else:
                st.error(f"Auth failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            st.error(f"Authentication error: {str(e)}")
            return False

    def get_accounts(self, safe=None, limit=50, search=None):
        """Retrieve accounts using CyberArk's GetAccounts API"""
        if not self.token and not self.authenticate():
            return []

        params = {
            "limit": limit,
            "search": search,
            "safe": safe
        }
        # Remove None parameters
        params = {k: v for k, v in params.items() if v is not None}

        url = f"{self.url}/PasswordVault/api/Accounts"
        try:
            resp = self.session.get(url, params=params, verify=False)
            if resp.status_code == 200:
                return resp.json()
            else:
                st.error(f"Failed to fetch accounts: {resp.status_code} - {resp.text}")
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
            resp = self.session.get(url, verify=False)
            if resp.status_code == 200:
                return resp.json()
            else:
                st.error(f"Failed to fetch safes: {resp.status_code} - {resp.text}")
                return []
        except Exception as e:
            st.error(f"Error fetching safes: {str(e)}")
            return []
