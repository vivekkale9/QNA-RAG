from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from beanie import Document as BeanieDocument, init_beanie
from pydantic import Field
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING

from ..config import get_settings

settings = get_settings()

mongodb_client: Optional[AsyncIOMotorClient] = None


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, Enum):
    PDF = "pdf"
    TXT = "txt"
    MD = "md"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Document(BeanieDocument):
    
    # Document identification
    filename: str
    original_filename: str
    file_path: str
    file_type: DocumentType
    file_size: int
    
    # Processing information
    status: DocumentStatus = DocumentStatus.PENDING
    processing_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    # Content information
    total_chunks: int = 0
    text_content: Optional[str] = None
    summary: Optional[str] = None
    
    # User association
    user_id: str  # Reference to PostgreSQL User.id
    
    # Timestamps
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "documents"
        indexes = [
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("file_type", ASCENDING)]),
            IndexModel([("uploaded_at", DESCENDING)]),
            IndexModel([("filename", ASCENDING)]),
        ]


class Chunk(BeanieDocument):
    
    # Content
    content: str
    embedding_id: Optional[str] = None  # Reference to vector store
    
    # Position information
    page_number: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    chunk_index: int
    
    # Metadata
    chunk_metadata: Optional[Dict[str, Any]] = None
    
    # Document reference
    document_id: str  # Reference to Document._id
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "chunks"
        indexes = [
            IndexModel([("document_id", ASCENDING)]),
            IndexModel([("chunk_index", ASCENDING)]),
            IndexModel([("embedding_id", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]


class Conversation(BeanieDocument):
    
    # Conversation details
    title: str
    summary: Optional[str] = None
    conversation_metadata: Optional[Dict[str, Any]] = None
    
    # User association
    user_id: str  # Reference to PostgreSQL User.id
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "conversations"
        indexes = [
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("updated_at", DESCENDING)]),
        ]


class Message(BeanieDocument):
    
    # Message content
    role: MessageRole
    content: str
    sources: Optional[List[Dict[str, Any]]] = None  # Source chunks/documents
    message_metadata: Optional[Dict[str, Any]] = None
    
    # Conversation reference
    conversation_id: str  # Reference to Conversation._id
    
    # User association
    user_id: str  # Reference to PostgreSQL User.id
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "messages"
        indexes = [
            IndexModel([("conversation_id", ASCENDING)]),
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("role", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ]


class QueryLog(BeanieDocument):
    
    # Query details
    query: str
    response: str
    conversation_id: Optional[str] = None  # Reference to Conversation._id
    
    # Performance metrics
    response_time: Optional[float] = None  # in seconds
    chunk_count: Optional[int] = None
    llm_provider: Optional[str] = None
    model_used: Optional[str] = None
    
    # Additional metadata
    query_metadata: Optional[Dict[str, Any]] = None
    
    # User association
    user_id: str  # Reference to PostgreSQL User.id
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "query_logs"
        indexes = [
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("conversation_id", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("response_time", ASCENDING)]),
            IndexModel([("llm_provider", ASCENDING)]),
        ]


# Database connection management
async def connect_to_mongodb():
    global mongodb_client
    mongodb_client = AsyncIOMotorClient(settings.mongo_url)


async def disconnect_from_mongodb():
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()


async def get_mongodb_database():
    global mongodb_client
    if not mongodb_client:
        await connect_to_mongodb()
    return mongodb_client[settings.mongo_db]


async def init_mongodb_db():
    global mongodb_client
    
    if not mongodb_client:
        await connect_to_mongodb()
    
    # Get database
    database = mongodb_client[settings.mongo_db]
    
    # Initialize Beanie with document models
    await init_beanie(
        database=database,
        document_models=[
            Document,
            Chunk,
            Conversation,
            Message,
            QueryLog
        ]
    )
    
    print("✅ MongoDB initialized with Beanie ODM") 