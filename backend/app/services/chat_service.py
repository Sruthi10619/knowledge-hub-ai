"""
Chat Service managing Conversations and Messages.
Bridges API endpoints to the RAG Pipeline and stores chat messages in the database.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from typing import Any, AsyncGenerator, Dict, List, Optional
from sqlalchemy import select, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.db.models.chat import Conversation, Message
from app.db.models.folder import Folder
from app.rag.pipeline import RAGPipeline
from app.memory import get_memory_store

logger = logging.getLogger(__name__)

# Prevent concurrent stream requests on the same conversation (double-submit guard)
_conversation_stream_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


class ChatService:
    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        folder_id: str,
        user_id: str,
        title: str = "New Conversation"
    ) -> Conversation:
        # Check folder ownership/permissions
        folder_stmt = select(Folder).where(Folder.id == folder_id)
        folder_res = await db.execute(folder_stmt)
        folder = folder_res.scalar_one_or_none()
        if not folder:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
        
        # Verify ownership or shared permission
        if folder.user_id != user_id and not folder.is_shared:
            # We can check folder_shares here if needed, keeping it simple for MVP
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        conv = Conversation(
            folder_id=folder_id,
            user_id=user_id,
            title=title
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return conv

    @staticmethod
    async def list_conversations(
        db: AsyncSession,
        folder_id: str,
        user_id: str
    ) -> List[Conversation]:
        stmt = (
            select(Conversation)
            .where(
                Conversation.folder_id == folder_id,
                Conversation.user_id == user_id,
                Conversation.is_active == True
            )
            .order_by(desc(Conversation.created_at))
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        conversation_id: str,
        user_id: str
    ) -> List[Message]:
        # Validate conversation ownership
        conv_stmt = select(Conversation).where(Conversation.id == conversation_id)
        conv_res = await db.execute(conv_stmt)
        conv = conv_res.scalar_one_or_none()
        if not conv or conv.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def delete_conversation(
        db: AsyncSession,
        conversation_id: str,
        user_id: str
    ) -> None:
        stmt = select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        res = await db.execute(stmt)
        conv = res.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        # Soft delete conversation
        conv.is_active = False
        db.add(conv)
        await db.commit()

    @classmethod
    async def stream_chat(
        cls,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        query: str,
        llm_provider: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Coordinates streaming token output, database writes, memory updates.
        Yields Server-Sent Events (SSE) serialized strings.
        """
        lock = _conversation_stream_locks[conversation_id]
        if lock.locked():
            yield f"event: error\ndata: {json.dumps({'detail': 'A response is already being generated for this conversation.'})}\n\n"
            return

        async with lock:
            async for event in cls._stream_chat_locked(
                db=db,
                conversation_id=conversation_id,
                user_id=user_id,
                query=query,
                llm_provider=llm_provider,
            ):
                yield event

    @classmethod
    async def _stream_chat_locked(
        cls,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        query: str,
        llm_provider: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        from sqlalchemy import select, desc
        from datetime import datetime, timezone
        from app.db.models.chat import Message
        # Validate conversation + get folder details
        stmt = (
            select(Conversation, Folder)
            .join(Folder, Conversation.folder_id == Folder.id)
            .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        )
        res = await db.execute(stmt)
        row = res.one_or_none()
        if not row:
            yield "event: error\ndata: {\"detail\": \"Conversation not found\"}\n\n"
            return
        
        conv, folder = row

        # Run Input safety check
        from app.guardrails.safety import SafetyGuardrails
        from app.core.exceptions import GuardrailViolation
        try:
            SafetyGuardrails.verify_input(query)
        except GuardrailViolation as gv:
            yield f"event: error\ndata: {json.dumps({'detail': str(gv)})}\n\n"
            return

        # Initialize memory store
        mem_store = get_memory_store(db)
        history = await mem_store.get_messages(user_id, folder.id, conversation_id)

        # Check for exact duplicate query in the last 5 seconds to prevent double-submits
        last_msg_stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.role == "user")
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        last_msg_res = await db.execute(last_msg_stmt)
        last_msg = last_msg_res.scalar_one_or_none()
        
        if last_msg and last_msg.content == query:
            time_diff = datetime.now(timezone.utc).replace(tzinfo=None) - last_msg.created_at
            if time_diff.total_seconds() < 5:
                yield f"event: error\ndata: {json.dumps({'detail': 'Duplicate query detected in a short time frame.'})}\n\n"
                return

        # Write user query to persistent DB
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=query
        )
        db.add(user_msg)
        await db.commit()
        # NOTE: Do NOT call mem_store.add_message for user here — SQLiteMemoryStore writes
        # to the same Message table, which would create a duplicate row.

        # Stream response from pipeline
        full_answer = ""
        citations = {}
        followup_questions = []

        start_time = time.perf_counter()
        
        try:
            async for chunk in RAGPipeline.query_stream(
                folder_id=folder.id,
                folder_name=folder.name,
                query=query,
                chat_history=history,
                llm_provider=llm_provider
            ):
                chunk_type = chunk["type"]
                content = chunk["content"]

                if chunk_type == "token":
                    full_answer += content
                    yield f"event: token\ndata: {json.dumps(content)}\n\n"
                elif chunk_type == "citations":
                    citations = content
                    yield f"event: citations\ndata: {json.dumps(content)}\n\n"
                elif chunk_type == "followup":
                    followup_questions = content
                    yield f"event: followup\ndata: {json.dumps(content)}\n\n"

        except Exception as e:
            logger.error(f"Stream generation encountered an error: {e}")
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
            return

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Run Output safety check
        try:
            SafetyGuardrails.verify_output(full_answer)
        except GuardrailViolation as gv:
            full_answer = "Response blocked: Generated answer violates the safety policy."
            citations = {}
            followup_questions = []

        # Save completed assistant response to SQL database
        # NOTE: Do NOT call mem_store.add_message for assistant here — SQLiteMemoryStore writes
        # to the same Message table, which would create a duplicate row.
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_answer,
            citations=citations,
            latency_ms=elapsed_ms,
            metadata_json={"followup_questions": followup_questions}
        )
        db.add(assistant_msg)
        await db.commit()

        # Enqueue background RAG evaluation (LLM-as-a-judge)
        try:
            from app.workers.task_manager import TaskManager
            from app.evaluation.ragas_eval import RAGEvaluator
            await TaskManager.enqueue(RAGEvaluator.evaluate_message, message_id=assistant_msg.id)
        except Exception as eval_err:
            logger.error(f"Failed to enqueue RAG evaluation: {eval_err}")
        
        yield "event: done\ndata: [DONE]\n\n"
