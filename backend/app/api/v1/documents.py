"""
Documents API Endpoints.
"""

from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session, get_current_active_user
from app.db.models.user import User
from app.schemas.document import DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="", tags=["documents"])


@router.post("/folders/{folder_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    folder_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """
    Uploads a new document file (PDF, DOCX, TXT, MD, CSV) to a workspace folder.
    Immediately triggers background processing to chunk and embed text.
    """
    return await DocumentService.upload_document(
        db=db,
        folder_id=folder_id,
        user_id=current_user.id,
        file=file
    )


@router.get("/folders/{folder_id}/documents", response_model=List[DocumentResponse])
async def list_documents(
    folder_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Lists all files uploaded into a specific workspace folder."""
    return await DocumentService.list_documents(
        db=db,
        folder_id=folder_id,
        user_id=current_user.id
    )


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves metadata and processing status for a single document."""
    return await DocumentService.get_document(
        db=db,
        doc_id=doc_id,
        user_id=current_user.id
    )


@router.post("/documents/{doc_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
):
    """Re-queue indexing for a failed or stuck pending document."""
    return await DocumentService.reprocess_document(
        db=db,
        doc_id=doc_id,
        user_id=current_user.id,
    )


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Deletes a document from SQL DB, deletes local storage file, and removes vector embeddings."""
    await DocumentService.delete_document(
        db=db,
        doc_id=doc_id,
        user_id=current_user.id
    )
