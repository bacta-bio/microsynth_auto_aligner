"""Authentication handling for Benchling API."""

import time
import logging
from typing import Dict, Optional
import requests
from .config import get_config

# Set up logger
logger = logging.getLogger(__name__)


class BenchlingAuth:
    """Handles OAuth2 Client Credentials authentication for Benchling Apps."""
    
    def __init__(self):
        self.config = get_config()
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._headers: Optional[Dict[str, str]] = None
        
        # Safety margin to refresh before actual expiry (in seconds)
        self._refresh_margin = 60
    
    def _token_is_valid(self) -> bool:
        return self._access_token is not None and time.time() < (self._token_expires_at - self._refresh_margin)
    
    def _fetch_token(self) -> None:
        """Fetch a new access token using client credentials."""
        try:
            data = {
                "grant_type": "client_credentials"
            }
            auth = (self.config.benchling_client_id, self.config.benchling_client_secret)
            
            resp = requests.post(
                self.config.benchling_token_url,
                data=data,
                auth=auth,
                timeout=self.config.request_timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            access_token = payload.get("access_token")
            expires_in = payload.get("expires_in", 3600)
            
            if not access_token:
                raise RuntimeError("No access_token in token response")
            
            self._access_token = access_token
            self._token_expires_at = time.time() + int(expires_in)
            logger.info("Fetched new OAuth access token")
        except requests.RequestException as e:
            logger.error("Failed to fetch OAuth token")
            logger.error(e)
            raise
    
    def _ensure_token(self) -> None:
        if not self._token_is_valid():
            self._fetch_token()
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get Authorization headers for API requests."""
        self._ensure_token()
        self._headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        return self._headers
    
    def validate_credentials(self) -> bool:
        """Validate OAuth credentials by fetching a token and making a small API call."""
        try:
            self._fetch_token()
            # Make a simple API call to validate connection (projects)
            test_url = f"{self.config.benchling_base_url}/projects"
            response = requests.get(
                test_url,
                headers=self.headers,
                timeout=self.config.request_timeout
            )
            if response.status_code in (200, 204):
                logger.info("OAuth credentials validated successfully")
                return True
            else:
                logger.error("Credential validation failed")
                logger.error(response.status_code)
                return False
        except Exception as e:
            logger.error("Failed to validate credentials")
            logger.error(e)
            return False
    
    def get_auth_info(self) -> Dict[str, str]:
        """Get authentication information for debugging."""
        return {
            "base_url": self.config.benchling_base_url,
            "token_url": self.config.benchling_token_url,
            "has_token": bool(self._access_token),
        }
    
    def refresh_auth(self) -> None:
        """Force refresh of the access token."""
        self._access_token = None
        self._token_expires_at = 0.0
        self._headers = None
        logger.info("Access token invalidated; will refresh on next request")
