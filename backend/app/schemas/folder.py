"""
Folder Workspace Pydantic Schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class FolderBase(BaseModel):
    name: str
    description: Optional[str] = None
    icon: str = "📁"
    color: str = "#6366f1"


class FolderCreate(FolderBase):
    pass


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class FolderResponse(FolderBase):
    id: str
    user_id: str
    chromadb_collection: str
    document_count: int
    is_shared: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FolderShareRequest(BaseModel):
    email: EmailStr
    permission: str = "read"  # read | write


class FolderShareResponse(BaseModel):
    id: str
    folder_id: str
    shared_with_user_id: str
    permission: str
    created_at: datetime

    class Config:
        from_attributes = True
