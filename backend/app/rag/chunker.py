"""
Recursive character text splitter for chunking document text.
Keeps parent metadata intact and generates start/end indexes.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


class TextChunker:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Splits list of parsed documents into smaller chunks.
        Each document contains "text" and "metadata".
        """
        chunks = []
        for doc in documents:
            text = doc["text"]
            metadata = doc["metadata"]
            
            split_texts = self._split_text(text)
            for idx, chunk_text in enumerate(split_texts):
                chunk_meta = metadata.copy()
                chunk_meta["chunk_index"] = idx
                
                chunks.append({
                    "text": chunk_text,
                    "metadata": chunk_meta
                })
        return chunks

    def _split_text(self, text: str) -> List[str]:
        """
        Splits a single text block using standard recursive character splitting rules.
        """
        separators = ["\n\n", "\n", " ", ""]
        return self._recursive_split(text, separators, self.chunk_size, self.chunk_overlap)

    def _recursive_split(
        self, text: str, separators: List[str], max_size: int, overlap: int
    ) -> List[str]:
        # If text is already small enough, return it
        if len(text) <= max_size:
            return [text]

        if not separators:
            # No separators left, hard split by character
            return [text[i : i + max_size] for i in range(0, len(text), max_size - overlap)]

        separator = separators[0]
        next_separators = separators[1:]
        
        # Split text by current separator
        if separator == "":
            splits = list(text)
        else:
            splits = text.split(separator)

        chunks = []
        current_chunk = []
        current_len = 0

        for split in splits:
            # If a single split exceeds max_size, split it recursively with next separators
            if len(split) > max_size:
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                    current_chunk = []
                    current_len = 0
                
                sub_chunks = self._recursive_split(split, next_separators, max_size, overlap)
                chunks.extend(sub_chunks)
                continue

            # Check if adding this split exceeds max_size
            # Length includes the separator we used to split
            separator_len = len(separator) if current_chunk else 0
            if current_len + separator_len + len(split) > max_size:
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                
                # Setup next chunk with overlap
                # Backtrack to satisfy overlap constraints
                backtrack_chunk = []
                backtrack_len = 0
                for item in reversed(current_chunk):
                    sep_len = len(separator) if backtrack_chunk else 0
                    if backtrack_len + sep_len + len(item) <= overlap:
                        backtrack_chunk.insert(0, item)
                        backtrack_len += sep_len + len(item)
                    else:
                        break
                
                current_chunk = backtrack_chunk
                current_len = backtrack_len

            # Add split to current chunk
            if current_chunk:
                current_chunk.append(split)
                current_len += len(separator) + len(split)
            else:
                current_chunk = [split]
                current_len = len(split)

        if current_chunk:
            chunks.append(separator.join(current_chunk))

        # Filter out empty or whitespace-only chunks
        return [c.strip() for c in chunks if c.strip()]
