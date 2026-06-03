"""
Core RAG Pipeline Orchestrator.
Coordinates query rewriting, hybrid retrieval, guardrails checking, 
prompt construction, streaming LLM execution, and citation extraction.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.config import get_settings
from app.rag.retriever import HybridRetriever
from app.rag.prompts import DEFAULT_RAG_SYSTEM_PROMPT, QUERY_REWRITER_PROMPT, FOLLOWUP_QUESTIONS_PROMPT
from app.rag.citations import CitationExtractor
from app.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


class RAGPipeline:
    @classmethod
    async def rewrite_query(
        cls,
        query: str,
        chat_history: List[Dict[str, str]],
        provider_name: Optional[str] = None
    ) -> str:
        """
        Rewrites a conversational follow-up query into a standalone search query
        using the conversation history.
        """
        if not chat_history:
            return query

        # Format history for prompt
        history_str = ""
        for msg in chat_history[-6:]: # Check last 6 messages
            history_str += f"{msg['role'].capitalize()}: {msg['content']}\n"

        prompt = QUERY_REWRITER_PROMPT.format(
            chat_history=history_str,
            query=query
        )

        try:
            provider = LLMFactory.get_provider(provider_name)
            messages = [{"role": "user", "content": prompt}]
            rewritten = await provider.generate(messages, temperature=0.0)
            rewritten_clean = rewritten.strip().strip('"').strip("'")
            if rewritten_clean:
                return rewritten_clean
        except Exception as e:
            logger.warning(f"Query rewriting failed, using original query: {e}")
            
        return query

    @classmethod
    async def generate_followup_questions(
        cls,
        query: str,
        context_str: str,
        provider_name: Optional[str] = None
    ) -> List[str]:
        """
        Generates 3 suggested follow-up questions based on query and retrieved context.
        """
        prompt = FOLLOWUP_QUESTIONS_PROMPT.format(
            context=context_str,
            query=query
        )
        try:
            provider = LLMFactory.get_provider(provider_name)
            messages = [{"role": "user", "content": prompt}]
            response = await provider.generate(messages, temperature=0.7)
            # Find JSON block
            start_idx = response.find("[")
            end_idx = response.rfind("]") + 1
            if start_idx != -1 and end_idx != -1:
                questions = json.loads(response[start_idx:end_idx])
                return [q for q in questions if isinstance(q, str)][:3]
        except Exception as e:
            logger.debug(f"Failed to generate follow-up questions: {e}")
        return []

    @classmethod
    async def query(
        cls,
        folder_id: str,
        folder_name: str,
        query: str,
        chat_history: List[Dict[str, str]],
        llm_provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs the full RAG pipeline (non-streaming).
        Returns dict containing:
        - "answer": LLM generated response
        - "citations": source mappings
        - "followup_questions": list of questions
        """
        # 1. Query re-writing (resolve coreferences)
        standalone_query = await cls.rewrite_query(query, chat_history, llm_provider)

        # 2. Retrieve documents
        retrieved_docs = await HybridRetriever.retrieve(
            folder_id=folder_id,
            query=standalone_query
        )

        if not retrieved_docs:
            return {
                "answer": "I could not find that information in this folder’s knowledge base.",
                "citations": {},
                "followup_questions": []
            }

        # 3. Format context
        context_parts = []
        for idx, doc in enumerate(retrieved_docs):
            source_num = idx + 1
            source_name = doc["metadata"].get("source", "Unknown Document")
            page_info = f", Page {doc['metadata']['page']}" if "page" in doc["metadata"] else ""
            context_parts.append(
                f"[{source_num}] Source: {source_name}{page_info}\nContent: {doc['text']}"
            )
        context_str = "\n\n".join(context_parts)

        # 4. Formulate messages
        system_prompt = DEFAULT_RAG_SYSTEM_PROMPT.format(
            folder_name=folder_name,
            context=context_str
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        # Append short-term memory (e.g. last 4 messages to keep context grounded)
        for msg in chat_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Append latest user query
        messages.append({"role": "user", "content": query})

        # 5. Generate Response
        provider = LLMFactory.get_provider(llm_provider)
        answer = await provider.generate(messages, temperature=0.0)

        # 6. Extract citations
        citation_results = CitationExtractor.extract_citations(answer, retrieved_docs)

        # 7. Generate follow-ups
        followups = await cls.generate_followup_questions(standalone_query, context_str, llm_provider)

        return {
            "answer": citation_results["text"],
            "citations": citation_results["citations"],
            "followup_questions": followups
        }

    @classmethod
    async def query_stream(
        cls,
        folder_id: str,
        folder_name: str,
        query: str,
        chat_history: List[Dict[str, str]],
        llm_provider: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Runs the full RAG pipeline streaming token-by-token.
        Yields dicts with keys:
        - "type": "token" | "citations" | "followup"
        - "content": token string or citations dict or follow-up list
        """
        # 1. Query re-writing
        standalone_query = await cls.rewrite_query(query, chat_history, llm_provider)

        # 2. Retrieve documents
        retrieved_docs = await HybridRetriever.retrieve(
            folder_id=folder_id,
            query=standalone_query
        )

        if not retrieved_docs:
            yield {
                "type": "token",
                "content": "I could not find that information in this folder’s knowledge base."
            }
            yield {
                "type": "citations",
                "content": {}
            }
            yield {
                "type": "followup",
                "content": []
            }
            return

        # 3. Format context
        context_parts = []
        for idx, doc in enumerate(retrieved_docs):
            source_num = idx + 1
            source_name = doc["metadata"].get("source", "Unknown Document")
            page_info = f", Page {doc['metadata']['page']}" if "page" in doc["metadata"] else ""
            context_parts.append(
                f"[{source_num}] Source: {source_name}{page_info}\nContent: {doc['text']}"
            )
        context_str = "\n\n".join(context_parts)

        # 4. Formulate messages
        system_prompt = DEFAULT_RAG_SYSTEM_PROMPT.format(
            folder_name=folder_name,
            context=context_str
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        for msg in chat_history[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        messages.append({"role": "user", "content": query})

        # 5. Stream generation
        provider = LLMFactory.get_provider(llm_provider)
        full_response = ""
        
        async for token in provider.generate_stream(messages, temperature=0.0):
            full_response += token
            yield {
                "type": "token",
                "content": token
            }

        # 6. Extract citations on the completed text
        citation_results = CitationExtractor.extract_citations(full_response, retrieved_docs)
        yield {
            "type": "citations",
            "content": citation_results["citations"]
        }

        # 7. Generate followups
        followups = await cls.generate_followup_questions(standalone_query, context_str, llm_provider)
        yield {
            "type": "followup",
            "content": followups
        }
