import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import ssl
import certifi

class SecureAPIClient:
    def __init__(self, base_url):
        self.session = self._create_secure_session()
        self.base_url = base_url
        
    def _create_secure_session(self):
        session = requests.Session()
        # Configure retry strategy
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        # Use custom SSL context
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('https://', adapter)
        return session
    
    def fetch_patient_data(self, patient_id, auth_token):
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'X-API-Version': '1.0',
        }
        response = self.session.get(
            f'{self.base_url}/patients/{patient_id}',
            headers=headers,
            verify=True  # Verify SSL certificates
        )
        return response.json() 