"""
Embedding generation service.
Supports local SentenceTransformers (default) and OpenAI embeddings.
Uses lazy loading to optimize memory usage on startup.
"""

from __future__ import annotations

from typing import List, Union
import numpy as np

from app.config import get_settings


class EmbeddingService:
    _local_model = None

    @classmethod
    def get_local_model(cls):
        """Lazy loads SentenceTransformer model."""
        if cls._local_model is None:
            settings = get_settings()
            try:
                from sentence_transformers import SentenceTransformer
                cls._local_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            except Exception as e:
                # Fallback / detailed error logging
                raise RuntimeError(f"Failed to load sentence-transformers model: {str(e)}")
        return cls._local_model

    @classmethod
    async def get_embeddings(cls, texts: List[str]) -> List[List[float]]:
        """
        Generates dense vector embeddings for a list of texts.
        """
        if not texts:
            return []

        settings = get_settings()
        
        # If using OpenAI embeddings
        if settings.DEFAULT_LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                response = await client.embeddings.create(
                    input=texts,
                    model="text-embedding-3-small"
                )
                return [data.embedding for data in response.data]
            except Exception:
                # If OpenAI fails or is not desired, fall back to local sentence-transformers
                pass

        # Generate embeddings using local SentenceTransformer
        model = cls.get_local_model()
        
        # Run blocking CPU bound execution in executor or synchronously if fast
        # SentenceTransformers encode is CPU-bound.
        embeddings = model.encode(texts, show_progress_bar=False)
        
        # Convert numpy array to list of floats
        if isinstance(embeddings, np.ndarray):
            return embeddings.tolist()
        return [list(emb) for emb in embeddings]

    @classmethod
    async def get_query_embedding(cls, query: str) -> List[float]:
        """Generates embedding for a single search query."""
        embeddings = await cls.get_embeddings([query])
        return embeddings[0]
