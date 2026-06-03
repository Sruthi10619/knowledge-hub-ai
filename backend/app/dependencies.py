"""
Dependency Injection helpers for FastAPI endpoints.
"""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db as db_generator
from app.core.security import get_current_user as current_user_getter
from app.db.models.user import User

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to retrieve an async database session."""
    async for session in db_generator():
        yield session

async def get_current_active_user(
    current_user: User = Depends(current_user_getter)
) -> User:
    """Dependency to get the current authenticated and active user."""
    return current_user
