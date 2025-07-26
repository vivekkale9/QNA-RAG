from enum import Enum
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, String, Index, JSON
from sqlalchemy.dialects.postgresql import TIMESTAMP
from databases import Database

from ..config import get_settings

settings = get_settings()

# Create async engine
async_engine = create_async_engine(
    settings.postgres_url,
    echo=settings.debug,
    future=True
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

postgres_database = Database(settings.postgres_url)

# SQLAlchemy Base
Base = declarative_base()

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"

class User(Base):
    __tablename__ = "User"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # User status and role
    role = Column(String(50), default=UserRole.USER.value, nullable=False)
    status = Column(String(50), default=UserStatus.ACTIVE.value, nullable=False)
    
    # LLM Configuration (tenant-specific)
    llm_provider = Column(String(50), nullable=True)  # groq, openai, etc.
    llm_config = Column(JSON, nullable=True)  # Custom LLM settings

    created_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_status', 'status'),
        Index('idx_user_role', 'role'),
        Index('idx_user_created', 'created_at'),
    )

async def get_postgres_database() -> AsyncSession:
    """
    Dependency to get PostgreSQL database session.
    
    Yields:
        AsyncSession: PostgreSQL database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_postgres_db():
    """Initialize PostgreSQL database tables and default data."""
    async with async_engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

async def connect_to_postgres():
    """Connect to PostgreSQL database."""
    await postgres_database.connect()

async def disconnect_from_postgres():
    """Disconnect from PostgreSQL database."""
    await postgres_database.disconnect()