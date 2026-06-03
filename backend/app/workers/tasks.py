"""
Background Tasks running in local ThreadPoolExecutor.
Handles multi-format parsing, recursive text splitting, embedding generation,
and ChromaDB indexing.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import async_session_factory
from app.db.models.document import Document
from app.db.models.folder import Folder
from app.rag.parser import DocumentParser
from app.rag.chunker import TextChunker
from app.rag.embeddings import EmbeddingService
from app.rag.vectorstore import VectorStoreManager

logger = logging.getLogger(__name__)


async def process_document_task(document_id: str, folder_id: str, file_path: str, filename: str) -> None:
    """
    Main document processing pipeline.
    Runs asynchronously, updating database states and index data.
    """
    logger.info(f"Starting background processing for document: {filename} ({document_id})")
    
    async with async_session_factory() as db:
        # 1. Retrieve document and set status to processing
        stmt = select(Document).where(Document.id == document_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            logger.error(f"Document {document_id} not found in database during task run.")
            return

        doc.status = "processing"
        db.add(doc)
        await db.commit()

        try:
            # 2. Read file content from local disk storage
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Source file not found at: {file_path}")
            
            content = path.read_bytes()

            # 3. Parse file text sections
            parsed_sections = DocumentParser.parse(filename, content)
            if not parsed_sections:
                raise ValueError("No extractable text content found in document.")

            # 4. Segment into overlapping chunks
            chunker = TextChunker()
            chunks = chunker.split_documents(parsed_sections)
            if not chunks:
                raise ValueError("Text split resulted in zero chunks.")

            # 5. Precompute dense vector embeddings
            texts = [c["text"] for c in chunks]
            embeddings = await EmbeddingService.get_embeddings(texts)

            # 6. Index chunks into folder collection in ChromaDB
            await VectorStoreManager.add_chunks(
                folder_id=folder_id,
                document_id=document_id,
                chunks=chunks,
                embeddings=embeddings
            )

            # 7. Update document state
            doc.status = "ready"
            doc.chunk_count = len(chunks)
            db.add(doc)

            # 8. Increment parent folder count
            folder_stmt = select(Folder).where(Folder.id == folder_id)
            folder_res = await db.execute(folder_stmt)
            folder = folder_res.scalar_one_or_none()
            if folder:
                folder.document_count += 1
                db.add(folder)

            await db.commit()
            logger.info(f"Successfully indexed document: {filename} into {len(chunks)} chunks.")

        except Exception as e:
            logger.error(f"Failed to process document {filename}: {e}", exc_info=True)
            # Rollback active changes on error and update status to failed
            await db.rollback()
            
            # Fetch fresh model reference to update error status
            res = await db.execute(select(Document).where(Document.id == document_id))
            doc = res.scalar_one()
            doc.status = "failed"
            doc.error_message = str(e)
            db.add(doc)
            await db.commit()
