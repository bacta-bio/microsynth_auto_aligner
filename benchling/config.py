"""Configuration management for Benchling API using dotenv."""

import os
from typing import Optional
from dotenv import load_dotenv


class BenchlingConfig:
    """Configuration class for Benchling API settings."""
    
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Benchling API URLs
        self.benchling_base_url: str = os.getenv(
            'BENCHLING_BASE_URL', 
            'https://api.benchling.com/v2'
        )
        self.benchling_token_url: str = os.getenv(
            'BENCHLING_TOKEN_URL', 
            'https://api.benchling.com/v2/token'
        )
        
        # OAuth2 Credentials
        self.benchling_client_id: Optional[str] = os.getenv('BENCHLING_CLIENT_ID')
        self.benchling_client_secret: Optional[str] = os.getenv('BENCHLING_CLIENT_SECRET')
        
        # Request Configuration
        self.request_timeout: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
        self.max_retries: int = int(os.getenv('MAX_RETRIES', '3'))
        
        # Validate required settings
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate that required configuration is present."""
        if not self.benchling_client_id:
            raise ValueError("BENCHLING_CLIENT_ID environment variable is required")
        if not self.benchling_client_secret:
            raise ValueError("BENCHLING_CLIENT_SECRET environment variable is required")
    
    def get_auth_info(self) -> dict:
        """Get authentication configuration info (without secrets)."""
        return {
            "base_url": self.benchling_base_url,
            "token_url": self.benchling_token_url,
            "has_client_id": bool(self.benchling_client_id),
            "has_client_secret": bool(self.benchling_client_secret),
            "request_timeout": self.request_timeout,
            "max_retries": self.max_retries
        }


# Global config instance
_config_instance: Optional[BenchlingConfig] = None


def get_config() -> BenchlingConfig:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = BenchlingConfig()
    return _config_instance


def reload_config() -> BenchlingConfig:
    """Reload the configuration from environment variables."""
    global _config_instance
    _config_instance = BenchlingConfig()
    return _config_instance
