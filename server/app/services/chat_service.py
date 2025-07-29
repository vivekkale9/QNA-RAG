import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from ..db.postgres import User
from ..db.mongodb import Conversation, Message, MessageRole, QueryLog
from ..models.chat import (
    ChatRequest, ChatResponse, ConversationResponse, MessageResponse, 
    SourceResponse, MessageRole
)
from ..llm.llm_manager import LLMManager
from ..db.milvus_vector_store import MilvusVectorStore

logger = logging.getLogger(__name__)


class ChatService:
    
    def __init__(self):
        self.llm_manager = None  # Will be initialized with tenant context
        self.vector_store = None  # Will be injected
    
    async def process_chat_message(
        self,
        chat_request: ChatRequest,
        user_id: str,
        db: AsyncSession,
        vector_store: MilvusVectorStore,
        tenant_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Process a chat message and return response.
        
        Args:
            chat_request: Chat request data
            user_id: User ID
            db: PostgreSQL database session (for user verification)
            vector_store: Vector store manager
            tenant_id: Tenant ID for LLM configuration
            
        Returns:
            ChatResponse: Chat response with answer and sources
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            # Verify user exists
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Initialize LLM manager with tenant context
            self.llm_manager = LLMManager(tenant_id=tenant_id)
            
            # Get or create conversation
            conversation = await self._get_or_create_conversation(
                chat_request.conversation_id, user_id
            )
            
            # Store user message
            user_message = Message(
                conversation_id=str(conversation.id),
                role=MessageRole.USER,
                content=chat_request.message,
                user_id=user_id,
                created_at=datetime.now(timezone.utc)
            )
            await user_message.save()
            
            # Retrieve relevant context from vector store with user isolation
            context_results = await vector_store.search_similar_chunks(
                query=chat_request.message,
                user_id=user_id,
                k=chat_request.max_chunks or 5,
                doc_ids=chat_request.document_ids,
                similarity_threshold=0.5  # Lower threshold for better results
            )
            
            # Prepare context and sources with fallback handling
            if context_results:
                # Found relevant chunks - use them as context
                context_text = "\n\n".join([result["text"] for result in context_results])
                sources = [
                    SourceResponse(
                        document_id=result["doc_id"],
                        document_name=result.get("source", "Unknown Document"),
                        chunk_id=result["chunk_id"],
                        content=result["text"],
                        similarity_score=result["similarity_score"],
                        page_number=result["metadata"].get("page_number") if result.get("metadata") else None,
                        start_char=result["metadata"].get("start_char") if result.get("metadata") else None,
                        end_char=result["metadata"].get("end_char") if result.get("metadata") else None
                    )
                    for result in context_results
                ]
                has_context = True
            else:
                # No relevant chunks found - prepare fallback response
                context_text = ""
                sources = []
                has_context = False
                logger.info(f"No relevant chunks found for user {user_id} query: '{chat_request.message[:100]}...'")
            
            # Prepare messages for LLM
            messages = await self._prepare_llm_messages(conversation, chat_request.message, context_text, has_context)
            
            # Generate response from LLM
            logger.info(f"Generating LLM response for user {user_id} - Has context: {has_context}, Sources: {len(sources)}")
            
            try:
                llm_response = await self.llm_manager.generate_response(
                    messages=messages,
                    max_tokens=2000,
                    temperature=0.7
                )
                
                # Log successful generation
                logger.info(f"LLM response generated successfully - Provider: {llm_response.provider}, Model: {llm_response.model}")
                
            except Exception as e:
                logger.error(f"LLM generation failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate response: {str(e)}"
                )
            
            # Store AI message
            ai_message = Message(
                conversation_id=str(conversation.id),
                role=MessageRole.ASSISTANT,
                content=llm_response.content,
                user_id=user_id,
                sources=[source.dict() for source in sources],
                message_metadata={
                    "model_used": llm_response.model,
                    "provider": llm_response.provider,
                    "chunk_count": len(context_results),
                    "usage": llm_response.usage
                },
                created_at=datetime.now(timezone.utc)
            )
            await ai_message.save()
            
            # Log query for analytics
            await self._log_query(
                user_id=user_id,
                query=chat_request.message,
                response=llm_response.content,
                sources_count=len(sources),
                tokens_used=llm_response.usage.get("total_tokens", 0),
                response_time=0.0  # We can calculate this later if needed
            )
            
            # Update conversation metadata
            conversation.updated_at = datetime.now(timezone.utc)
            conversation.message_count = (conversation.message_count or 0) + 2
            await conversation.save()
            
            logger.info(f"Chat message processed for user {user_id}")
            
            return ChatResponse(
                message=llm_response.content,
                sources=sources,
                conversation_id=str(conversation.id),
                message_id=str(ai_message.id),
                tokens_used=llm_response.usage.get("total_tokens"),
                model_used=llm_response.model
            )
            
        except Exception as e:
            logger.error(f"Chat processing failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Chat processing failed"
            )
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        user_id: str,
        db: AsyncSession
    ) -> ConversationResponse:
        """
        Get conversation history.
        
        Args:
            conversation_id: Conversation ID
            user_id: User ID
            db: PostgreSQL database session (for user verification)
            
        Returns:
            ConversationResponse: Conversation with messages
            
        Raises:
            HTTPException: If conversation not found
        """
        try:
            # Verify user exists
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Get conversation from MongoDB
            conversation = await Conversation.get(conversation_id)
            
            if not conversation or conversation.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
            
            # Get messages
            messages = await Message.find(
                Message.conversation_id == conversation_id
            ).sort("+created_at").to_list()
            
            message_responses = [
                MessageResponse(
                    id=str(msg.id),
                    role=msg.role,
                    content=msg.content,
                    sources=[SourceResponse(**source) for source in (msg.sources or [])],
                    created_at=msg.created_at,
                    tokens_used=msg.tokens_used,
                    model_used=msg.model_used
                )
                for msg in messages
            ]
            
            return ConversationResponse(
                id=str(conversation.id),
                title=conversation.title,
                messages=message_responses,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get conversation history failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve conversation"
            )
    
    async def get_user_conversations(
        self,
        user_id: str,
        skip: int,
        limit: int,
        db: AsyncSession
    ) -> List[ConversationResponse]:
        """
        Get user's conversations.
        
        Args:
            user_id: User ID
            skip: Number of conversations to skip
            limit: Maximum number of conversations to return
            db: PostgreSQL database session (for user verification)
            
        Returns:
            List[ConversationResponse]: List of user conversations
            
        Raises:
            HTTPException: If user not found
        """
        try:
            # Verify user exists
            user = await self._get_user_by_id(db, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Get conversations from MongoDB
            conversations = await Conversation.find(
                Conversation.user_id == user_id
            ).sort("-updated_at").skip(skip).limit(limit).to_list()
            
            conversation_responses = []
            for conv in conversations:
                # Get recent messages for preview
                recent_messages = await Message.find(
                    Message.conversation_id == str(conv.id)
                ).sort("-created_at").limit(5).to_list()
                
                message_responses = [
                    MessageResponse(
                        id=str(msg.id),
                        role=msg.role,
                        content=msg.content,
                        sources=[SourceResponse(**source) for source in (msg.sources or [])],
                        created_at=msg.created_at,
                        tokens_used=msg.tokens_used,
                        model_used=msg.model_used
                    )
                    for msg in reversed(recent_messages)
                ]
                
                conversation_responses.append(
                    ConversationResponse(
                        id=str(conv.id),
                        title=conv.title,
                        messages=message_responses,
                        created_at=conv.created_at,
                        updated_at=conv.updated_at
                    )
                )
            
            return conversation_responses
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get user conversations failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve conversations"
            )
    
    # Private helper methods
    
    async def _get_user_by_id(self, db: AsyncSession, user_id: str) -> Optional[User]:
        """Get user by ID from PostgreSQL."""
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def _get_or_create_conversation(
        self, 
        conversation_id: Optional[str], 
        user_id: str
    ) -> Conversation:
        """Get existing conversation or create new one."""
        if conversation_id:
            conversation = await Conversation.get(conversation_id)
            if conversation and conversation.user_id == user_id:
                return conversation
        
        # Create new conversation
        conversation = Conversation(
            user_id=user_id,
            title="New Conversation",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await conversation.save()
        return conversation
    
    async def _prepare_llm_messages(
        self, 
        conversation: Conversation, 
        current_message: str, 
        context: str,
        has_context: bool = True
    ) -> List[Dict[str, str]]:
        """Prepare messages for LLM."""
        # Get recent conversation history
        recent_messages = await Message.find(
            Message.conversation_id == str(conversation.id)
        ).sort("-created_at").limit(10).to_list()
        
        # Prepare system message based on whether we have context
        if has_context and context:
            system_content = f"You are a helpful AI assistant. Use the following context to answer questions accurately:\n\n{context}"
        else:
            system_content = (
                "You are a helpful AI assistant. I could not find any relevant information in the uploaded documents for this query. "
                "Please provide a general response based on your knowledge, but start your response with: "
                "'I could not find any relevant information in the documents, but here's what I can tell you:'"
            )
        
        messages = [
            {
                "role": "system",
                "content": system_content
            }
        ]
        
        # Add conversation history (in chronological order)
        for msg in reversed(recent_messages):
            messages.append({
                "role": "user" if msg.role == MessageRole.USER else "assistant",
                "content": msg.content
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": current_message
        })
        
        return messages
    
    async def _log_query(
        self,
        user_id: str,
        query: str,
        response: str,
        sources_count: int,
        tokens_used: int,
        response_time: float
    ):
        """Log query for analytics."""
        query_log = QueryLog(
            user_id=user_id,
            query=query,
            response=response,
            sources_count=sources_count,
            tokens_used=tokens_used,
            response_time=response_time,
            created_at=datetime.now(timezone.utc)
        )
        await query_log.save() 