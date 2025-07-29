"""
Chat Routes

Defines HTTP endpoints for chat functionality and delegates all logic to controllers.
"""

from typing import List
from fastapi import APIRouter, Depends, Query

from ..controllers import ChatController
from ..models import ChatRequest, ChatResponse, ConversationResponse
from ..db import get_postgres_database  # For user verification
from ..utils import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])
chat_controller = ChatController()


@router.post("/", response_model=ChatResponse)
async def send_message(
    chat_request: ChatRequest,
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)  # For user verification
):
    return await chat_controller.send_message(
        chat_request, current_user.id, db_session
    )


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)  # For user verification
):
    """Get conversations endpoint - delegates to controller."""
    return await chat_controller.get_conversations(
        current_user.id, skip, limit, db_session
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user = Depends(get_current_user),
    db_session = Depends(get_postgres_database)  # For user verification
):
    """Get specific conversation endpoint - delegates to controller."""
    return await chat_controller.get_conversation(
        conversation_id, current_user.id, db_session
    ) 