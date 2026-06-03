"""
SQLite-backed memory store using ORM tables directly.
Perfect for single-container free HF Spaces deployments.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.manager import MemoryStore
from app.db.models.chat import Message as DBMessage, Conversation as DBConversation


class SQLiteMemoryStore(MemoryStore):
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_messages(
        self,
        user_id: str,
        folder_id: str,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        # Fetch last N messages sorted by created_at ascending
        stmt = (
            select(DBMessage)
            .join(DBConversation)
            .where(
                DBConversation.id == conversation_id,
                DBConversation.user_id == user_id,
                DBConversation.folder_id == folder_id,
                DBConversation.is_active == True
            )
            .order_by(desc(DBMessage.created_at))
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        messages = result.scalars().all()
        
        # Reverse to return chronological order (oldest first)
        return [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(messages)
        ]

    async def add_message(
        self,
        user_id: str,
        folder_id: str,
        conversation_id: str,
        role: str,
        content: str
    ) -> None:
        # Creating a message DB object and adding it to current session
        # The main database commit handles transaction scope
        msg = DBMessage(
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        self.db.add(msg)
        await self.db.flush()

    async def clear(
        self,
        user_id: str,
        folder_id: str,
        conversation_id: str
    ) -> None:
        stmt = (
            delete(DBMessage)
            .where(DBMessage.conversation_id == conversation_id)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_summary(
        self,
        user_id: str,
        folder_id: str,
        conversation_id: str
    ) -> Optional[str]:
        stmt = (
            select(DBConversation.summary)
            .where(
                DBConversation.id == conversation_id,
                DBConversation.user_id == user_id,
                DBConversation.folder_id == folder_id
            )
        )
        result = await self.db.execute(stmt)
        summary_dict = result.scalar_one_or_none()
        if summary_dict and isinstance(summary_dict, dict):
            return summary_dict.get("text")
        return None

    async def save_summary(
        self,
        user_id: str,
        folder_id: str,
        conversation_id: str,
        summary: str
    ) -> None:
        stmt = (
            select(DBConversation)
            .where(
                DBConversation.id == conversation_id,
                DBConversation.user_id == user_id,
                DBConversation.folder_id == folder_id
            )
        )
        result = await self.db.execute(stmt)
        conv = result.scalar_one_or_none()
        if conv:
            conv.summary = {"text": summary}
            self.db.add(conv)
            await self.db.flush()
