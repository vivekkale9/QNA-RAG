"""
Document Models

Pydantic models for document upload, processing, and management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """Document processing status enumeration."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class DocumentType(str, Enum):
    """Supported document types."""
    PDF = "pdf"
    TXT = "txt"
    MD = "md"


class DocumentBase(BaseModel):
    """Base document model with common fields."""
    name: str = Field(..., description="Original filename")
    description: Optional[str] = Field(None, description="Document description")


class DocumentCreate(DocumentBase):
    """Model for document creation during upload."""
    file_size: int = Field(..., description="File size in bytes")
    file_type: DocumentType = Field(..., description="Document type")
    user_id: str = Field(..., description="Owner user ID")


class DocumentResponse(DocumentBase):
    """Model for document response."""
    id: str = Field(..., description="Document ID")
    file_size: int = Field(..., description="File size in bytes")
    file_type: DocumentType = Field(..., description="Document type")
    status: DocumentStatus = Field(..., description="Processing status")
    chunk_count: int = Field(default=0, description="Number of text chunks")
    query_count: int = Field(default=0, description="Number of queries against this document")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    user_id: str = Field(..., description="Owner user ID")
    file_path: str = Field(..., description="File storage path")

    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    """Model for updating document information."""
    name: Optional[str] = Field(None, description="Updated filename")
    description: Optional[str] = Field(None, description="Updated description")
    status: Optional[DocumentStatus] = Field(None, description="Updated status")


class ChunkResponse(BaseModel):
    """Model for document chunk information."""
    id: str = Field(..., description="Chunk ID")
    document_id: str = Field(..., description="Parent document ID")
    content: str = Field(..., description="Chunk text content")
    chunk_index: int = Field(..., description="Chunk position in document")
    page_number: Optional[int] = Field(None, description="Source page number")
    similarity_score: Optional[float] = Field(None, description="Similarity score for retrieval")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional chunk metadata")

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    """Model for file upload response."""
    success: bool = Field(..., description="Upload success status")
    message: str = Field(..., description="Status message")
    document: Optional[DocumentResponse] = Field(None, description="Created document information")
    processing_id: Optional[str] = Field(None, description="Background processing task ID")


class ProcessingStatus(BaseModel):
    """Model for processing status check."""
    document_id: str = Field(..., description="Document ID")
    status: DocumentStatus = Field(..., description="Current processing status")
    progress: int = Field(..., description="Processing progress percentage")
    chunks_processed: int = Field(default=0, description="Number of chunks processed")
    total_chunks: int = Field(default=0, description="Total number of chunks")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class DocumentSearchRequest(BaseModel):
    """Model for document search request."""
    query: str = Field(..., description="Search query")
    document_ids: Optional[List[str]] = Field(None, description="Specific document IDs to search")
    limit: int = Field(default=10, description="Maximum number of results")
    similarity_threshold: float = Field(default=0.7, description="Minimum similarity threshold")


class DocumentSearchResponse(BaseModel):
    """Model for document search response."""
    total_results: int = Field(..., description="Total number of matching chunks")
    chunks: List[ChunkResponse] = Field(..., description="Retrieved chunks")
    query_time: float = Field(..., description="Query execution time in seconds") 