"""
Memory Package Export.
Exposes a factory function to return the SQLite memory store.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.manager import MemoryStore
from app.memory.sqlite_store import SQLiteMemoryStore


def get_memory_store(db: AsyncSession) -> MemoryStore:
    """
    Returns the SQLite-backed MemoryStore instance.
    """
    return SQLiteMemoryStore(db)
