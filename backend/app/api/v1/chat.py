"""
Chat and Conversational API Endpoints.
Provides streaming chat responses using Server-Sent Events (SSE).
"""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session, get_current_active_user
from app.db.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
    ChatRequest
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Creates a new isolated chat conversation workspace inside a folder."""
    return await ChatService.create_conversation(
        db=db,
        folder_id=payload.folder_id,
        user_id=current_user.id,
        title=payload.title
    )


@router.get("/folders/{folder_id}/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    folder_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Lists all active conversations inside a specific folder."""
    return await ChatService.list_conversations(
        db=db,
        folder_id=folder_id,
        user_id=current_user.id
    )


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves all messages in a conversation chronological order."""
    return await ChatService.get_messages(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Soft deletes a conversation."""
    await ChatService.delete_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id
    )


@router.post("/conversations/{conversation_id}/query")
async def send_chat_query(
    conversation_id: str,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Sends a query to the folder-isolated RAG pipeline inside the conversation.
    Returns a Server-Sent Events (SSE) stream of tokens, citations, and suggested follow-ups.
    """
    generator = ChatService.stream_chat(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        query=payload.query,
        llm_provider=payload.llm_provider
    )
    
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
