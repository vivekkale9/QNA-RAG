"""
Application Configuration

Centralized configuration management using Pydantic Settings.
Loads configuration from environment variables or .env file.
"""

import os
from pydantic import BaseModel
from typing import Optional, List
from dotenv import load_dotenv
from functools import lru_cache

class Settings(BaseModel):

    load_dotenv()

    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "development")

    # PostgresSQL
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_user: str = os.getenv("POSTGRES_USER", "docuchat")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")
    postgres_db: str = os.getenv("POSTGRES_DB", "docuchat")

    @property
    def postgres_url(self) -> str:
        """PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    mongo_host: str = os.getenv("MONGO_HOST", "localhost")
    mongo_user: str = os.getenv("MONGO_USER", "")
    mongo_password: str = os.getenv("MONGO_PASSWORD", "")
    mongo_db: str = os.getenv("MONGO_DB", "docuchat")

    @property
    def mongo_url(self) -> str:
        """MongoDB connection URL."""
        if self.mongo_user and self.mongo_password:
            return f"mongodb+srv://{self.mongo_user}:{self.mongo_password}@{self.mongo_host}/{self.mongo_db}"

    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    secret_key: str = os.getenv("SECRET_KEY", "")

    #Milvus/Zilliz Cloud Configuration
    milvus_host: str = os.getenv("MILVUS_HOST", "")
    milvus_port: int = int(os.getenv("MILVUS_PORT", "19530"))
    milvus_token: str = os.getenv("MILVUS_TOKEN", "")  # For Zilliz Cloud authentication
    milvus_collection_name: str = os.getenv("MILVUS_COLLECTION_NAME", "insurance_chunks")
    milvus_index_type: str = os.getenv("MILVUS_INDEX_TYPE", "AUTOINDEX")  # Better for Zilliz Cloud
    milvus_metric_type: str = os.getenv("MILVUS_METRIC_TYPE", "COSINE")
    milvus_nlist: int = int(os.getenv("MILVUS_NLIST", "128"))
    
    @property
    def is_zilliz_cloud(self) -> bool:
        return bool(self.milvus_token and self.milvus_host)

    # Embedding Configuration
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))

    #Chunking Configuration
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "300"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # Individual Groq API keys for round-robin load balancing
    groq_api_key_1: str = os.getenv("GROQ_API_KEY_1", "")
    groq_api_key_2: str = os.getenv("GROQ_API_KEY_2", "")
    groq_api_key_3: str = os.getenv("GROQ_API_KEY_3", "")
    groq_api_key_4: str = os.getenv("GROQ_API_KEY_4", "")
    groq_api_key_5: str = os.getenv("GROQ_API_KEY_5", "")
    groq_api_key_6: str = os.getenv("GROQ_API_KEY_6", "")
    groq_model: str = os.getenv("GROQ_MODEL", "")
    groq_base_url: str = os.getenv("GROQ_BASE_URL", "")
    groq_max_tokens: int = int(os.getenv("GROQ_MAX_TOKENS", ""))
    groq_rate_limit_rpm: int = int(os.getenv("GROQ_RATE_LIMIT_RPM", ""))
    groq_rate_limit_tpm: int = int(os.getenv("GROQ_RATE_LIMIT_TPM", ""))
    
    # Tenant Configuration
    enable_tenant_llm_config: bool = os.getenv("ENABLE_TENANT_LLM_CONFIG", "true").lower() == "true"
    enable_tenant_api_keys: bool = os.getenv("ENABLE_TENANT_API_KEYS", "true").lower() == "true"

    @property
    def groq_api_keys(self) -> List[str]:
        keys = [
            self.groq_api_key_1,
            self.groq_api_key_2,
            self.groq_api_key_3,
            self.groq_api_key_4,
            self.groq_api_key_5,
            self.groq_api_key_6,
        ]
        # Filter out default values
        return [key for key in keys if key and not key.startswith("your-groq-api-key")]
    


def get_tenant_llm_config(tenant_id: Optional[str] = None) -> dict:
    """
    Get LLM configuration for a specific tenant.
    
    Args:
        tenant_id: Optional tenant identifier (user_id)
        
    Returns:
        dict: LLM configuration for the tenant
    """
    settings = get_settings()
    
    # Default configuration (fallback)
    default_config = {
        "default_provider": "groq",
        "groq": {
            "api_keys": settings.groq_api_keys,
            "model": settings.groq_model,
            "base_url": settings.groq_base_url,
            "max_tokens": settings.groq_max_tokens,
            "rate_limit_rpm": settings.groq_rate_limit_rpm,
            "rate_limit_tpm": settings.groq_rate_limit_tpm,
        }
    }
    
    # If no tenant_id provided or tenant configuration disabled, return default
    if not tenant_id or not settings.enable_tenant_llm_config:
        return default_config
    
    try:
        # Import here to avoid circular imports
        from .db.postgres import User, AsyncSessionLocal
        from sqlalchemy import select
        import asyncio
        
        async def get_user_llm_config():
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.id == tenant_id))
                user = result.scalar_one_or_none()
                
                if not user:
                    return default_config
                
                # If user has custom LLM configuration
                if user.llm_provider and user.llm_config:
                    custom_config = default_config.copy()
                    
                    # Override provider if specified
                    if user.llm_provider in ["groq"]:
                        custom_config["default_provider"] = user.llm_provider
                    
                    # Merge user's custom LLM config
                    if isinstance(user.llm_config, dict):
                        # Override specific provider settings
                        if user.llm_provider in custom_config:
                            custom_config[user.llm_provider].update(user.llm_config)
                        else:
                            # Add new provider config
                            custom_config[user.llm_provider] = user.llm_config
                    
                    return custom_config
                
                return default_config
        
        # Run async function
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(get_user_llm_config())
        except RuntimeError:
            # If no event loop is running, create a new one
            return asyncio.run(get_user_llm_config())
            
    except Exception as e:
        # If any error occurs, fall back to default config
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to get tenant LLM config for {tenant_id}: {e}")
        return default_config


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings() 