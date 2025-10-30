"""Main API client wrapper for Benchling API operations."""

import time
import logging
from typing import Dict, List, Optional, Any, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .config import get_config
from .auth import BenchlingAuth

# Set up logger
logger = logging.getLogger(__name__)


class BenchlingClient:
    """Main client for interacting with Benchling API."""
    
    def __init__(self):
        self.config = get_config()
        self.auth = BenchlingAuth()
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.config.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=frozenset(["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"]),
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        **kwargs
    ) -> requests.Response:
        """Internal method for making HTTP requests with common logic."""
        url = f"{self.config.benchling_base_url}{endpoint}"
        headers = self.auth.headers
        
        # Add timeout
        kwargs.setdefault("timeout", self.config.request_timeout)
        
        logger.debug(
            f"Making {method} request",
            url=url,
            method=method,
            params=params
        )
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                **kwargs
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(
                    "Rate limited, waiting before retry",
                    retry_after=retry_after
                )
                time.sleep(retry_after)
                return self._make_request(method, endpoint, data, params, **kwargs)
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Request failed: {method} {endpoint}",
                error=str(e),
                status_code=getattr(e.response, 'status_code', None)
            )
            raise
    
    def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        safe_mode: bool = False,
        error_message: str = "API request failed",
        **kwargs
    ) -> Union[requests.Response, bool]:
        """
        Public method for making custom HTTP requests to the Benchling API.
        
        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            endpoint: API endpoint (e.g., '/records', '/projects')
            data: Request body data (for POST, PUT, PATCH)
            params: Query parameters
            safe_mode: If True, returns boolean success/failure instead of raising exceptions
            error_message: Custom error message when safe_mode is True
            **kwargs: Additional arguments passed to requests
            
        Returns:
            If safe_mode=False: requests.Response (the HTTP response)
            If safe_mode=True: bool (True if successful, False otherwise)
            
        Example:
            # Standard API call
            response = client.make_request('GET', '/custom-endpoint', params={'filter': 'value'})
            data = response.json()
            
            # Safe API call that won't raise exceptions
            success = client.make_request('POST', '/update', data={'field': 'value'}, safe_mode=True)
            if success:
                print("Update successful")
            else:
                print("Update failed")
        """
        try:
            response = self._make_request(method, endpoint, data, params, **kwargs)
            if safe_mode:
                return True
            return response
        except Exception as e:
            logger.error(f"{error_message}. Reason: {e}")
            if safe_mode:
                return False
            raise
    
    def get_entities_by_schema(
        self, 
        schema_id: str, 
        endpoint: str, 
        response_key: str
    ) -> List[Dict]:
        """
        A generic function to retrieve all entities of a specific schema from a given endpoint.
        Handles pagination automatically to ensure all results are returned.

        Args:
            schema_id (str): The API ID of the schema to filter by.
            endpoint (str): The API endpoint to query (e.g., '/custom-entities').
            response_key (str): The key in the JSON response that contains the list of items.

        Returns:
            List[Dict]: A list of all found entity/container dictionaries.
        """
        logger.info(f"Fetching all entities with schema '{schema_id}' from endpoint '{endpoint}'...")
        params = {'schemaId': schema_id}
        entities = self.paginated_request(endpoint, params, response_key)
        logger.info(f"Successfully retrieved {len(entities)} total entities.")
        return entities
    
    def get_dropdown_options(self, schema_id: str, field_name: str) -> Dict[str, str]:
        """
        Fetches the options for a dropdown schema field in a two-step process.
        The Benchling API requires two calls: first to get the schema to find the
        dropdown's ID, and second to use that ID to get the dropdown's options.

        Args:
            client (BenchlingClient): An initialized client instance.
            schema_id (str): The API ID of the entity schema (e.g., 'ts_...').
            field_name (str): The exact name of the dropdown field.

        Returns:
            Dict[str, str]: A dictionary mapping the option name to the option's unique ID.
                            Example: {'Hyg': 'sfso_abc123', 'TK-Zeo': 'sfso_def456'}
        """
        logger.debug(f"Fetching dropdown options for field '{field_name}'...")
        try:
            # Step 1: Get the schema definition to find the dropdownId for the field
            schema_response = self.make_request('GET', f'/entity-schemas/{schema_id}')
            schema_details = schema_response.json()
            dropdown_id = None
            for field_def in schema_details.get('fieldDefinitions', []):
                if field_def.get('name') == field_name and field_def.get('type') == 'dropdown':
                    dropdown_id = field_def.get('dropdownId')
                    break
            if not dropdown_id:
                logger.error(f"Could not find a dropdown field named '{field_name}'.")
                return {}
            
            # Step 2: Use the dropdownId to get the actual options
            dropdown_response = self.make_request('GET', f'/dropdowns/{dropdown_id}')
            dropdown_details = dropdown_response.json()
            options = dropdown_details.get('options', [])
            return {opt['name']: opt['id'] for opt in options}
        except Exception as e:
            logger.error(f"Error fetching dropdown options: {e}")
            return {}

            
    def paginated_request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        response_key: str,
        page_size: int = 100
    ) -> List[Dict]:
        """
        Internal method to handle paginated API requests with automatic pagination.
        
        Args:
            endpoint: API endpoint to query
            params: Query parameters (pageSize will be added/overwritten)
            response_key: Key in response containing the list of items
            page_size: Number of items per page
            
        Returns:
            List of all items from all pages
        """
        all_items = []
        next_token = None
        
        while True:
            # Prepare parameters for this page
            page_params = params.copy()
            page_params['pageSize'] = page_size
            if next_token:
                page_params['nextToken'] = next_token
                
            try:
                response = self._make_request('GET', endpoint, params=page_params)
                data = response.json()
            except Exception as e:
                logger.error(f"Error during paginated request to {endpoint}: {e}")
                break
                
            items_on_page = data.get(response_key, [])
            if not items_on_page:
                break
                
            all_items.extend(items_on_page)
            next_token = data.get('nextToken')
            if not next_token:
                break
                
        return all_items
    
    def get_projects(self, pageSize: int = 50) -> List[Dict]:
        """Get projects from Benchling."""
        endpoint = "/projects"
        params = {"pageSize": pageSize}
        
        response = self._make_request("GET", endpoint, params=params)
        data = response.json()
        
        return data.get("projects", [])

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the API connection."""
        try:
            # Test authentication
            auth_valid = self.auth.validate_credentials()
            
            # Test basic API call
            projects = self.get_projects()
            
            return {
                "status": "healthy" if auth_valid and projects else "unhealthy",
                "authentication": "valid" if auth_valid else "invalid",
                "api_connection": "working" if projects else "failed",
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
