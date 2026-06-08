import requests

class CyberArkClient:
    def __init__(self, url=None, username=None, password=None):
        self.url = url
        self.username = username
        self.password = password
        self.token = None
        self.session = None

    def authenticate(self):
        # ... (Your existing standard authentication logic remains here) ...
        pass

    def get_accounts(self, safe=None, limit=50):
        # ... (Your existing get_accounts logic) ...
        pass

    def get_safes(self):
        # ... (Your existing get_safes logic) ...
        pass

    # =========================================================================
    # NEW: Privilege Cloud (PCloud) Service User Auth & Data Routines
    # =========================================================================
    
    def authenticate_pcloud(self, priv_cloud_url, identity_url, client_id, client_secret):
        """Authenticates to CyberArk Identity using OAuth2 Client Credentials for PCloud Service Users."""
        base_pcloud = priv_cloud_url.strip("/")
        base_identity = identity_url.strip("/")
        
   # CyberArk Identity OAuth2 Platform Token Endpoint for Privilege Cloud Shared Services
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
                
                # Build an isolated session for PCloud resource mapping
                self.session = requests.Session()
                self.session.headers.update({
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                })
                # Override base URL context to point to Privilege Cloud instead of PVWA
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
