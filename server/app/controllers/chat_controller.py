"""
Chat Controller

Handles chat-related request processing and coordinates
between routes and services.
"""

from typing import List, Optional
from fastapi import HTTPException, status
import logging

from ..services import ChatService
from ..models import ChatRequest, ChatResponse, ConversationResponse
from ..dependencies import get_vector_store


class ChatController:
    
    def __init__(self):
        self.chat_service = ChatService()
    
    async def send_message(
        self, 
        chat_request: ChatRequest, 
        user_id: str, 
        db_session
    ) -> ChatResponse:
        """
        Handle chat message.
        
        Args:
            chat_request: Chat request data
            user_id: Current user ID
            db_session: Database session
            
        Returns:
            ChatResponse: Chat response with answer and sources
        """
        # Get vector store with lazy initialization
        vector_manager = await get_vector_store()
        
        try:
            response = await self.chat_service.process_chat_message(
                chat_request=chat_request,
                user_id=user_id,
                db=db_session,
                vector_store=vector_manager,
                tenant_id=user_id  # Use user_id as tenant_id for LLM config
            )
            return response
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Chat processing failed: {str(e)}"
            )
    
    async def get_conversations(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 50, 
        db_session = None
    ) -> List[ConversationResponse]:
        """
        Get user conversations.
        
        Args:
            user_id: Current user ID
            skip: Number of conversations to skip
            limit: Maximum number of conversations to return
            db_session: Database session
            
        Returns:
            List[ConversationResponse]: User's conversations
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(f"ChatController: Getting conversations for user {user_id}")
            
            conversations = await self.chat_service.get_user_conversations(
                user_id=user_id,
                skip=skip,
                limit=limit,
                db=db_session
            )
            
            logger.info(f"ChatController: Got {len(conversations)} conversations from service")
            
            # The service already returns ConversationResponse objects, no need to validate again
            return conversations
            
        except Exception as e:
            logger.error(f"ChatController: Error getting conversations for user {user_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Controller error: {str(e)}"
            )
    
    async def get_conversation(
        self, 
        conversation_id: str, 
        user_id: str, 
        db_session
    ) -> ConversationResponse:
        """
        Get specific conversation with full history.
        
        Args:
            conversation_id: Conversation ID
            user_id: Current user ID
            db_session: Database session
            
        Returns:
            ConversationResponse: Full conversation with messages
        """
        conversation = await self.chat_service.get_conversation_history(
            conversation_id=conversation_id,
            user_id=user_id,
            db=db_session
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return ConversationResponse.model_validate(conversation) 