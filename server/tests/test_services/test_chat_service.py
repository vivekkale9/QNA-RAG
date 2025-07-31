"""
Unit tests for ChatService.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.services.chat_service import ChatService
from app.models.chat import ChatRequest, ChatResponse, MessageRole
from app.db.postgres import User, UserRole, UserStatus
from app.db.mongodb import Conversation, Message


@pytest.mark.unit
@pytest.mark.chat
class TestChatService:
    """Test cases for ChatService."""

    async def test_process_chat_message_success(self, chat_service, async_db_session, mock_vector_store, test_user):
        """Test successful chat message processing."""
        chat_request = ChatRequest(
            message="What is this document about?",
            conversation_id=None,
            max_chunks=5
        )
        
        mock_conversation = Mock()
        mock_conversation.id = "conv_123"
        
        with patch.object(chat_service, '_get_user_by_id', return_value=test_user):
            with patch.object(chat_service, '_get_or_create_conversation', return_value=mock_conversation):
                with patch('app.db.mongodb.Message.save', new_callable=AsyncMock):
                    with patch.object(chat_service, '_generate_ai_response') as mock_generate:
                        mock_generate.return_value = {
                            "message": "This document is about testing.",
                            "model_used": "test-model"
                        }
                        
                        with patch('app.db.mongodb.Message.save', new_callable=AsyncMock):
                            result = await chat_service.process_chat_message(
                                chat_request, test_user.id, async_db_session, mock_vector_store
                            )
                            
                            assert isinstance(result, ChatResponse)
                            assert result.message == "This document is about testing."
                            assert result.conversation_id == "conv_123"
                            assert result.model_used == "test-model"

    async def test_process_chat_message_user_not_found(self, chat_service, async_db_session, mock_vector_store):
        """Test chat processing when user doesn't exist."""
        chat_request = ChatRequest(
            message="Test message",
            conversation_id=None
        )
        
        with patch.object(chat_service, '_get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await chat_service.process_chat_message(
                    chat_request, "nonexistent_user", async_db_session, mock_vector_store
                )
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "User not found" in exc_info.value.detail

    async def test_process_chat_message_with_existing_conversation(self, chat_service, async_db_session, mock_vector_store, test_user):
        """Test chat processing with existing conversation."""
        chat_request = ChatRequest(
            message="Follow-up question",
            conversation_id="existing_conv_123",
            max_chunks=3
        )
        
        mock_conversation = Mock()
        mock_conversation.id = "existing_conv_123"
        
        with patch.object(chat_service, '_get_user_by_id', return_value=test_user):
            with patch.object(chat_service, '_get_or_create_conversation', return_value=mock_conversation):
                with patch('app.db.mongodb.Message.save', new_callable=AsyncMock):
                    with patch.object(chat_service, '_generate_ai_response') as mock_generate:
                        mock_generate.return_value = {
                            "message": "This is a follow-up response.",
                            "model_used": "test-model"
                        }
                        
                        with patch('app.db.mongodb.Message.save', new_callable=AsyncMock):
                            result = await chat_service.process_chat_message(
                                chat_request, test_user.id, async_db_session, mock_vector_store
                            )
                            
                            assert result.conversation_id == "existing_conv_123"
                            assert result.message == "This is a follow-up response."

    async def test_process_chat_message_vector_search_error(self, chat_service, async_db_session, mock_vector_store, test_user):
        """Test handling of vector search errors."""
        chat_request = ChatRequest(
            message="Test message",
            conversation_id=None
        )
        
        mock_conversation = Mock()
        mock_conversation.id = "conv_123"
        
        # Mock vector store to raise an exception
        mock_vector_store.search_similar_chunks.side_effect = Exception("Vector search failed")
        
        with patch.object(chat_service, '_get_user_by_id', return_value=test_user):
            with patch.object(chat_service, '_get_or_create_conversation', return_value=mock_conversation):
                with patch('app.db.mongodb.Message.save', new_callable=AsyncMock):
                    with pytest.raises(HTTPException) as exc_info:
                        await chat_service.process_chat_message(
                            chat_request, test_user.id, async_db_session, mock_vector_store
                        )
                    
                    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    async def test_get_user_conversations_success(self, chat_service, async_db_session, test_user):
        """Test successful retrieval of user conversations."""
        mock_conversations = [
            Mock(id="conv_1", title="Conversation 1", created_at=datetime.now(timezone.utc)),
            Mock(id="conv_2", title="Conversation 2", created_at=datetime.now(timezone.utc))
        ]
        
        with patch.object(chat_service, '_get_user_by_id', return_value=test_user):
            with patch('app.db.mongodb.Conversation.find') as mock_find:
                mock_find.return_value.sort.return_value.skip.return_value.limit.return_value.to_list = AsyncMock(
                    return_value=mock_conversations
                )
                
                result = await chat_service.get_user_conversations(
                    test_user.id, async_db_session, skip=0, limit=10
                )
                
                assert len(result) == 2
                assert all(conv.id in ["conv_1", "conv_2"] for conv in result)

    async def test_get_user_conversations_user_not_found(self, chat_service, async_db_session):
        """Test conversation retrieval when user doesn't exist."""
        with patch.object(chat_service, '_get_user_by_id', return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await chat_service.get_user_conversations(
                    "nonexistent_user", async_db_session
                )
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_conversation_success(self, chat_service, async_db_session, test_user):
        """Test successful conversation retrieval."""
        mock_conversation = Mock()
        mock_conversation.id = "conv_123"
        mock_conversation.title = "Test Conversation"
        mock_conversation.user_id = test_user.id
        
        mock_messages = [
            Mock(role=MessageRole.USER, content="Hello", created_at=datetime.now(timezone.utc)),
            Mock(role=MessageRole.ASSISTANT, content="Hi there!", created_at=datetime.now(timezone.utc))
        ]
        
        with patch.object(chat_service, '_get_user_by_id', return_value=test_user):
            with patch('app.db.mongodb.Conversation.get') as mock_get_conv:
                mock_get_conv.return_value = mock_conversation
                with patch('app.db.mongodb.Message.find') as mock_find_messages:
                    mock_find_messages.return_value.sort.return_value.to_list = AsyncMock(
                        return_value=mock_messages
                    )
                    
                    result = await chat_service.get_conversation(
                        "conv_123", test_user.id, async_db_session
                    )
                    
                    assert result.id == "conv_123"
                    assert result.title == "Test Conversation"
                    assert len(result.messages) == 2

    async def test_get_conversation_not_found(self, chat_service, async_db_session, test_user):
        """Test conversation retrieval when conversation doesn't exist."""
        with patch.object(chat_service, '_get_user_by_id', return_value=test_user):
            with patch('app.db.mongodb.Conversation.get', return_value=None):
                with pytest.raises(HTTPException) as exc_info:
                    await chat_service.get_conversation(
                        "nonexistent_conv", test_user.id, async_db_session
                    )
                
                assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_conversation_access_denied(self, chat_service, async_db_session, test_user):
        """Test conversation retrieval when user doesn't own the conversation."""
        mock_conversation = Mock()
        mock_conversation.user_id = "other_user_id"
        
        with patch.object(chat_service, '_get_user_by_id', return_value=test_user):
            with patch('app.db.mongodb.Conversation.get', return_value=mock_conversation):
                with pytest.raises(HTTPException) as exc_info:
                    await chat_service.get_conversation(
                        "conv_123", test_user.id, async_db_session
                    )
                
                assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_conversation_success(self, chat_service, async_db_session, test_user):
        """Test successful conversation deletion."""
        mock_conversation = Mock()
        mock_conversation.id = "conv_123"
        mock_conversation.user_id = test_user.id
        
        with patch.object(chat_service, '_get_user_by_id', return_value=test_user):
            with patch('app.db.mongodb.Conversation.get', return_value=mock_conversation):
                with patch('app.db.mongodb.Message.find') as mock_find:
                    mock_find.return_value.delete_many = AsyncMock()
                    with patch.object(mock_conversation, 'delete', new_callable=AsyncMock):
                        result = await chat_service.delete_conversation(
                            "conv_123", test_user.id, async_db_session
                        )
                        
                        assert result["message"] == "Conversation deleted successfully"

    async def test_generate_ai_response_success(self, chat_service, mock_llm_manager):
        """Test successful AI response generation."""
        context_results = [
            {
                "content": "Test document content",
                "chunk_id": "chunk_1",
                "score": 0.95,
                "document_id": "doc_1",
                "metadata": {"page": 1}
            }
        ]
        
        chat_service.llm_manager = mock_llm_manager
        
        result = await chat_service._generate_ai_response(
            "What is this about?", context_results, []
        )
        
        assert "message" in result
        assert "model_used" in result
        mock_llm_manager.generate_response.assert_called_once()

    async def test_get_or_create_conversation_new(self, chat_service, test_user):
        """Test creating a new conversation."""
        with patch('app.db.mongodb.Conversation') as mock_conv_class:
            mock_conversation = Mock()
            mock_conversation.save = AsyncMock()
            mock_conv_class.return_value = mock_conversation
            
            result = await chat_service._get_or_create_conversation(None, test_user.id)
            
            assert result == mock_conversation
            mock_conversation.save.assert_called_once()

    async def test_get_or_create_conversation_existing(self, chat_service, test_user):
        """Test retrieving an existing conversation."""
        mock_conversation = Mock()
        mock_conversation.user_id = test_user.id
        
        with patch('app.db.mongodb.Conversation.get', return_value=mock_conversation):
            result = await chat_service._get_or_create_conversation("conv_123", test_user.id)
            
            assert result == mock_conversation

    async def test_get_or_create_conversation_access_denied(self, chat_service, test_user):
        """Test access denied when trying to access another user's conversation."""
        mock_conversation = Mock()
        mock_conversation.user_id = "other_user_id"
        
        with patch('app.db.mongodb.Conversation.get', return_value=mock_conversation):
            with pytest.raises(HTTPException) as exc_info:
                await chat_service._get_or_create_conversation("conv_123", test_user.id)
            
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN 