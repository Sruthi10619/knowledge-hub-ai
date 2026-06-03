"""
Folder Workspaces API Endpoints.
"""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session, get_current_active_user
from app.db.models.user import User
from app.schemas.folder import (
    FolderCreate,
    FolderUpdate,
    FolderResponse,
    FolderShareRequest,
    FolderShareResponse
)
from app.services.folder_service import FolderService

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    payload: FolderCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Creates a new isolated workspace folder."""
    return await FolderService.create_folder(
        db=db,
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        icon=payload.icon,
        color=payload.color
    )


@router.get("", response_model=List[FolderResponse])
async def list_folders(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Lists all folders owned by or shared with the authenticated user."""
    return await FolderService.list_folders(db=db, user_id=current_user.id)


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Gets details of a single workspace folder."""
    return await FolderService.get_folder(db=db, folder_id=folder_id, user_id=current_user.id)


@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    payload: FolderUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Updates a folder's properties (title, icon, description, color)."""
    return await FolderService.update_folder(
        db=db,
        folder_id=folder_id,
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        icon=payload.icon,
        color=payload.color
    )


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Permanently deletes a folder and removes its items from the vector index."""
    await FolderService.delete_folder(db=db, folder_id=folder_id, user_id=current_user.id)


@router.post("/{folder_id}/share", response_model=FolderShareResponse)
async def share_folder(
    folder_id: str,
    payload: FolderShareRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Shares a folder with another user by email."""
    return await FolderService.share_folder(
        db=db,
        folder_id=folder_id,
        owner_id=current_user.id,
        share_with_email=payload.email,
        permission=payload.permission
    )
