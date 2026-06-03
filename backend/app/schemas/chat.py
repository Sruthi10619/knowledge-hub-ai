"""
Chat and Conversation Pydantic Schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    citations: Optional[Dict[str, Any]] = None
    latency_ms: Optional[float] = None
    token_count: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    title: str = "New Conversation"


class ConversationCreate(ConversationBase):
    folder_id: str


class ConversationResponse(ConversationBase):
    id: str
    folder_id: str
    user_id: str
    summary: Optional[Dict[str, Any]] = None
    language: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    query: str
    llm_provider: Optional[str] = None
