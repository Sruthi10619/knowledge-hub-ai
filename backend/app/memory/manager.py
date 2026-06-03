"""
Memory Manager base and abstract storage provider.
Scopes conversation memory to specific users, folders, and conversation IDs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class MemoryStore(ABC):
    @abstractmethod
    async def get_messages(
        self,
        user_id: str,
        folder_id: str,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """Retrieves list of message dicts (role, content) for the session."""
        pass

    @abstractmethod
    async def add_message(
        self,
        user_id: str,
        folder_id: str,
        conversation_id: str,
        role: str,
        content: str
    ) -> None:
        """Appends a single message to the session memory."""
        pass

    @abstractmethod
    async def clear(
        self,
        user_id: str,
        folder_id: str,
        conversation_id: str
    ) -> None:
        """Clears all conversation memory for the session."""
        pass

    @abstractmethod
    async def get_summary(
        self,
        user_id: str,
        folder_id: str,
        conversation_id: str
    ) -> Optional[str]:
        """Retrieves the conversation summary if it exists."""
        pass

    @abstractmethod
    async def save_summary(
        self,
        user_id: str,
        folder_id: str,
        conversation_id: str,
        summary: str
    ) -> None:
        """Saves a conversation summary."""
        pass
