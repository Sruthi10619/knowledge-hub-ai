"""
Hybrid Retriever combining Dense (ChromaDB) and Sparse (BM25) search.
Includes Cross-Encoder Reranking for enhanced precision.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from rank_bm25 import BM25Okapi
import numpy as np

from app.config import get_settings
from app.rag.embeddings import EmbeddingService
from app.rag.vectorstore import VectorStoreManager

logger = logging.getLogger(__name__)


class HybridRetriever:
    _reranker_model = None

    @classmethod
    def get_reranker(cls):
        """Lazy loads Reranker model."""
        settings = get_settings()
        if not settings.RERANKING_ENABLED:
            return None

        if cls._reranker_model is None:
            try:
                from sentence_transformers import CrossEncoder
                cls._reranker_model = CrossEncoder(settings.RERANKING_MODEL)
            except Exception as e:
                logger.warning(f"Failed to load reranker model. Reranking will be disabled: {e}")
                settings.RERANKING_ENABLED = False
        return cls._reranker_model

    @classmethod
    async def retrieve(
        cls,
        folder_id: str,
        query: str,
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Main retrieval method combining dense and sparse search.
        Reranks results using Cross-Encoder.
        """
        settings = get_settings()
        
        # 1. Generate query embedding
        query_embedding = await EmbeddingService.get_query_embedding(query)

        # 2. Dense Search (fetch double top_k to allow hybrid fusion and reranking)
        dense_results = await VectorStoreManager.similarity_search(
            folder_id=folder_id,
            query_embedding=query_embedding,
            top_k=max(top_k * 4, 30),
            where_filter=where_filter
        )

        if not dense_results:
            return []

        # 3. Sparse Search (BM25 Okapi)
        # We index the texts fetched from dense search to find keyword relevance
        # This acts as a secondary filter / reranker.
        corpus = [doc["text"] for doc in dense_results]
        tokenized_corpus = [doc.lower().split(" ") for doc in corpus]
        
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.lower().split(" ")
        bm25_scores = bm25.get_scores(tokenized_query)

        # Combine Dense and Sparse scores (Reciprocal Rank Fusion)
        # RRF combines ranks instead of raw scores
        dense_ranks = {doc["id"]: idx for idx, doc in enumerate(dense_results)}
        
        # Sort by BM25 score
        sorted_sparse_indices = np.argsort(bm25_scores)[::-1]
        sparse_ranks = {dense_results[idx]["id"]: rank for rank, idx in enumerate(sorted_sparse_indices)}

        rrf_scores = {}
        k_rrf = 60 # Constant for RRF
        
        for doc in dense_results:
            doc_id = doc["id"]
            dense_rank = dense_ranks[doc_id]
            sparse_rank = sparse_ranks[doc_id]
            
            # RRF formula
            rrf_scores[doc_id] = (1.0 / (k_rrf + dense_rank)) + (1.0 / (k_rrf + sparse_rank))

        # Sort documents by RRF score
        fused_docs = sorted(dense_results, key=lambda x: rrf_scores[x["id"]], reverse=True)
        candidate_docs = fused_docs[:top_k * 3]

        # 4. Cross-Encoder Reranking
        reranker = cls.get_reranker()
        if reranker and candidate_docs:
            pairs = [[query, doc["text"]] for doc in candidate_docs]
            rerank_scores = reranker.predict(pairs)
            
            # Attach rerank score and sort
            for idx, score in enumerate(rerank_scores):
                # Sigmoid scaling to turn raw logits into 0-1 confidence scores
                confidence = 1.0 / (1.0 + np.exp(-score))
                candidate_docs[idx]["score"] = float(confidence)

            # Re-sort based on reranker scores
            reranked_docs = sorted(candidate_docs, key=lambda x: x["score"], reverse=True)
        else:
            reranked_docs = candidate_docs

        # 5. Filter by confidence threshold
        final_docs = [
            doc for doc in reranked_docs 
            if doc.get("score", 1.0) >= settings.CONFIDENCE_THRESHOLD
        ]

        # Return top_k docs
        return final_docs[:top_k]
