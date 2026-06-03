"""
Folder Service managing workspaces.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status

from app.db.models.folder import Folder, FolderShare
from app.db.models.document import Document
from app.rag.vectorstore import VectorStoreManager

logger = logging.getLogger(__name__)


class FolderService:
    @staticmethod
    async def create_folder(
        db: AsyncSession,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        icon: str = "📁",
        color: str = "#6366f1"
    ) -> Folder:
        # ChromaDB collection name unique to this folder
        import uuid
        folder_id = str(uuid.uuid4())
        collection_name = VectorStoreManager.get_collection_name(folder_id)

        # Precreate the collection in vector DB
        try:
            VectorStoreManager.get_or_create_collection(folder_id)
        except Exception as e:
            logger.error(f"Failed to create ChromaDB collection: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize folder storage index."
            )

        folder = Folder(
            id=folder_id,
            user_id=user_id,
            name=name,
            description=description,
            icon=icon,
            color=color,
            chromadb_collection=collection_name
        )
        db.add(folder)
        await db.commit()
        await db.refresh(folder)
        return folder

    @staticmethod
    async def list_folders(db: AsyncSession, user_id: str) -> List[Folder]:
        # Lists owned and shared folders
        stmt = select(Folder).where(Folder.user_id == user_id)
        res = await db.execute(stmt)
        owned_folders = list(res.scalars().all())
        
        # Fetch shared folders via FolderShare
        shared_stmt = (
            select(Folder)
            .join(FolderShare, Folder.id == FolderShare.folder_id)
            .where(FolderShare.shared_with_user_id == user_id)
        )
        shared_res = await db.execute(shared_stmt)
        shared_folders = list(shared_res.scalars().all())
        
        return list(set(owned_folders + shared_folders))

    @staticmethod
    async def get_folder(db: AsyncSession, folder_id: str, user_id: str) -> Folder:
        stmt = select(Folder).where(Folder.id == folder_id)
        res = await db.execute(stmt)
        folder = res.scalar_one_or_none()
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
            
        # Verify access
        if folder.user_id != user_id:
            # Check share
            share_stmt = select(FolderShare).where(
                FolderShare.folder_id == folder_id,
                FolderShare.shared_with_user_id == user_id
            )
            share_res = await db.execute(share_stmt)
            if not share_res.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
                
        return folder

    @staticmethod
    async def update_folder(
        db: AsyncSession,
        folder_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None
    ) -> Folder:
        folder = await FolderService.get_folder(db, folder_id, user_id)
        if folder.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the folder owner can update folder properties."
            )

        if name:
            folder.name = name
        if description is not None:
            folder.description = description
        if icon:
            folder.icon = icon
        if color:
            folder.color = color

        db.add(folder)
        await db.commit()
        await db.refresh(folder)
        return folder

    @staticmethod
    async def delete_folder(db: AsyncSession, folder_id: str, user_id: str) -> None:
        folder = await FolderService.get_folder(db, folder_id, user_id)
        if folder.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the folder owner can delete the folder."
            )

        # 1. Drop ChromaDB Collection asynchronously/synchronously
        try:
            await VectorStoreManager.delete_folder_collection(folder_id)
        except Exception as e:
            logger.warning(f"Error dropping Chroma collection during folder delete: {e}")

        # 2. Delete folder from database (cascades document, share, conversation deletes)
        await db.delete(folder)
        await db.commit()

    @staticmethod
    async def share_folder(
        db: AsyncSession,
        folder_id: str,
        owner_id: str,
        share_with_email: str,
        permission: str = "read"
    ) -> FolderShare:
        folder = await FolderService.get_folder(db, folder_id, owner_id)
        if folder.user_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner can share this folder."
            )

        # Resolve share_with user
        from app.db.models.user import User
        user_stmt = select(User).where(User.email == share_with_email)
        user_res = await db.execute(user_stmt)
        target_user = user_res.scalar_one_or_none()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email '{share_with_email}' does not exist."
            )

        if target_user.id == owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot share a folder with yourself."
            )

        # Check existing share
        share_stmt = select(FolderShare).where(
            FolderShare.folder_id == folder_id,
            FolderShare.shared_with_user_id == target_user.id
        )
        share_res = await db.execute(share_stmt)
        existing_share = share_res.scalar_one_or_none()
        if existing_share:
            existing_share.permission = permission
            db.add(existing_share)
            await db.commit()
            return existing_share

        share = FolderShare(
            folder_id=folder_id,
            shared_with_user_id=target_user.id,
            permission=permission
        )
        db.add(share)
        
        # Update folder state
        folder.is_shared = True
        db.add(folder)
        
        await db.commit()
        await db.refresh(share)
        return share
