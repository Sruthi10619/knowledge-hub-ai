"""Folder and FolderShare models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Boolean, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(10), default="📁")
    color: Mapped[str] = mapped_column(String(7), default="#6366f1")
    chromadb_collection: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="folders")
    documents = relationship("Document", back_populates="folder", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="folder", cascade="all, delete-orphan")
    shares = relationship("FolderShare", back_populates="folder", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Folder {self.name}>"


class FolderShare(Base):
    __tablename__ = "folder_shares"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    folder_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("folders.id", ondelete="CASCADE"), nullable=False
    )
    shared_with_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    permission: Mapped[str] = mapped_column(String(10), default="read")  # read | write

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    folder = relationship("Folder", back_populates="shares")
