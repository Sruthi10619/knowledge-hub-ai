"""
ChromaDB vector store manager.
Implements folder-based index isolation using ChromaDB collections.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings


class VectorStoreManager:
    _client = None

    @classmethod
    def get_client(cls):
        """Singleton ChromaDB client initialization."""
        if cls._client is None:
            settings = get_settings()
            cls._client = chromadb.PersistentClient(
                path=str(settings.CHROMA_PERSIST_DIR),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        return cls._client

    @classmethod
    def get_collection_name(cls, folder_id: str) -> str:
        """Standard collection naming convention for folders."""
        # ChromaDB collections must start with a letter/digit, be 3-63 chars, and contain no consecutive dots
        # folder_id is a UUID (36 chars) so 'f_' + UUID is 38 chars, perfect.
        cleaned_uuid = folder_id.replace("-", "_")
        return f"f_{cleaned_uuid}"

    @classmethod
    def get_or_create_collection(cls, folder_id: str):
        client = cls.get_client()
        name = cls.get_collection_name(folder_id)
        # Using L2 (squared l2) or cosine distance
        return client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )

    @classmethod
    async def add_chunks(
        cls,
        folder_id: str,
        document_id: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """
        Adds text chunks and their precomputed embeddings to a folder's collection.
        """
        if not chunks:
            return

        collection = cls.get_or_create_collection(folder_id)
        
        ids = []
        documents = []
        metadatas = []
        
        for idx, chunk in enumerate(chunks):
            # Unique ID for each chunk: document_id + chunk_index
            chunk_id = f"{document_id}_c{idx}"
            ids.append(chunk_id)
            documents.append(chunk["text"])
            
            # Enrich metadata
            meta = chunk["metadata"].copy()
            meta["document_id"] = document_id
            
            # ChromaDB metadata values must be str, int, float, or bool
            cleaned_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    cleaned_meta[k] = v
                elif isinstance(v, list):
                    cleaned_meta[k] = ",".join(map(str, v))
                else:
                    cleaned_meta[k] = str(v)
            metadatas.append(cleaned_meta)

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

    @classmethod
    async def delete_document_chunks(cls, folder_id: str, document_id: str) -> None:
        """Deletes all chunks corresponding to a specific document."""
        try:
            client = cls.get_client()
            name = cls.get_collection_name(folder_id)
            collection = client.get_collection(name)
            collection.delete(where={"document_id": document_id})
        except Exception:
            # Collection might not exist yet or was already deleted
            pass

    @classmethod
    async def delete_folder_collection(cls, folder_id: str) -> None:
        """Removes the entire collection associated with a folder."""
        client = cls.get_client()
        name = cls.get_collection_name(folder_id)
        try:
            client.delete_collection(name)
        except Exception:
            pass

    @classmethod
    async def similarity_search(
        self,
        folder_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Searches the collection for top k documents matching query embedding.
        Returns a list of dictionaries with text, metadata, and distance score.
        """
        try:
            client = self.get_client()
            name = self.get_collection_name(folder_id)
            collection = client.get_collection(name)
        except Exception:
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter
        )

        search_results = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            ids = results["ids"][0]
            distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)

            for i in range(len(docs)):
                # Convert distance (cosine distance = 1 - cosine_similarity) to similarity score
                similarity = 1.0 - distances[i]
                search_results.append({
                    "id": ids[i],
                    "text": docs[i],
                    "metadata": metas[i],
                    "score": float(similarity)
                })

        return search_results
