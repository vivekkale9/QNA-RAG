"""
Chat Models

Pydantic models for chat functionality, LLM interactions, and conversation management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Chat message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class LLMProvider(str, Enum):
    """Available LLM providers."""
    OLLAMA = "ollama"
    GROQ = "groq"
    OPENAI = "openai"


class ChatRequest(BaseModel):
    """Model for chat request."""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    document_ids: Optional[List[int]] = Field(None, description="Specific document IDs to query")
    max_chunks: int = Field(default=5, description="Maximum number of context chunks")
    max_sources: int = Field(default=5, description="Max sources to return")
    temperature: float = Field(default=0.7, description="LLM temperature for response generation")
    stream: bool = Field(default=False, description="Enable streaming response")
    include_sources: bool = Field(default=True, description="Include source documents in response")


class SourceResponse(BaseModel):
    """Model for source document information in chat response."""
    document_id: str = Field(..., description="Source document ID")
    document_name: str = Field(..., description="Source document name")
    chunk_id: str = Field(..., description="Source chunk ID")
    page_number: Optional[int] = Field(None, description="Source page number")
    content: str = Field(..., description="Relevant text snippet")
    similarity_score: float = Field(..., description="Similarity score")
    start_char: Optional[int] = Field(None, description="Start character position in document")
    end_char: Optional[int] = Field(None, description="End character position in document")


class MessageResponse(BaseModel):
    """Model for individual chat message."""
    id: int = Field(..., description="Message ID")
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    sources: List[SourceResponse] = Field(default_factory=list, description="Source documents")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional message metadata")

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Model for chat response."""
    message: str = Field(..., description="Assistant response message")
    sources: List[SourceResponse] = Field(default_factory=list, description="Source documents")
    conversation_id: str = Field(..., description="Conversation ID")
    message_id: str = Field(..., description="Message ID")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    model_used: str = Field(..., description="Model used for generation")


class ConversationResponse(BaseModel):
    """Model for conversation history."""
    id: str = Field(..., description="Conversation ID")
    user_id: int = Field(..., description="User ID")
    title: str = Field(..., description="Conversation title")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    message_count: int = Field(..., description="Number of messages")
    messages: List[MessageResponse] = Field(default_factory=list, description="Conversation messages")

    class Config:
        from_attributes = True


class StreamingResponse(BaseModel):
    """Model for streaming chat response chunks."""
    conversation_id: str = Field(..., description="Conversation ID")
    message_id: int = Field(..., description="Message ID")
    content_delta: str = Field(..., description="Incremental content chunk")
    is_final: bool = Field(default=False, description="Whether this is the final chunk")
    sources: Optional[List[SourceResponse]] = Field(None, description="Sources (only in final chunk)")


class ConversationCreate(BaseModel):
    """Model for creating a new conversation."""
    title: Optional[str] = Field(None, description="Conversation title")
    user_id: int = Field(..., description="User ID")


class ConversationUpdate(BaseModel):
    """Model for updating conversation information."""
    title: Optional[str] = Field(None, description="Updated conversation title")


class FeedbackRequest(BaseModel):
    """Model for message feedback."""
    message_id: int = Field(..., description="Message ID")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback_text: Optional[str] = Field(None, description="Optional feedback text")


class ChatStats(BaseModel):
    """Model for chat statistics."""
    total_conversations: int = Field(..., description="Total number of conversations")
    total_messages: int = Field(..., description="Total number of messages")
    avg_response_time: float = Field(..., description="Average response time in seconds")
    popular_topics: List[str] = Field(default_factory=list, description="Most queried topics")
    user_satisfaction: float = Field(..., description="Average user rating") 