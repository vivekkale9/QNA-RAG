"""
Pytest configuration and fixtures for the test suite.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import AsyncGenerator, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient
import mongomock_motor

from main import app
from app.config import Settings, get_settings
from app.db.postgres import Base, User, UserRole, UserStatus
from app.db.mongodb import Document, Chunk, Conversation, Message, MessageRole
from app.db.milvus_vector_store import MilvusVectorStore
from app.services import AuthService, ChatService, DocumentService, UserSerivce
from app.utils.auth import create_access_token


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Settings()
    settings.environment = "test"
    settings.secret_key = "test-secret-key"
    settings.postgres_url = "sqlite+aiosqlite:///:memory:"
    settings.mongo_db = "test_db"
    return settings


@pytest.fixture
async def async_db_engine(mock_settings):
    """Create test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def async_db_session(async_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        async_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture
def mock_mongodb():
    """Mock MongoDB client and database."""
    client = mongomock_motor.AsyncMongoMockClient()
    db = client.test_db
    return db


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    mock_store = AsyncMock(spec=MilvusVectorStore)
    mock_store.search_similar_chunks.return_value = [
        {
            "chunk_id": "test_chunk_1",
            "content": "Test chunk content",
            "score": 0.95,
            "document_id": "test_doc_1",
            "metadata": {"page": 1}
        }
    ]
    mock_store.add_chunk_vectors.return_value = True
    mock_store.delete_document_vectors.return_value = True
    return mock_store


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "id": "test_user_123",
        "email": "test@example.com",
        "password": "testpassword123",
        "role": UserRole.USER,
        "status": UserStatus.ACTIVE,
        "created_at": datetime.now(timezone.utc)
    }


@pytest.fixture
async def test_user(async_db_session, test_user_data):
    """Create test user in database."""
    from app.utils.auth import hash_password
    
    user = User(
        id=test_user_data["id"],
        email=test_user_data["email"],
        password_hash=hash_password(test_user_data["password"]),
        role=test_user_data["role"],
        status=test_user_data["status"],
        created_at=test_user_data["created_at"]
    )
    
    async_db_session.add(user)
    await async_db_session.commit()
    await async_db_session.refresh(user)
    
    return user


@pytest.fixture
def test_access_token(test_user_data, mock_settings):
    """Create test access token."""
    return create_access_token(
        data={"sub": test_user_data["id"]},
        secret_key=mock_settings.secret_key
    )


@pytest.fixture
def auth_headers(test_access_token):
    """Authorization headers for API tests."""
    return {"Authorization": f"Bearer {test_access_token}"}


@pytest.fixture
def test_document_data():
    """Test document data."""
    return {
        "id": "test_doc_123",
        "name": "test_document.pdf",
        "file_size": 1024,
        "file_type": "pdf",
        "user_id": "test_user_123",
        "file_path": "/tmp/test_document.pdf",
        "status": "completed",
        "uploaded_at": datetime.now(timezone.utc),
        "processed_at": datetime.now(timezone.utc)
    }


@pytest.fixture
def test_conversation_data():
    """Test conversation data."""
    return {
        "id": "test_conv_123",
        "user_id": "test_user_123",
        "title": "Test Conversation",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }


@pytest.fixture
def test_message_data():
    """Test message data."""
    return {
        "id": "test_msg_123",
        "conversation_id": "test_conv_123",
        "role": MessageRole.USER,
        "content": "What is this document about?",
        "user_id": "test_user_123",
        "created_at": datetime.now(timezone.utc)
    }


@pytest.fixture
def auth_service(mock_settings):
    """Auth service instance."""
    with pytest.MonkeyPatch().context() as m:
        m.setattr("app.config.get_settings", lambda: mock_settings)
        return AuthService()


@pytest.fixture
def user_service():
    """User service instance."""
    return UserSerivce()


@pytest.fixture
def chat_service():
    """Chat service instance."""
    return ChatService()


@pytest.fixture
def document_service():
    """Document service instance."""
    service = DocumentService()
    service.processor = Mock()
    return service


@pytest.fixture
async def async_client():
    """Async HTTP client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def client():
    """Sync HTTP client for API testing."""
    return TestClient(app)


@pytest.fixture
def mock_llm_manager():
    """Mock LLM manager."""
    mock_manager = Mock()
    mock_manager.generate_response.return_value = {
        "message": "This is a test response from the AI.",
        "model_used": "test-model"
    }
    return mock_manager


@pytest.fixture
def sample_file_content():
    """Sample file content for upload tests."""
    return b"This is a sample PDF content for testing purposes."


@pytest.fixture
def mock_file_upload():
    """Mock file upload object."""
    from fastapi import UploadFile
    from io import BytesIO
    
    file_content = b"This is a test file content"
    file_obj = BytesIO(file_content)
    
    mock_file = UploadFile(
        filename="test.pdf",
        file=file_obj,
        size=len(file_content),
        headers={"content-type": "application/pdf"}
    )
    
    return mock_file


@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch, mock_settings, mock_vector_store, mock_mongodb):
    """Auto-used fixture to mock external dependencies."""
    monkeypatch.setattr("app.config.get_settings", lambda: mock_settings)
    monkeypatch.setattr("app.main.vector_store_manager", mock_vector_store)
    
    # Mock database connections
    async def mock_get_postgres_db():
        return None
    
    async def mock_get_mongodb_db():
        return mock_mongodb
    
    monkeypatch.setattr("app.db.postgres.get_postgres_database", mock_get_postgres_db)
    monkeypatch.setattr("app.db.mongodb.get_mongodb_database", mock_get_mongodb_db)


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close() 