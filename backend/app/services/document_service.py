"""
Document Service managing uploads, indexing triggers, and deletion.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, UploadFile, status

from app.config import get_settings
from app.db.models.document import Document
from app.db.models.folder import Folder
from app.core.security import validate_file_upload, compute_file_hash, sanitize_filename
from app.services.folder_service import FolderService
from app.workers.task_manager import TaskManager
from app.workers.tasks import process_document_task
from app.rag.vectorstore import VectorStoreManager

logger = logging.getLogger(__name__)


class DocumentService:
    @staticmethod
    async def upload_document(
        db: AsyncSession,
        folder_id: str,
        user_id: str,
        file: UploadFile
    ) -> Document:
        settings = get_settings()

        if not file.filename or not str(file.filename).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file must have a filename.",
            )

        safe_filename = sanitize_filename(file.filename)

        # 1. Read file bytes
        try:
            content = await file.read()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read upload: {str(e)}"
            )

        # 2. Safety Validation (types, size limit, script injections)
        is_valid, err_msg = validate_file_upload(safe_filename, content, settings.MAX_UPLOAD_SIZE_MB)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=err_msg
            )

        # 3. Check folder existence and permissions
        folder = await FolderService.get_folder(db, folder_id, user_id)

        # Verify upload permission (only owners can upload)
        if folder.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the folder owner can upload documents."
            )

        # 4. Check for duplicate filenames inside same folder
        dup_stmt = select(Document).where(
            Document.folder_id == folder_id,
            Document.filename == safe_filename,
            Document.status != "failed"
        )
        dup_res = await db.execute(dup_stmt)
        if dup_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document '{safe_filename}' already exists in this folder."
            )

        # 5. Write file safely to uploads directory
        dest_dir = settings.UPLOAD_DIR / folder_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / safe_filename

        try:
            dest_path.write_bytes(content)
        except Exception as e:
            logger.error(f"File writing failed to {dest_path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not save file to disk storage."
            )

        # 6. Create database record
        doc = Document(
            folder_id=folder_id,
            user_id=user_id,
            filename=safe_filename,
            file_type=safe_filename.rsplit(".", 1)[-1].lower(),
            file_size=len(content),
            storage_path=str(dest_path),
            status="pending",
            metadata_json={"hash": compute_file_hash(content)}
        )
        db.add(doc)
        try:
            await db.commit()
            await db.refresh(doc)
        except Exception as e:
            await db.rollback()
            try:
                if dest_path.exists():
                    dest_path.unlink()
            except Exception as cleanup_err:
                logger.warning(f"Failed to remove orphan upload file {dest_path}: {cleanup_err}")
            logger.error(f"Database commit failed after file write: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not save document record.",
            )

        # 7. Queue background indexing task
        try:
            await TaskManager.enqueue(
                process_document_task,
                document_id=doc.id,
                folder_id=folder_id,
                file_path=str(dest_path),
                filename=safe_filename
            )
        except Exception as e:
            logger.error(f"Failed to queue background worker task: {e}")

        return doc

    @staticmethod
    async def list_documents(db: AsyncSession, folder_id: str, user_id: str) -> List[Document]:
        await FolderService.get_folder(db, folder_id, user_id)

        stmt = select(Document).where(Document.folder_id == folder_id).order_by(Document.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_document(db: AsyncSession, doc_id: str, user_id: str) -> Document:
        stmt = select(Document).where(Document.id == doc_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        await FolderService.get_folder(db, doc.folder_id, user_id)
        return doc

    @staticmethod
    async def reprocess_document(db: AsyncSession, doc_id: str, user_id: str) -> Document:
        stmt = select(Document).where(Document.id == doc_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        folder_stmt = select(Folder).where(Folder.id == doc.folder_id)
        folder_res = await db.execute(folder_stmt)
        folder = folder_res.scalar_one_or_none()
        if not folder or folder.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the folder owner can reprocess documents.",
            )

        if doc.status not in ("failed", "pending"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reprocess document with status '{doc.status}'.",
            )

        path = Path(doc.storage_path)
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Source file no longer exists on disk.",
            )

        doc.status = "pending"
        doc.error_message = None
        doc.chunk_count = 0
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        try:
            await TaskManager.enqueue(
                process_document_task,
                document_id=doc.id,
                folder_id=doc.folder_id,
                file_path=str(path),
                filename=doc.filename,
            )
        except Exception as e:
            logger.error(f"Failed to queue reprocess task: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not queue document for reprocessing.",
            )

        return doc

    @staticmethod
    async def delete_document(db: AsyncSession, doc_id: str, user_id: str) -> None:
        stmt = select(Document).where(Document.id == doc_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        # Verify folder ownership
        folder_stmt = select(Folder).where(Folder.id == doc.folder_id)
        folder_res = await db.execute(folder_stmt)
        folder = folder_res.scalar_one_or_none()
        if not folder or folder.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the folder owner can delete documents."
            )

        # 1. Clean vector chunks inside ChromaDB
        try:
            await VectorStoreManager.delete_document_chunks(doc.folder_id, doc.id)
        except Exception as e:
            logger.warning(f"Failed to clear Chroma chunks during document deletion: {e}")

        # 2. Remove file from storage
        try:
            path = Path(doc.storage_path)
            if path.exists():
                path.unlink()
        except Exception as e:
            logger.warning(f"Could not remove local file path {doc.storage_path}: {e}")

        # 3. Update folder count
        if folder.document_count > 0:
            folder.document_count -= 1
            db.add(folder)

        # 4. Remove SQL record
        await db.delete(doc)
        await db.commit()
