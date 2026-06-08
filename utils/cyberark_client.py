import requests

class CyberArkClient:
    def __init__(self, url=None, username=None, password=None):
        """
        Constructor parameters default to None, allowing the class to be 
        instantiated without arguments for Privilege Cloud OAuth sessions.
        """
        self.url = url.strip("/") if url else None
        self.username = username
        self.password = password
        self.token = None
        self.session = None

    # =========================================================================
    # Standard Vault (PVWA) Authentication & Data Routines
    # =========================================================================
    def authenticate(self):
        """Standard CyberArk Authentication flow (PVWA)."""
        if not self.url or not self.username or not self.password:
            return False
            
        auth_url = f"{self.url}/PasswordVault/API/auth/Cyberark/Logon"
        payload = {
            "username": self.username,
            "password": self.password
        }
        
        try:
            # verify=False is used here assuming internal development environments
            response = requests.post(auth_url, json=payload, verify=False, timeout=15)
            if response.status_code == 200:
                # Direct string or JSON token payload handling depending on PVWA version
                self.token = response.json() if isinstance(response.json(), str) else response.json().get("LogonResult")
                self.session = requests.Session()
                self.session.headers.update({
                    "Authorization": self.token,
                    "Content-Type": "application/json"
                })
                return True
            return False
        except Exception:
            return False

    def get_accounts(self, safe=None, limit=50):
        """Fetches accounts from standard vault environment."""
        if not self.session:
            return None
        url = f"{self.url}/PasswordVault/api/Accounts"
        params = {"limit": limit}
        if safe:
            params["filter"] = f"safeName eq {safe}"
            
        try:
            response = self.session.get(url, params=params, verify=False, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get("value") if isinstance(data, dict) and "value" in data else data
            return None
        except Exception:
            return None

    def get_safes(self):
        """Fetches safes from standard vault environment."""
        if not self.session:
            return None
        url = f"{self.url}/PasswordVault/api/Safes"
        try:
            response = self.session.get(url, verify=False, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get("value") if isinstance(data, dict) and "value" in data else data
            return None
        except Exception:
            return None

    def get_safe_members(self, safe_name):
        """Fetches safe members from standard vault environment."""
        if not self.session:
            return None
        url = f"{self.url}/PasswordVault/api/Safes/{safe_name}/Members"
        try:
            response = self.session.get(url, verify=False, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get("value") if isinstance(data, dict) and "value" in data else data
            return None
        except Exception:
            return None

    # =========================================================================
    # Privilege Cloud (PCloud) Service User Auth & Data Routines
    # =========================================================================
    def authenticate_pcloud(self, priv_cloud_url, identity_url, client_id, client_secret):
        """Authenticates to CyberArk Identity using OAuth2 Client Credentials for PCloud Service Users."""
        base_pcloud = priv_cloud_url.strip("/")
        base_identity = identity_url.strip("/")
        
        # FIXED: Modified endpoint to match the psPAS implementation for Shared Services
        token_url = f"{base_identity}/oauth2/platformtoken"
        
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            response = requests.post(token_url, data=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token") or data.get("token")
                
                if not access_token:
                    return {"success": False, "error": "OAuth token missing from Identity response body."}
                
                # Configure the session wrapper for dynamic PCloud endpoints
                self.session = requests.Session()
                self.session.headers.update({
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                })
                self.url = base_pcloud
                return {"success": True, "token": access_token}
            else:
                return {"success": False, "error": f"HTTP {response.status_code} - {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_pcloud_safes(self):
        """Fetches all safes from the Privilege Cloud environment."""
        if not self.session:
            return None
        url = f"{self.url}/PasswordVault/api/Safes"
        try:
            response = self.session.get(url, verify=False, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get("value") if isinstance(data, dict) and "value" in data else data
            return None
        except Exception:
            return None

    def get_pcloud_safe_members(self, safe_name):
        """Fetches members and granular permissions for a given safe in PCloud."""
        if not self.session:
            return None
        url = f"{self.url}/PasswordVault/api/Safes/{safe_name}/Members"
        try:
            response = self.session.get(url, verify=False, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get("value") if isinstance(data, dict) and "value" in data else data
            return None
        except Exception:
            return None
