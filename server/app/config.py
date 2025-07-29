"""
Application Configuration

Centralized configuration management using Pydantic Settings.
Loads configuration from environment variables or .env file.
"""

import os
from pydantic import BaseModel
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

    #Milvus
    milvus_host: str = os.getenv("MILVUS_HOST", "localhost")
    milvus_port: int = int(os.getenv("MILVUS_PORT", "19530"))
    milvus_collection_name: str = os.getenv("MILVUS_COLLECTION_NAME", "insurance_chunks")
    milvus_index_type: str = os.getenv("MILVUS_INDEX_TYPE", "IVF_FLAT")
    milvus_metric_type: str = os.getenv("MILVUS_METRIC_TYPE", "COSINE")
    milvus_nlist: int = int(os.getenv("MILVUS_NLIST", "128"))

    # Embedding Configuration
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))

    #Chunking Configuration
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "300"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "50"))


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings() 