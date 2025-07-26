"""
Application Configuration

Centralized configuration management using Pydantic Settings.
Loads configuration from environment variables or .env file.
"""

import os
from pydantic import BaseModel
from functools import lru_cache

class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    environment: str = os.getenv("ENVIRONMENT", "development")

@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings() 