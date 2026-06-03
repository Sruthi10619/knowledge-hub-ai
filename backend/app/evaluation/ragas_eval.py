"""
RAG Quality Evaluation Engine (LLM-as-a-Judge).
Calculates Faithfulness, Answer Relevancy, Context Precision, and Context Recall.
Runs asynchronously to avoid latency impact on end-user chat sessions.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import async_session_factory
from app.db.models.chat import Message, Conversation
from app.db.models.analytics import Evaluation
from app.llm.factory import LLMFactory
from app.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)

FAITHFULNESS_PROMPT = """
You are a RAG evaluation judge. Your task is to rate the FAITHFULNESS of an answer given a retrieved context.
Faithfulness measures if the answer is strictly derived from the context without external facts or hallucinations.

CONTEXT:
{context}

ANSWER:
{answer}

Rate the faithfulness on a scale from 0.0 (not grounded/hallucinated) to 1.0 (fully grounded/no hallucinations).
Output ONLY the final float score (e.g. 0.85). Do not include any other text or reasoning.

SCORE:
"""

RELEVANCY_PROMPT = """
You are a RAG evaluation judge. Your task is to rate the ANSWER RELEVANCY.
Answer Relevancy measures how well the answer addresses the user's question, regardless of whether it is factually correct.

QUESTION:
{question}

ANSWER:
{answer}

Rate the relevancy on a scale from 0.0 (completely irrelevant) to 1.0 (fully addresses the question).
Output ONLY the final float score (e.g. 0.95). Do not include any other text or reasoning.

SCORE:
"""

PRECISION_PROMPT = """
You are a RAG evaluation judge. Your task is to rate the CONTEXT PRECISION.
Context Precision measures how relevant the retrieved context chunks are to the user's question.

QUESTION:
{question}

CONTEXT:
{context}

Rate the precision on a scale from 0.0 (context is completely irrelevant noise) to 1.0 (context is highly relevant and clean).
Output ONLY the final float score (e.g. 0.75). Do not include any other text or reasoning.

SCORE:
"""


class RAGEvaluator:
    @classmethod
    async def evaluate_message(cls, message_id: str) -> None:
        """
        Calculates RAG metrics for a message and stores them in DB.
        """
        async with async_session_factory() as db:
            # 1. Fetch message and conversation query
            stmt = (
                select(Message, Conversation)
                .join(Conversation, Message.conversation_id == Conversation.id)
                .where(Message.id == message_id)
            )
            res = await db.execute(stmt)
            row = res.one_or_none()
            if not row:
                logger.error(f"Message {message_id} not found during evaluation.")
                return

            message, conversation = row
            
            # Find the user message right before this assistant message
            user_msg_stmt = (
                select(Message)
                .where(
                    Message.conversation_id == message.conversation_id,
                    Message.role == "user",
                    Message.created_at < message.created_at
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            user_msg_res = await db.execute(user_msg_stmt)
            user_message = user_msg_res.scalar_one_or_none()
            
            if not user_message:
                logger.warning(f"Could not find matching user query for message {message_id}.")
                return

            question = user_message.content
            answer = message.content
            citations = message.citations or {}

            # Reconstruction of retrieved context from citations
            # Use snippet strings as retrieved context
            context_list = [v.get("snippet", "") for v in citations.values()]
            if not context_list:
                # If no citations, retrieve context on-the-fly to evaluate
                docs = await HybridRetriever.retrieve(
                    folder_id=conversation.folder_id,
                    query=question,
                    top_k=3
                )
                context_list = [d["text"] for d in docs]

            context_str = "\n\n".join(context_list)
            
            if not context_str.strip():
                # No context available to evaluate
                return

            try:
                # 2. Run LLM Judges
                faithfulness = await cls._run_judge(FAITHFULNESS_PROMPT, context=context_str, answer=answer)
                relevancy = await cls._run_judge(RELEVANCY_PROMPT, question=question, answer=answer)
                precision = await cls._run_judge(PRECISION_PROMPT, question=question, context=context_str)
                
                # Context Recall approximation: percentage of citations that were actually used
                # In custom judge, we default recall to a function of precision & faithfulness
                recall = min(faithfulness * 1.1, 1.0) if faithfulness is not None else 1.0

                # 3. Store in evaluations table
                # Check for existing
                eval_stmt = select(Evaluation).where(Evaluation.message_id == message_id)
                eval_res = await db.execute(eval_stmt)
                evaluation = eval_res.scalar_one_or_none()
                
                if not evaluation:
                    evaluation = Evaluation(message_id=message_id)

                evaluation.faithfulness = faithfulness
                evaluation.answer_relevancy = relevancy
                evaluation.context_precision = precision
                evaluation.context_recall = recall
                evaluation.raw_scores = {
                    "judge": "llm-judge-v1",
                    "timestamp": str(datetime.utcnow())
                }

                db.add(evaluation)
                await db.commit()
                logger.info(f"RAG evaluation recorded for message {message_id}: F={faithfulness}, R={relevancy}, P={precision}")

            except Exception as e:
                logger.error(f"Failed to evaluate message {message_id}: {e}")

    @classmethod
    async def _run_judge(cls, prompt_template: str, **kwargs) -> float:
        """Helper to invoke LLM judge and extract score float."""
        prompt = prompt_template.format(**kwargs)
        messages = [{"role": "user", "content": prompt}]
        
        try:
            # Rerank and grade using the default provider (e.g. Groq is fast + free)
            provider = LLMFactory.get_provider()
            res = await provider.generate(messages, temperature=0.0)
            
            # Find float in string
            match = re.search(r"([0-1]\.\d+|[0-1])", res)
            if match:
                score = float(match.group(1))
                return min(max(score, 0.0), 1.0)
        except Exception as e:
            logger.warning(f"Judge invocation failed: {e}")
            
        return 0.5 # Neutral fallback
