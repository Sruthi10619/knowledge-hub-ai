"""
Analytics Service compiling usage, performance, and RAG evaluation metrics.
Uses the relational DB tables as the primary observability store.
"""

from __future__ import annotations
from typing import Optional

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.models.folder import Folder
from app.db.models.document import Document
from app.db.models.chat import Conversation, Message
from app.db.models.analytics import AnalyticsEvent, Evaluation

logger = logging.getLogger(__name__)


class AnalyticsService:
    @staticmethod
    async def get_dashboard_stats(db: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        Calculates workspace stats: document counts, chats, average latency, 
        and daily request volumes for charts.
        """
        # 1. Total folders
        folder_count_stmt = select(func.count(Folder.id)).where(Folder.user_id == user_id)
        folder_count_res = await db.execute(folder_count_stmt)
        total_folders = folder_count_res.scalar() or 0

        # 2. Total documents
        doc_count_stmt = select(func.count(Document.id)).where(Document.user_id == user_id)
        doc_count_res = await db.execute(doc_count_stmt)
        total_docs = doc_count_res.scalar() or 0

        # 3. Total conversations
        conv_count_stmt = select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
        conv_count_res = await db.execute(conv_count_stmt)
        total_conversations = conv_count_res.scalar() or 0

        # 4. Total assistant messages and average latency
        msg_stmt = (
            select(
                func.count(Message.id),
                func.avg(Message.latency_ms)
            )
            .join(Conversation)
            .where(
                Conversation.user_id == user_id,
                Message.role == "assistant"
            )
        )
        msg_res = await db.execute(msg_stmt)
        msg_count, avg_latency = msg_res.all()[0]
        
        total_queries = msg_count or 0
        avg_latency_ms = float(avg_latency) if avg_latency is not None else 0.0

        # 5. Timeline data (last 7 days of queries)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        timeline_stmt = (
            select(
                func.date(Message.created_at).label("query_date"),
                func.count(Message.id).label("query_count")
            )
            .join(Conversation)
            .where(
                Conversation.user_id == user_id,
                Message.role == "assistant",
                Message.created_at >= seven_days_ago
            )
            .group_by(func.date(Message.created_at))
            .order_by(func.date(Message.created_at))
        )
        timeline_res = await db.execute(timeline_stmt)
        timeline = [
            {"date": str(row[0]), "queries": row[1]}
            for row in timeline_res.all()
        ]

        # 6. RAGAS average scores (Observability & quality check)
        eval_stmt = (
            select(
                func.avg(Evaluation.faithfulness).label("avg_faithfulness"),
                func.avg(Evaluation.answer_relevancy).label("avg_relevancy"),
                func.avg(Evaluation.context_precision).label("avg_precision"),
                func.avg(Evaluation.context_recall).label("avg_recall")
            )
            .join(Message, Evaluation.message_id == Message.id)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Conversation.user_id == user_id)
        )
        eval_res = await db.execute(eval_stmt)
        eval_row = eval_res.all()[0]
        
        evaluation_averages = {
            "faithfulness": float(eval_row[0]) if eval_row[0] is not None else 0.0,
            "answer_relevancy": float(eval_row[1]) if eval_row[1] is not None else 0.0,
            "context_precision": float(eval_row[2]) if eval_row[2] is not None else 0.0,
            "context_recall": float(eval_row[3]) if eval_row[3] is not None else 0.0,
        }

        # 7. Document indexing states summary
        doc_states_stmt = (
            select(Document.status, func.count(Document.id))
            .where(Document.user_id == user_id)
            .group_by(Document.status)
        )
        doc_states_res = await db.execute(doc_states_stmt)
        states = {row[0]: row[1] for row in doc_states_res.all()}

        return {
            "total_folders": total_folders,
            "total_documents": total_docs,
            "total_conversations": total_conversations,
            "total_queries": total_queries,
            "avg_latency_ms": avg_latency_ms,
            "timeline": timeline,
            "evaluation_metrics": evaluation_averages,
            "document_status_distribution": states
        }

    @staticmethod
    async def log_event(
        db: AsyncSession,
        user_id: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None
    ) -> AnalyticsEvent:
        event = AnalyticsEvent(
            user_id=user_id,
            event_type=event_type,
            event_data=event_data
        )
        db.add(event)
        await db.commit()
        return event
